# Mino voice assistant

Mino is the local-first desktop assistant for MineOS on Debian 13 and Plasma/X11. Click the microphone beside the pixel companion and speak when **Listening…** appears. You can also say “Mino” or hold **Ctrl + Alt + Space**, speak, and release. On PipeWire with echo cancellation enabled, speaking over the reply interrupts playback.

## Audit

- The existing desktop chat and CLI lacked a shared speech pipeline. Mino uses a dedicated user service, a small GTK overlay, and a CLI that shares the service's short-term context.
- The coding agent can run model-written Python for tool use. Mino uses a separate registry of typed tools and fast command patterns. File overwrites and Trash actions have review dialogs. Terminal requests require explicit approval and run with a read-only workspace and isolated network.
- The previous screen OCR path could wait up to 15 seconds. Mino captures the focused X11 window, bounds the OCR input, and times out Tesseract after 1.25 seconds. Recognizable errors get a short explanation and a documentation link without waiting for the language model.

## Install or upgrade

Run from the MineOS checkout as your normal desktop user.

    bash scripts/install-mino.sh
    mino status

The installer uses sudo for Debian packages and installs the program under /opt/mino. The systemd user service starts with the graphical session. Initial model downloads require internet access. To install the program and download the models separately, use

    MINO_SKIP_MODELS=1 bash scripts/install-mino.sh
    mino models tiny

The program stores voice models under ~/.local/share/mineos/mino/models. MINO_MODEL_DIR can override this location. Run mino models after changing the voice or recognition model to download that selection. Use systemctl --user restart mino.service after changing model files or editing settings by hand.

## Voice settings

Open **Mino Voice Settings** from the app menu or run mino settings. Choose Auto, Hindi, or English, set playback speed, and enable or disable wake-word listening. Auto uses multilingual Whisper. Choose Hindi explicitly if short Hindi or mixed-language phrases are detected as English.

| Setting | Default | Options |
| --- | --- | --- |
| wake_word | true | Custom offline PocketSphinx keyword or optional openWakeWord model |
| model_size | auto | tiny on about 4 GB, base on about 8 GB, small on machines with more than 10 GB |
| language | auto | auto, en, hi |
| en_voice | en_US-amy-low | en_US-amy-low, en_US-lessac-medium |
| hi_voice | hi_IN-rohan-medium | hi_IN-rohan-medium, hi_IN-pratham-medium |
| speed | 1.0 | 0.65 to 1.5 |
| voice_engine | piper | piper, kokoro for English |
| wake_model | empty | Path to a trained Mino openWakeWord ONNX model |
| local_vision | false | Use the installed MineOS vision model when OCR finds no text |
| use_hosted_planner | false | Use the optional provider from MineOS's agent.json |

Settings are stored in ~/.config/mineos/mino.json. Mino defaults to faster-whisper on CPU with int8 weights and Piper for English and Hindi. If a larger speech model is missing, it uses the downloaded tiny model. eSpeak NG provides speech if the selected Piper voice is missing or fails. Set MINO_KOKORO=1 at install time for optional English Kokoro. Use mino models kokoro to fetch its weights. Set MINO_OPENWAKEWORD=1 when installing to use your own trained Mino model. Wake sensitivity varies with the microphone and background noise.

The common desktop commands, OCR, recognition, and speech run on-device. General requests use the existing MineOS loopback model. Hosted planning receives the current request after you enable it, while file reads and screen explanations stay local. Web search, reference pages, and YouTube require connectivity. Mino checks the official YouTube feed for Sourav Joshi Vlogs and opens the uploads page if the lookup is unavailable.

On Wayland, use a compositor shortcut bound to mino listen. Screen capture requires a compositor compatible with grim and slurp. The X11 shortcut, focused-window capture, and close-window follow-ups are tested on the MineOS target.

## Demo

    bash scripts/demo-mino.sh --check
    bash scripts/demo-mino.sh

The first command runs regression checks without opening apps or browsing. The second sends the following requests to the installed service and speaks the replies. It gives you time to focus a window with an error, and creates notes.txt in a dedicated demo folder. Say the same requests aloud to try the microphone.

1. “Mino, open VS Code.” This opens MineOS IDE when it is installed.
2. “Create a file notes.txt and write hello.” A bare filename goes into Documents.
3. “Read my screen and explain this error.” You can also say “isko samjhao.”
4. “Play Sourav Joshi latest vlog.”

Try “ab isse close kar do” after launching an app. Mino asks the window to close so the app can still prompt to save. For terminal errors, try mino 'run python3 --version', then review the command in the approval dialog.

Run journalctl --user -u mino.service -n 30 for startup and microphone diagnostics. Use mino listen for a one-shot recording and mino stop to stop speech.
