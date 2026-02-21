"""
H2N Bridge — Application Controller
=====================================
Wires together audio recording, transcription, translation and the
floating overlay UI.  Global hotkey (Ctrl+K) toggles recording.

IMPORTANT: All QObject / QTimer / QThread operations MUST run on the
main Qt thread.  The pynput hotkey fires on a daemon thread, so it
only emits a thread-safe pyqtSignal which is handled on the main
thread via a queued connection.
"""

# ── Early Qt plugin setup (MUST happen before any PyQt6 import) ──────
# macOS SIP strips DYLD_* and sometimes QT_PLUGIN_PATH from child
# processes.  Setting it via os.environ in Python bypasses that.
import os, pathlib
_this_dir = pathlib.Path(__file__).resolve().parent.parent.parent        # project root
_plugin_dir = (
    _this_dir / ".venv311" / "lib" / "python3.11" / "site-packages"
    / "PyQt6" / "Qt6" / "plugins"
)
if _plugin_dir.is_dir():
    os.environ.setdefault("QT_PLUGIN_PATH", str(_plugin_dir))
os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")

# ─────────────────────────────────────────────────────────────────────

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer
from h2n_bridge.ui.overlay import Overlay, SignalHandler
from h2n_bridge.ui.settings import SettingsWindow
from h2n_bridge.components.audio import AudioRecorder
from h2n_bridge.components.transcriber import FasterTranscriber
from h2n_bridge.components.translator import Translator
from h2n_bridge.components.output import OutputHandler
from h2n_bridge.components.shortcut_manager import ShortcutManager
from h2n_bridge.config import WHISPER_MODEL_SIZE
from pynput import keyboard as pynput_keyboard # Keep this import style
import threading
import time
import sys
import numpy as np


# ────────────────────────  Worker (QThread)  ─────────────────────────
class Worker(QObject):
    """
    Runs STT + Groq translation on a background QThread.
    Emits progress updates and the final translated text.
    """
    finished            = pyqtSignal()
    progress            = pyqtSignal(str)
    translation_finished = pyqtSignal(str)   # final English text

    def __init__(self, audio_data, transcriber, translator):
        super().__init__()
        self.audio_data = audio_data
        self.transcriber = transcriber
        self.translator = translator

    def run(self):
        try:
            # 1. Transcribe (STT)
            self.progress.emit("Transcribing…")
            hebrew_text = self.transcriber.transcribe(self.audio_data)
            print(f"Hebrew: {hebrew_text}", flush=True)

            if not hebrew_text or hebrew_text.strip() == "":
                self.progress.emit("No speech detected.")
                time.sleep(1.0)
                self.finished.emit()   # ← single emit, then return
                return                 # ← IMPORTANT: skip the emit at the bottom

            # 2. Translate via Groq
            self.progress.emit("Translating…")
            english_text = self.translator.translate(hebrew_text)
            print(f"English: {english_text}", flush=True)

            # Emit the final result — connected to on_conversion_success
            self.translation_finished.emit(english_text)

        except Exception as e:
            print(f"Worker error: {e}", flush=True)
            self.progress.emit(f"Error: {e}")
            time.sleep(1.5)

        self.finished.emit()   # single emit on success / error paths


# ───────────────────  Hotkey Bridge (thread→main)  ───────────────────
class HotkeyBridge(QObject):
    """
    Tiny QObject that lives on the main thread.
    The pynput daemon thread emits signals, and because of Qt's
    automatic queued-connection the slots run on the main thread.
    """
    translation_triggered = pyqtSignal()
    settings_triggered = pyqtSignal()
    exit_triggered = pyqtSignal()


# ────────────────────  Application Controller  ──────────────────────
class AppController:
    """
    Manages the 4-state lifecycle:
      IDLE → LISTENING → PROCESSING → COMPLETED → (auto) IDLE
    """

    def __init__(self):
        # ── Overlay + signal handler (lives on main thread) ──
        self.signal_handler = SignalHandler()
        self.overlay = Overlay(self.signal_handler)

        # ── Back-end components ──
        print("Initializing components…", flush=True)
        self.recorder = AudioRecorder()
        self.transcriber = FasterTranscriber(model_size=WHISPER_MODEL_SIZE)
        try:
            self.translator = Translator()
        except ValueError as e:
            print(f"Configuration Error: {e}", flush=True)
            sys.exit(1)

        self.output_handler = OutputHandler()

        # ── State ──
        self.is_recording = False
        self._worker_thread: QThread | None = None
        self._worker: Worker | None = None
        self._thread_busy = False   # True while a QThread is alive

        # ── Audio amplitude timer (MUST be started on main thread) ──
        self._level_timer = QTimer()
        self._level_timer.setInterval(30)   # ~33 fps
        self._level_timer.timeout.connect(self._pump_amplitude)

        # ── Shortcut Manager (handles daemon thread) ──
        self.shortcut_manager = ShortcutManager()
        
        # ── Hotkey bridge: daemon thread → main thread ──
        self._hotkey_bridge = HotkeyBridge()
        self._hotkey_bridge.translation_triggered.connect(self._on_hotkey_main_thread)
        self._hotkey_bridge.settings_triggered.connect(self._toggle_settings)
        self._hotkey_bridge.exit_triggered.connect(QApplication.instance().quit)

        # Register callbacks to bridge
        self.shortcut_manager.register_callback(
            "translation_trigger", self._hotkey_bridge.translation_triggered.emit
        )
        self.shortcut_manager.register_callback(
            "app_launch", self._hotkey_bridge.settings_triggered.emit
        )
        self.shortcut_manager.register_callback(
            "app_exit", self._hotkey_bridge.exit_triggered.emit
        )

        # Start listening
        self.shortcut_manager.start_listener()
        
        # ── Settings UI ──
        self.settings_window = SettingsWindow(self.shortcut_manager)

        print(f"App Ready. Configured shortcuts: {self.shortcut_manager.shortcuts}", flush=True)

    def _toggle_settings(self):
        """Shows/hides the settings window."""
        if self.settings_window.isVisible():
            self.settings_window.hide()
        else:
            self.settings_window.show()
            self.settings_window.activateWindow()
            self.settings_window.raise_()

    # ─────────────────────────────────────────────────────────────────
    #  Hotkey listener (runs on daemon thread)
    # ─────────────────────────────────────────────────────────────────
    # Removed _start_listener as it's handled by ShortcutManager

    # ─────────────────────────────────────────────────────────────────
    #  Main-thread slot — safe for all Qt operations
    # ─────────────────────────────────────────────────────────────────
    def _on_hotkey_main_thread(self):
        """Called on the MAIN thread via queued signal."""
        if not self.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    # ─────────────────────────────────────────────────────────────────
    #  State: IDLE → LISTENING
    # ─────────────────────────────────────────────────────────────────
    def _start_recording(self):
        # Guard: refuse to start if a background thread is still winding down
        if self._thread_busy:
            print("Busy — previous processing still running, ignoring hotkey.", flush=True)
            return

        print("Starting recording…", flush=True)
        self.is_recording = True

        # Overlay → LISTENING
        self.signal_handler.show_window.emit()
        self.signal_handler.set_state.emit("listening")

        # Start mic capture (sounddevice manages its own thread)
        try:
            self.recorder.start_recording()
        except OSError as e:
            print(f"microphone error: {e}", flush=True)
            self.signal_handler.update_text.emit(f"Mic Error: {e}")
            self.is_recording = False
            QTimer.singleShot(2000, lambda: self.signal_handler.hide_window.emit())
            return

        # Start amplitude pump (safe — we are on the main thread)
        self._level_timer.start()

    # ─────────────────────────────────────────────────────────────────
    #  State: LISTENING → PROCESSING
    # ─────────────────────────────────────────────────────────────────
    def _stop_recording(self):
        print("Stopping recording…", flush=True)
        self.is_recording = False

        # Stop amplitude pump
        self._level_timer.stop()

        # Overlay → PROCESSING
        self.signal_handler.set_state.emit("processing")

        # Grab audio buffer
        audio_data = self.recorder.stop_recording()

        if audio_data:
            self._process_audio(audio_data)
        else:
            # Nothing recorded — cancel
            self.signal_handler.update_text.emit("Cancelled")
            QTimer.singleShot(
                1000, lambda: self.signal_handler.hide_window.emit()
            )

    # ─────────────────────────────────────────────────────────────────
    #  Amplitude pump (main thread timer)
    # ─────────────────────────────────────────────────────────────────
    def _pump_amplitude(self):
        """Read the latest audio chunk and emit RMS amplitude to the waveform."""
        try:
            q = self.recorder.audio_queue
            if q is not None and not q.empty():
                # Peek at most-recent chunk (queue.Queue wraps a deque)
                chunk = q.queue[-1]
                if chunk is not None and len(chunk) > 0:
                    samples = chunk.astype(np.float32)
                    rms = np.sqrt(np.mean(samples ** 2))
                    normalised = min(1.0, rms / 8000.0)
                    self.signal_handler.set_amplitude.emit(normalised)
                    return
        except Exception:
            pass

        self.signal_handler.set_amplitude.emit(0.0)

    # ─────────────────────────────────────────────────────────────────
    #  Background processing (QThread + Worker)
    # ─────────────────────────────────────────────────────────────────
    def _process_audio(self, audio_data):
        """Spawn a QThread for STT + translation (does NOT block the UI)."""

        # Mark thread as busy — blocks _start_recording until we clear it
        self._thread_busy = True

        # Create worker + thread on the MAIN thread
        self._worker_thread = QThread()
        self._worker = Worker(audio_data, self.transcriber, self.translator)
        self._worker.moveToThread(self._worker_thread)

        # Wire signals
        self._worker_thread.started.connect(self._worker.run)

        # Worker → Controller
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.translation_finished.connect(self._on_conversion_success)
        self._worker.finished.connect(self._on_worker_finished)

        # Worker done → stop thread event loop
        self._worker.finished.connect(self._worker_thread.quit)
        # After thread fully stops → clear flag and refs
        self._worker_thread.finished.connect(self._on_thread_finished)

        # Go
        self._worker_thread.start()

    # ─────────────────────────────────────────────────────────────────
    #  Worker callbacks (all on main thread via queued connections)
    # ─────────────────────────────────────────────────────────────────
    def _on_worker_progress(self, text: str):
        """Update the overlay label with transcription/translation progress."""
        self.signal_handler.update_text.emit(text)

    def _on_conversion_success(self, translated_text: str):
        """
        Called when the Worker emits translation_finished.
          a) Transition overlay → COMPLETED (shows checkmark + 'Finished')
          b) Schedule text insertion after the overlay starts fading
        """
        print(f"✅ Translation complete: {translated_text}", flush=True)

        # Overlay → COMPLETED (auto-dismisses after 1.5 s internally)
        self.signal_handler.set_state.emit("completed")

        # Paste the translated text into the active app after a short delay
        # (Increased to 300ms to ensure focus has settled)
        QTimer.singleShot(
            300, lambda: self.output_handler.insert(translated_text)
        )

    def _on_worker_finished(self):
        """
        Fires when Worker.run() returns — the QThread is still tearing down.
        Only handles overlay state; do NOT null out thread refs here since
        the C++ QThread object hasn't fully stopped yet.
        """
        if self.overlay._state.name == "PROCESSING":
            QTimer.singleShot(
                500, lambda: self.signal_handler.hide_window.emit()
            )

    def _on_thread_finished(self):
        """
        Fires when the QThread has FULLY stopped (its event loop has exited).
        Only here is it safe to drop our Python references — the C++ objects
        are fully done.  Also clears _thread_busy so the next recording can start.
        """
        self._worker = None
        self._worker_thread = None
        self._thread_busy = False   # ← gate re-opens here


# ─────────────────────────  Entry Point  ─────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Ensure app doesn't quit when overlay hides
    app.setQuitOnLastWindowClosed(False)

    # ── Hide Dock Icon (macOS) ──
    # Setting this after QApplication initialization is more reliable 
    # as Qt can sometimes reset the activation policy during startup.
    try:
        import AppKit
        # NSApplicationActivationPolicyAccessory = 1 (Hide from dock, keep window capability)
        # NSApplicationActivationPolicyProhibited = 2 (Complete background agent)
        # We use 1 (Accessory) for better window visibility on macOS.
        AppKit.NSApplication.sharedApplication().setActivationPolicy_(1)
        print("Successfully set activation policy to Accessory (Hidden Dock Icon)", flush=True)
    except Exception as e:
        print(f"Failed to set activation policy: {e}", flush=True)

    controller = AppController()
    sys.exit(app.exec())
