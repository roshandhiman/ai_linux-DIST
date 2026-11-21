"""Local audio capture, endpoint detection, speech recognition and playback."""

import ctypes
import ctypes.util
import os
import queue
import re
import selectors
import subprocess
import threading
import time
import wave
from collections import deque
from pathlib import Path

from .config import model_dir

RATE = 16000
FRAME = 320
FRAME_BYTES = FRAME * 2
VAD_TAIL = 16
WAKE_TAIL = 28


def stop_child(child):
    if child is not None and child.poll() is None:
        try:
            child.terminate()
        except ProcessLookupError:
            pass


class Denoise:
    def __init__(self):
        self.lib = None
        self.handle = None
        path = ctypes.util.find_library("speexdsp")
        if path:
            lib = ctypes.CDLL(path)
            lib.speex_preprocess_state_init.argtypes = (ctypes.c_int, ctypes.c_int)
            lib.speex_preprocess_state_init.restype = ctypes.c_void_p
            lib.speex_preprocess_run.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_short))
            lib.speex_preprocess_ctl.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p)
            lib.speex_preprocess_state_destroy.argtypes = (ctypes.c_void_p,)
            self.lib = lib
            self.handle = lib.speex_preprocess_state_init(FRAME, RATE)
            if self.handle:
                lib.speex_preprocess_ctl(self.handle, 0, ctypes.byref(ctypes.c_int(1)))
                lib.speex_preprocess_ctl(self.handle, 18, ctypes.byref(ctypes.c_int(-16)))

    def __call__(self, frame):
        if not self.handle:
            return frame
        data = (ctypes.c_short * FRAME).from_buffer_copy(frame)
        self.lib.speex_preprocess_run(self.handle, data)
        return bytes(data)

    def close(self):
        if self.handle:
            self.lib.speex_preprocess_state_destroy(self.handle)
            self.handle = None


class Wake:
    """Optional custom openWakeWord model and an offline Mino keyword fallback."""

    def __init__(self, path=""):
        self.detector = None
        self.decoder = None
        self.frames = []
        if path:
            from openwakeword.model import Model
            self.detector = Model(wakeword_models=[str(Path(path).expanduser())], inference_framework="onnx")
        else:
            from pocketsphinx import Decoder
            self.decoder = Decoder(lm=None, loglevel="ERROR", kws_threshold=1e-30,
                                   samprate=RATE)
            if not self.decoder.lookup_word("mino"):
                self.decoder.add_word("mino", "M IY N OW", True)
            self.decoder.add_keyphrase("wake", "mino")
            self.decoder.activate_search("wake")
            self.decoder.start_utt()

    def feed(self, frame):
        if self.detector:
            import numpy as np
            self.frames.append(frame)
            if len(self.frames) < 4:
                return False
            audio = np.frombuffer(b"".join(self.frames), dtype=np.int16)
            self.frames.clear()
            return any(score >= .60 for score in self.detector.predict(audio).values())
        self.decoder.process_raw(frame, False, False)
        if self.decoder.hyp() is None:
            return False
        self.reset()
        return True

    def reset(self):
        self.frames.clear()
        if self.decoder:
            self.decoder.end_utt()
            self.decoder.start_utt()
        elif self.detector:
            self.detector.reset()

    def close(self):
        if self.decoder:
            self.decoder.end_utt()


class Recognizer:
    def __init__(self, settings):
        self.settings = settings
        self.model = None

    def model_path(self):
        preferred = model_dir() / f"whisper-{self.settings.stt_size}"
        lightweight = model_dir() / "whisper-tiny"
        if (preferred / "model.bin").is_file() or not (lightweight / "model.bin").is_file():
            return preferred
        return lightweight

    def load(self):
        if self.model is None:
            from faster_whisper import WhisperModel
            directory = self.model_path()
            if not (directory / "model.bin").is_file():
                raise RuntimeError("Mino's speech model is missing. Run mino models.")
            self.model = WhisperModel(str(directory), device="cpu", compute_type="int8",
                                      cpu_threads=self.settings.threads, num_workers=1,
                                      local_files_only=True)
        return self.model

    def transcribe(self, pcm):
        import numpy as np
        audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768
        model = self.load()
        language = None if self.settings.language == "auto" else self.settings.language
        kwargs = dict(beam_size=1, condition_on_previous_text=False, without_timestamps=True,
                      max_new_tokens=90, no_speech_threshold=.65)
        words, info = model.transcribe(audio, language=language,
                                       hotwords=None if language == "hi" else "Mino, VS Code", **kwargs)
        if language is None and info.language not in ("en", "hi"):
            words, _ = model.transcribe(audio, language="hi", **kwargs)
        return " ".join(part.text.strip() for part in words).strip()


class Echo:
    """Route only Mino's streams through a PipeWire/PulseAudio echo canceller."""

    def __init__(self):
        self.source = ""
        self.sink = ""
        self.module = ""

    @staticmethod
    def pulse(*args):
        return subprocess.check_output(["pactl", *args], text=True, stderr=subprocess.DEVNULL, timeout=2).strip()

    def start(self):
        try:
            source, sink = self.pulse("get-default-source"), self.pulse("get-default-sink")
            if not source or source.endswith(".monitor") or not sink:
                return
            pid = os.getpid()
            name = f"mino_echo_{pid}"
            self.module = self.pulse(
                "load-module", "module-echo-cancel", f"source_master={source}", f"sink_master={sink}",
                f"source_name={name}_in", f"sink_name={name}_out",
                "aec_method=webrtc", "source_properties=priority.session=1", "sink_properties=priority.session=1",
            )
            self.source, self.sink = f"{name}_in", f"{name}_out"
        except (OSError, subprocess.SubprocessError):
            pass

    def close(self):
        if self.module.isdecimal():
            try:
                self.pulse("unload-module", self.module)
            except (OSError, subprocess.SubprocessError):
                pass
        self.module = self.source = self.sink = ""


class Capture:
    """Twenty-millisecond microphone frames with VAD, pre-roll and interruption."""

    def __init__(self, settings, echo, submit, state, is_speaking, cancel_speech, warn, busy):
        self.settings = settings
        self.echo = echo
        self.submit = submit
        self.state = state
        self.is_speaking = is_speaking
        self.cancel_speech = cancel_speech
        self.warn = warn
        self.busy = busy
        self.commands = queue.SimpleQueue()
        self.stop = threading.Event()
        self.child = None
        self.thread = threading.Thread(target=self.run, daemon=True, name="mino-mic")

    def arm(self, hold=False):
        self.commands.put("hold" if hold else "listen")

    def release(self):
        self.commands.put("release")

    def cancel(self):
        self.commands.put("cancel")

    def close(self):
        self.stop.set()
        self.commands.put("cancel")
        stop_child(self.child)

    def run(self):
        try:
            import webrtcvad
            vad = webrtcvad.Vad(2)
            denoise = Denoise()
        except (ImportError, OSError, ValueError) as exc:
            self.warn(f"Audio capture could not start: {exc}")
            return
        wake = None
        if self.settings.wake_word:
            try:
                wake = Wake(self.settings.wake_model)
            except Exception as exc:
                self.warn(f"Wake word is unavailable: {exc}. Use push-to-talk.")
        frames = []
        pre = deque(maxlen=14)
        audio = bytearray()
        held = False
        started = None
        speech = quiet = interrupts = 0
        activated_by_wake = False
        has_command = False
        retry_at = 0
        try:
            with selectors.DefaultSelector() as selector:
                while not self.stop.is_set():
                    while not self.commands.empty():
                        command = self.commands.get()
                        if command == "release":
                            held = False
                            if frames and speech >= 5:
                                quiet = max(quiet, VAD_TAIL - 2)
                            continue
                        if command == "cancel":
                            started = None
                            held = False
                            frames = []
                            self.state("idle")
                            continue
                        if self.busy():
                            self.warn("I'm still working on your previous request.")
                            continue
                        if self.is_speaking():
                            self.cancel_speech()
                        started = time.monotonic()
                        frames = list(pre)
                        held = command == "hold"
                        activated_by_wake = False
                        has_command = False
                        speech = quiet = 0
                        self.state("listening")
                    if self.child and self.child.poll() is not None:
                        selector.unregister(self.child.stdout)
                        self.child.stdout.close()
                        self.child = None
                        retry_at = time.monotonic() + 4
                        self.warn("The microphone is unavailable. Check your input device and try again.")
                    if self.child and started is None and not wake:
                        selector.unregister(self.child.stdout)
                        stop_child(self.child)
                        self.child.wait(timeout=2)
                        self.child.stdout.close()
                        self.child = None
                    if not self.child and (wake or started is not None) and time.monotonic() >= retry_at:
                        try:
                            args = ["parec", "--raw", "--format=s16le", "--rate=16000", "--channels=1",
                                    "--latency-msec=30", "--client-name=Mino"]
                            if self.echo.source:
                                args.append(f"--device={self.echo.source}")
                            self.child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                            selector.register(self.child.stdout, selectors.EVENT_READ)
                            audio.clear()
                        except OSError:
                            retry_at = time.monotonic() + 4
                            self.warn("Unable to open a microphone. Check PipeWire audio.")
                    if started is not None and time.monotonic() - started > 11:
                        if speech >= 5 and has_command:
                            self.submit(b"".join(frames))
                        else:
                            self.state("idle")
                        started = None
                        held = False
                        frames = []
                    if not self.child or not selector.select(.08):
                        if not self.child:
                            self.stop.wait(.08)
                        continue
                    incoming = os.read(self.child.stdout.fileno(), 4096)
                    if not incoming:
                        self.stop.wait(.04)
                        continue
                    audio.extend(incoming)
                    while len(audio) >= FRAME_BYTES:
                        frame = denoise(bytes(audio[:FRAME_BYTES]))
                        del audio[:FRAME_BYTES]
                        voiced = vad.is_speech(frame, RATE)
                        pre.append(frame)
                        if started is None and self.is_speaking():
                            if not self.echo.source:
                                continue
                            interrupts = interrupts + 1 if voiced else 0
                            if interrupts < 9:
                                continue
                            self.cancel_speech()
                            interrupts = 0
                            started = time.monotonic()
                            frames = list(pre)
                            activated_by_wake = False
                            has_command = True
                            speech, quiet = 6, 0
                            self.state("listening")
                        if started is None:
                            if self.busy():
                                continue
                            if wake and wake.feed(frame):
                                started = time.monotonic()
                                frames = list(pre)
                                speech = quiet = 0
                                activated_by_wake = True
                                has_command = False
                                self.state("listening")
                            continue
                        frames.append(frame)
                        speech += int(voiced)
                        quiet = 0 if voiced else quiet + 1
                        if speech >= 5:
                            has_command = True
                        pause = WAKE_TAIL if activated_by_wake else VAD_TAIL
                        if speech >= 5 and quiet >= pause and not held:
                            self.submit(b"".join(frames[:-max(0, quiet - 5)]))
                            started = None
                            frames = []
                            pre.clear()
                            if wake:
                                wake.reset()
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            if not self.stop.is_set():
                self.warn(f"Microphone capture stopped: {exc}")
        finally:
            stop_child(self.child)
            if self.child:
                self.child.wait()
                self.child.stdout.close()
            denoise.close()
            if wake:
                wake.close()


class Speaker:
    """Queue sentence audio without waiting for the whole answer to be rendered."""

    def __init__(self, settings, echo, state, warn):
        self.settings = settings
        self.echo = echo
        self.state = state
        self.warn = warn
        self.jobs = queue.Queue(maxsize=12)
        self.generation = 0
        self.playback = None
        self.speaking = threading.Event()
        self.closed = threading.Event()
        self.engine = None
        self.voice_id = None
        self.thread = threading.Thread(target=self.run, daemon=True, name="mino-tts")
        self.thread.start()

    def cancel(self):
        self.generation += 1
        stop_child(self.playback)

    def say(self, text, generation):
        if generation != self.generation or self.closed.is_set() or not text.strip():
            return
        try:
            self.jobs.put_nowait((text[:1000], generation))
        except queue.Full:
            pass

    def chunks(self, text):
        language = self.settings.language
        hindi = language == "hi" or language == "auto" and bool(re.search(r"[\u0900-\u097f]", text))
        identifier = self.settings.hi_voice if hindi else self.settings.en_voice
        if self.settings.voice_engine == "kokoro" and not hindi:
            try:
                from kokoro_onnx import Kokoro
                key = "kokoro"
                if key != self.voice_id:
                    self.engine = Kokoro(str(model_dir() / "kokoro-v1.0.onnx"),
                                         str(model_dir() / "voices-v1.0.bin"))
                    self.voice_id = key
                for sentence in re.split(r"(?<=[.!?])\s+", text):
                    floats, rate = self.engine.create(sentence, voice="af_heart",
                                                      speed=self.settings.speed, lang="en-us")
                    yield rate, (floats.clip(-1, 1) * 32767).astype("<i2").tobytes()
                return
            except (ImportError, OSError, ValueError, RuntimeError):
                self.warn("Kokoro isn't ready. Using Piper.")
        path = model_dir() / f"{identifier}.onnx"
        if path.is_file():
            try:
                from piper import PiperVoice, SynthesisConfig
                if identifier != self.voice_id:
                    self.engine = PiperVoice.load(str(path))
                    self.voice_id = identifier
                config = SynthesisConfig(length_scale=1 / self.settings.speed)
                for chunk in self.engine.synthesize(text, config):
                    yield chunk.sample_rate, chunk.audio_int16_bytes
                return
            except (ImportError, OSError, ValueError, RuntimeError):
                self.warn("Piper isn't ready. Using the small local fallback voice.")
        with subprocess.Popen(
            ["espeak-ng", "--stdin", "--stdout", "-v", "hi" if hindi else "en",
             "-s", str(int(168 * self.settings.speed))], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        ) as synth:
            synth.stdin.write(text.encode())
            synth.stdin.close()
            with wave.open(synth.stdout) as rendered:
                while data := rendered.readframes(2048):
                    yield rendered.getframerate(), data

    def run(self):
        while not self.closed.is_set():
            try:
                text, generation = self.jobs.get(timeout=.3)
            except queue.Empty:
                continue
            if generation != self.generation:
                continue
            self.speaking.set()
            self.state("speaking")
            try:
                for rate, data in self.chunks(text):
                    if generation != self.generation or self.closed.is_set():
                        break
                    if not self.playback:
                        args = ["pacat", "--playback", "--raw", "--format=s16le", f"--rate={rate}",
                                "--channels=1", "--latency-msec=40", "--client-name=Mino"]
                        if self.echo.sink:
                            args.append(f"--device={self.echo.sink}")
                        self.playback = subprocess.Popen(args, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    self.playback.stdin.write(data)
                    self.playback.stdin.flush()
            except Exception as exc:
                if generation == self.generation:
                    self.warn(f"Audio playback is unavailable: {exc}")
            finally:
                if self.playback:
                    try:
                        self.playback.stdin.close()
                        self.playback.wait(timeout=4)
                    except (OSError, subprocess.TimeoutExpired):
                        stop_child(self.playback)
                        self.playback.wait()
                    self.playback = None
                self.speaking.clear()
                if generation == self.generation:
                    self.state("idle")

    def close(self):
        self.closed.set()
        self.cancel()
