"""MineOS Camera and its on-demand, offline AI view."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import fcntl
import logging
import os
from pathlib import Path
import struct
import sys
from threading import Event, Lock, Thread
import time

import cv2
import gi

gi.require_versions({"Gtk": "3.0", "Gdk": "3.0", "GdkPixbuf": "2.0"})
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk

from camera_overlay import LiveVision, POSE_LINKS
from camera_scene import SceneDetector, available, fingerprint, merge_boxes, scene_distance
from camera_vision import MODEL

LIVE_INTERVAL = .18
OVERLAY_MAX_AGE = .65
SCENE_CHANGE = 8
SCENE_REFRESH = 3.0
BOX_COLORS = {
    "person": (.31, .87, .92),
    "bottle": (.40, .94, .68),
    "cell phone": (.75, .66, 1),
}
FALLBACK_BOX_COLOR = (.98, .77, .44)

LOG = logging.getLogger(__name__)
IMAGES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".avif"}
CSS = b"""
window.mineos-camera { background-color: #181b22; color: #ecedf4; }
.mineos-camera headerbar { background: #232733; color: #ecedf4; border-bottom-color: #383d4a; }
.mineos-camera .view { background: #0d0f14; color: #cacdd9; }
.mineos-camera .tools { background: #222632; padding: 8px 12px; }
.mineos-camera label.status { color: #c4c8d6; }
"""


def cameras():
    devices = {}
    for path in sorted(Path("/dev").glob("video*")):
        try:
            with open(path, "rb", opener=lambda name, flags: os.open(name, flags | os.O_NONBLOCK)) as device:
                caps = bytearray(104)
                fcntl.ioctl(device.fileno(), 0x80685600, caps)  # VIDIOC_QUERYCAP
            flags, device_flags = struct.unpack_from("=II", caps, 84)
            if (device_flags if flags & 0x80000000 else flags) & 0x00001001:
                card = bytes(caps[16:48]).split(b"\0", 1)[0].decode(errors="replace")
                devices[str(path)] = card.split(": ", 1)[0]
        except OSError:
            continue
    return devices


def camera_has_swapped_channels(path):
    # Parallels forwards the built-in MacBook camera with red and blue reversed.
    device = Path("/sys/class/video4linux") / Path(path).name / "device"
    try:
        usb = device.resolve(strict=True).parent
        return ((usb / "idVendor").read_text().strip() == "203a"
                and (usb / "product").read_text().strip().startswith("MacBook "))
    except OSError:
        return False


def output_file(extension):
    pictures = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) or str(Path.home() / "Pictures")
    folder = Path(pictures) / "MineOS Camera"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / (datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f") + extension)


class Stream:
    def __init__(self, path, kind, lock):
        self.path, self.kind, self.lock = path, kind, lock
        self.stop = Event()
        self.pause = Event()
        self.frame = None
        self.error = ""
        self.record_path = None
        self.recorded = None
        self.ended = False
        Thread(target=self.run, name="camera-capture").start()

    def run(self):
        try:
            if self.kind == "image":
                self.frame = cv2.imread(self.path, cv2.IMREAD_COLOR)
                if self.frame is None:
                    self.error = "Couldn’t open this image."
            elif self.kind == "camera":
                with self.lock:
                    if not self.stop.is_set():
                        self.read_video()
            else:
                self.read_video()
        except (cv2.error, OSError):
            LOG.exception("Camera source stopped")
            self.error = "Couldn’t read this source."
        finally:
            self.ended = True

    def read_video(self):
        live = self.kind == "camera"
        backend = cv2.CAP_V4L2 if live else cv2.CAP_FFMPEG
        capture = cv2.VideoCapture(self.path, backend)
        writer = None
        recorded = None
        swap_channels = live and camera_has_swapped_channels(self.path)
        try:
            if not capture.isOpened():
                self.error = "Camera unavailable. Check access or select another device." if live else "Couldn’t open this video."
                return
            if live:
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                capture.set(cv2.CAP_PROP_FPS, 30)
            fps = capture.get(cv2.CAP_PROP_FPS)
            if not 1 <= fps <= 120:
                fps = 30
            while not self.stop.is_set():
                if self.pause.is_set():
                    self.stop.wait(0.035)
                    continue
                start = time.monotonic()
                ok, frame = capture.read()
                if not ok:
                    if live or self.frame is None:
                        self.error = "No video frames received."
                    break
                if swap_channels:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                if live:
                    frame = cv2.flip(frame, 1)
                self.frame = frame
                requested = self.record_path
                if writer and requested != recorded:
                    writer.release()
                    self.recorded = recorded
                    writer = None
                if requested and not writer:
                    height, width = frame.shape[:2]
                    writer = cv2.VideoWriter(str(requested), cv2.VideoWriter_fourcc(*"MJPG"), fps, (width, height))
                    if not writer.isOpened():
                        writer.release()
                        writer = None
                        self.record_path = None
                        self.error = "Couldn’t start recording."
                    else:
                        recorded = requested
                if writer:
                    writer.write(frame)
                if not live:
                    self.stop.wait(max(0, 1 / fps - (time.monotonic() - start)))
        finally:
            if writer:
                writer.release()
                self.recorded = recorded
            self.record_path = None
            capture.release()


def icon_button(icon, label, handler):
    button = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
    button.set_tooltip_text(label)
    button.get_accessible().set_name(label)
    button.connect("clicked", handler)
    return button


class CameraWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="Camera")
        self.set_default_size(960, 680)
        self.set_size_request(420, 420)
        self.get_style_context().add_class("mineos-camera")
        self.capture_lock = Lock()
        self.stream = None
        self.displayed = None
        self.pixbuf = None
        self.reported = None
        self.live_queue = ThreadPoolExecutor(max_workers=1, thread_name_prefix="camera-overlay")
        self.live_vision = LiveVision()
        self.scene_queue = ThreadPoolExecutor(max_workers=1, thread_name_prefix="camera-scene")
        self.scene_detector = None
        self.scene_job = None
        self.scene_frame = None
        self.scene_marks = None
        self.scene_boxes = []
        self.scene_next = 0.0
        self.scene_updated = 0.0
        self.scene_available = available()
        self.live_job = None
        self.live_last_frame = None
        self.live_next = 0
        self.live_generation = 0
        self.live_result = None
        self.live_result_time = 0
        self.live_error = False
        self.closed = False

        header = Gtk.HeaderBar(title="Camera", show_close_button=True)
        self.set_titlebar(header)
        self.modes = Gtk.Stack()
        self.modes.add_titled(Gtk.Box(), "camera", "Camera")
        self.modes.add_titled(Gtk.Box(), "ai", "AI Camera")
        self.modes.show_all()
        header.set_custom_title(Gtk.StackSwitcher(stack=self.modes))
        self.modes.connect("notify::visible-child-name", self.mode_changed)
        self.device = Gtk.ComboBoxText()
        self.device.connect("changed", self.open_camera)
        self.device.set_tooltip_text("Camera source")
        self.device.get_accessible().set_name("Camera source")
        header.pack_start(self.device)
        self.open_button = icon_button("document-open-symbolic", "Open image or video", self.open_file)
        header.pack_end(self.open_button)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)
        preview = Gtk.Overlay()
        preview.get_style_context().add_class("view")
        self.view = Gtk.DrawingArea()
        self.view.connect("draw", self.draw)
        preview.add(self.view)
        self.placeholder = Gtk.Label(label="No camera connected", halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        preview.add_overlay(self.placeholder)
        root.pack_start(preview, True, True, 0)

        controls = Gtk.Box(spacing=8)
        controls.get_style_context().add_class("tools")
        self.photo = icon_button("camera-photo-symbolic", "Take photo", self.save_photo)
        self.record = icon_button("media-record-symbolic", "Record video", self.toggle_record)
        self.play = icon_button("media-playback-pause-symbolic", "Play or pause", self.toggle_play)
        for button in (self.photo, self.record, self.play):
            controls.pack_start(button, False, False, 0)
        self.status = Gtk.Label(xalign=0)
        self.status.get_style_context().add_class("status")
        self.status.set_single_line_mode(True)
        controls.pack_start(self.status, True, True, 0)
        root.pack_start(controls, False, False, 0)

        self.connect("destroy", self.on_destroy)

        self.show_all()
        self.mode_changed()
        self.device.append("off", "Camera off")
        for path, name in cameras().items():
            self.device.append(path, name or path)
        self.device.set_active(1 if len(self.device.get_model()) > 1 else 0)
        self.timer = GLib.timeout_add(33, self.refresh)

    def set_mode(self, mode):
        self.modes.set_visible_child_name(mode)

    def mode_changed(self, *_):
        if hasattr(self, "view"):
            self.reset_overlay()

    def change_source(self, path, kind):
        old = self.stream
        if old:
            old.stop.set()
        self.stream = Stream(path, kind, self.capture_lock) if path else None
        self.displayed = self.pixbuf = self.reported = None
        self.reset_overlay()
        self.status.set_text("")
        self.placeholder.set_text("Opening…" if path else "Camera off")
        self.placeholder.show()
        self.view.queue_draw()

    def open_camera(self, *_):
        path = self.device.get_active_id()
        self.change_source(path if path != "off" else None, "camera")

    def open_file(self, *_):
        dialog = Gtk.FileChooserNative.new("Open image or video", self, Gtk.FileChooserAction.OPEN, "Open", "Cancel")
        media = Gtk.FileFilter(name="Images and videos")
        media.add_mime_type("image/*")
        media.add_mime_type("video/*")
        dialog.add_filter(media)
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            self.device.set_active_id("off")
            kind = "image" if Path(path).suffix.lower() in IMAGES else "video"
            self.change_source(path, kind)
        dialog.destroy()

    def is_ai_mode(self):
        return self.modes.get_visible_child_name() == "ai"

    def reset_overlay(self):
        self.live_generation += 1
        self.live_last_frame = self.live_result = None
        self.live_next = 0
        self.live_error = False
        self.scene_frame = self.scene_marks = None
        self.scene_boxes = []
        self.scene_next = self.scene_updated = 0.0
        self.view.queue_draw()

    def update_overlay(self, frame, now):
        if not self.is_ai_mode() or frame is None or self.live_error:
            return
        if self.live_result and frame is not self.live_last_frame and now - self.live_result_time > OVERLAY_MAX_AGE:
            self.live_result = None
            self.view.queue_draw()
        if self.live_job or frame is self.live_last_frame or now < self.live_next:
            return
        if not MODEL.is_file():
            self.live_error = True
            self.status.set_text("Offline object detector is missing.")
            return
        self.live_last_frame = frame
        self.live_next = now + LIVE_INTERVAL
        generation = self.live_generation
        self.live_job = self.live_queue.submit(self.live_vision.inspect, frame)
        self.live_job.add_done_callback(
            lambda future: GLib.idle_add(self.show_overlay, future, generation, now)
        )

    def show_overlay(self, future, generation, started):
        self.live_job = None
        if self.closed or generation != self.live_generation:
            return False
        try:
            result = future.result()
        except Exception:
            LOG.exception("Live camera detection failed")
            self.live_error = True
            self.status.set_text("Live detection unavailable.")
            return False
        self.live_result_time = started
        self.live_result = result
        self.view.queue_draw()
        return False

    def update_scene(self, frame, now):
        if not self.is_ai_mode() or frame is None or not self.scene_available:
            return
        marks = fingerprint(frame)
        distance = scene_distance(self.scene_marks, marks) if self.scene_marks is not None else None
        if distance is not None and distance > SCENE_CHANGE and self.scene_boxes:
            self.scene_boxes = []
            self.view.queue_draw()
        if self.scene_job or frame is self.scene_frame or now < self.scene_next:
            return
        if distance is not None and distance < 2.0 and now - self.scene_updated < SCENE_REFRESH:
            return
        self.scene_frame = frame
        generation = self.live_generation
        self.scene_job = self.scene_queue.submit(self.detect_scene, frame)
        self.scene_job.add_done_callback(
            lambda future: GLib.idle_add(self.show_scene, future, generation, marks)
        )

    def detect_scene(self, frame):
        if self.scene_detector is None:
            self.scene_detector = SceneDetector()
        return self.scene_detector.detect(frame)

    def show_scene(self, future, generation, marks):
        self.scene_job = None
        if self.closed:
            return False
        try:
            boxes = future.result()
        except Exception:
            LOG.exception("Could not run the scene detector")
            self.scene_available = False
            self.status.set_text("Detailed detection unavailable.")
            return False
        if generation != self.live_generation or self.displayed is None:
            return False
        self.scene_updated = time.monotonic()
        self.scene_next = self.scene_updated + .45
        if scene_distance(marks, fingerprint(self.displayed)) <= SCENE_CHANGE:
            self.scene_marks = marks
            self.scene_boxes = boxes
            self.view.queue_draw()
        return False

    def draw(self, widget, context):
        if not self.pixbuf:
            return False
        width, height = self.pixbuf.get_width(), self.pixbuf.get_height()
        scale = min(widget.get_allocated_width() / width, widget.get_allocated_height() / height)
        context.translate((widget.get_allocated_width() - width * scale) / 2,
                          (widget.get_allocated_height() - height * scale) / 2)
        context.save()
        context.scale(scale, scale)
        Gdk.cairo_set_source_pixbuf(context, self.pixbuf, 0, 0)
        context.paint()
        context.restore()
        if self.is_ai_mode() and (self.live_result or self.scene_boxes):
            self.draw_overlay(context, width * scale, height * scale)
        return False

    def draw_overlay(self, context, width, height):
        result = self.live_result
        source_width, source_height = result.size if result else self.displayed.shape[1::-1]
        sx, sy = width / source_width, height / source_height
        context.rectangle(0, 0, width, height)
        context.clip()
        context.set_line_width(2)
        context.set_source_rgba(.31, .87, .92, .93)
        for points in result.poses if result else ():
            for a, b in POSE_LINKS:
                if points[a] is None or points[b] is None:
                    continue
                x, y = points[a]
                context.move_to(x * sx, y * sy)
                x, y = points[b]
                context.line_to(x * sx, y * sy)
            context.stroke()
            for point in points[11:29]:
                if point is not None:
                    context.new_sub_path()
                    context.arc(point[0] * sx, point[1] * sy, 2.3, 0, 6.283185)
            context.fill()

        context.select_font_face("Sans", 0, 1)
        context.set_font_size(13)
        for label, (x, y, w, h) in merge_boxes(result.boxes if result else (), self.scene_boxes):
            x, y, w, h = x * sx, y * sy, w * sx, h * sy
            color = BOX_COLORS.get(label, FALLBACK_BOX_COLOR)
            context.set_source_rgb(*color)
            context.rectangle(x, y, w, h)
            context.stroke()
            text = "Phone" if label == "cell phone" else label.capitalize()
            text_width = context.text_extents(text)[4] + 12
            label_x = max(0, min(x, width - text_width))
            label_y = y - 21 if y >= 21 else y
            context.rectangle(label_x, label_y, text_width, 20)
            context.fill()
            context.set_source_rgb(.04, .08, .10)
            context.move_to(label_x + 6, label_y + 14)
            context.show_text(text)

    def refresh(self):
        stream = self.stream
        frame = stream.frame if stream else None
        if frame is not None and frame is not self.displayed:
            self.displayed = frame
            height, width = frame.shape[:2]
            scale = min(1, 1280 / max(width, height))
            preview = frame
            if scale < 1:
                preview = cv2.resize(frame, (max(1, round(width * scale)), max(1, round(height * scale))))
            rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
            height, width = rgb.shape[:2]
            self.pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
                GLib.Bytes.new(rgb.tobytes()), GdkPixbuf.Colorspace.RGB, False, 8, width, height, width * 3)
            self.placeholder.hide()
            self.view.queue_draw()
        now = time.monotonic()
        self.update_overlay(frame, now)
        self.update_scene(frame, now)
        issue = stream.error if stream else ""
        if issue and issue != self.reported:
            self.reported = issue
            if frame is None:
                self.placeholder.set_text(issue)
            else:
                self.status.set_text(issue)
        if stream and stream.recorded:
            self.status.set_text(f"Saved {stream.recorded.name}")
            stream.recorded = None
        live = bool(stream and stream.kind == "camera" and not stream.ended)
        playing_file = bool(stream and stream.kind == "video")
        self.record.set_sensitive(live and frame is not None)
        self.photo.set_sensitive(frame is not None)
        self.play.set_visible(playing_file)
        recording = bool(stream and stream.record_path)
        record_style = self.record.get_style_context()
        if recording != record_style.has_class("destructive-action"):
            if recording:
                record_style.add_class("destructive-action")
            else:
                record_style.remove_class("destructive-action")
            self.set_icon(self.record, "media-playback-stop-symbolic" if recording else "media-record-symbolic")
        if playing_file:
            self.set_icon(self.play, "media-playback-start-symbolic" if stream.pause.is_set() or stream.ended else "media-playback-pause-symbolic")
        return True

    @staticmethod
    def set_icon(button, icon):
        image = button.get_image()
        if image.get_icon_name()[0] != icon:
            image.set_from_icon_name(icon, Gtk.IconSize.BUTTON)

    def save_photo(self, *_):
        if self.displayed is None:
            return
        frame = self.displayed

        def save():
            try:
                path = output_file(".jpg")
                message = f"Saved {path.name}" if cv2.imwrite(str(path), frame) else "Couldn’t save the photo."
            except (OSError, cv2.error):
                message = "Couldn’t save the photo."
            GLib.idle_add(self.show_status, message)

        Thread(target=save, name="camera-photo").start()

    def show_status(self, message):
        if not self.closed:
            self.status.set_text(message)
        return False

    def toggle_record(self, *_):
        stream = self.stream
        if not stream or stream.ended or stream.kind != "camera":
            return
        if stream.record_path:
            stream.record_path = None
        else:
            try:
                stream.error = ""
                self.reported = None
                stream.record_path = output_file(".avi")
                self.status.set_text("Recording…")
            except OSError:
                self.status.set_text("Couldn’t save the recording.")

    def toggle_play(self, *_):
        stream = self.stream
        if not stream or stream.kind != "video":
            return
        if stream.ended:
            self.change_source(stream.path, "video")
        elif stream.pause.is_set():
            stream.pause.clear()
        else:
            stream.pause.set()

    def on_destroy(self, *_):
        self.closed = True
        GLib.source_remove(self.timer)
        if self.stream:
            self.stream.stop.set()
        self.live_queue.shutdown(wait=False, cancel_futures=True)
        self.scene_queue.shutdown(wait=False, cancel_futures=True)


class CameraApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.mineos.Camera", flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

    def do_startup(self):
        Gtk.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        screen = Gdk.Screen.get_default()
        if screen:
            Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def do_command_line(self, command_line):
        mode = "ai" if "--ai" in command_line.get_arguments()[1:] else "camera"
        window = self.get_active_window() or CameraWindow(self)
        window.set_mode(mode)
        window.present()
        return 0


if __name__ == "__main__":
    cv2.setNumThreads(2)
    raise SystemExit(CameraApp().run(sys.argv))
