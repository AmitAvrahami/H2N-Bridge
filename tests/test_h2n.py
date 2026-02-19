"""
test_h2n.py — Comprehensive Unit Test Suite for the H2N Bridge application.

Run with:
    pytest tests/test_h2n.py -v
    pytest tests/test_h2n.py -v --cov=src --cov-report=term-missing

Test Classes
------------
  TestWorkerLogic          — Worker QObject signal emission and error handling
  TestOverlayStateMachine  — UI label transitions (pytest-qt)
  TestTranslatorMocking    — Groq API: success, timeout, 401, 500, empty input
  TestAutoTypeLogic        — OutputHandler.insert passthrough
  TestEdgeCases            — Rapid-fire guard, empty audio, Hebrew encoding, noisy audio
"""

import io
import os
import sys
import time
import struct
import wave
from unittest.mock import MagicMock, patch, call, PropertyMock
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

class SignalCapture:
    """
    Lightweight signal spy that does NOT depend on pytest-qt.
    Connect it to any pyqtSignal:
        spy = SignalCapture()
        some_signal.connect(spy)
    """
    def __init__(self):
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)

    @property
    def count(self):
        return len(self.calls)

    @property
    def last_arg(self):
        return self.calls[-1][0] if self.calls else None


# ─────────────────────────────────────────────────────────────────────────────
# Class 1 — Worker Logic (no QThread needed — run() called directly)
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkerLogic:
    """
    Tests the Worker QObject in isolation.

    Worker.run() is called synchronously — no QThread is spawned.
    This lets us assert on signals without timer hacks, while still
    exercising the real Worker code path.
    """

    def _make_worker(self, mock_transcriber, mock_translator, audio_data=None):
        """Helper: import and instantiate Worker with provided mocks."""
        from h2n_bridge.main import Worker

        if audio_data is None:
            audio_data = io.BytesIO(b"fake-wav")

        worker = Worker(audio_data, mock_transcriber, mock_translator)

        # Attach signal spies
        worker._spy_progress = SignalCapture()
        worker._spy_finished = SignalCapture()
        worker._spy_translation = SignalCapture()

        worker.progress.connect(worker._spy_progress)
        worker.finished.connect(worker._spy_finished)
        worker.translation_finished.connect(worker._spy_translation)

        return worker

    # ── Happy path ───────────────────────────────────────────────────────────

    @patch("time.sleep")          # speed up deliberate sleeps in Worker
    def test_worker_success_emits_signals(self, _sleep, mock_transcriber, mock_translator, dummy_wav):
        """Translation succeeds → translation_finished carries the English string, finished fires once."""
        mock_transcriber.transcribe.return_value = "שלום עולם"
        mock_translator.translate.return_value = "Hello World"

        worker = self._make_worker(mock_transcriber, mock_translator, dummy_wav)
        worker.run()

        assert worker._spy_translation.count == 1
        assert worker._spy_translation.last_arg == "Hello World"
        assert worker._spy_finished.count == 1

    @patch("time.sleep")
    def test_worker_emits_progress_stages(self, _sleep, mock_transcriber, mock_translator, dummy_wav):
        """Worker emits 'Transcribing…' then 'Translating…' progress messages."""
        mock_transcriber.transcribe.return_value = "כן"
        mock_translator.translate.return_value = "Yes"

        worker = self._make_worker(mock_transcriber, mock_translator, dummy_wav)
        worker.run()

        progress_texts = [c[0] for c in worker._spy_progress.calls]
        assert "Transcribing…" in progress_texts
        assert "Translating…" in progress_texts

    # ── Empty audio ──────────────────────────────────────────────────────────

    @patch("time.sleep")
    def test_worker_empty_audio_skips_translation(self, _sleep, mock_transcriber, mock_translator, dummy_wav):
        """When STT returns empty string, translation is skipped and 'No speech detected.' is emitted."""
        mock_transcriber.transcribe.return_value = ""

        worker = self._make_worker(mock_transcriber, mock_translator, dummy_wav)
        worker.run()

        progress_texts = [c[0] for c in worker._spy_progress.calls]
        assert "No speech detected." in progress_texts
        assert worker._spy_translation.count == 0   # translate() must NOT be called
        assert worker._spy_finished.count == 1       # finished must still fire

    @patch("time.sleep")
    def test_worker_whitespace_only_audio_skips_translation(self, _sleep, mock_transcriber, mock_translator, dummy_wav):
        """A whitespace-only transcription is treated as empty — no translation attempted."""
        mock_transcriber.transcribe.return_value = "   "

        worker = self._make_worker(mock_transcriber, mock_translator, dummy_wav)
        worker.run()

        assert worker._spy_translation.count == 0
        assert worker._spy_finished.count == 1

    # ── Error handling ───────────────────────────────────────────────────────

    @patch("time.sleep")
    def test_worker_error_handling_api_exception(self, _sleep, mock_transcriber, mock_translator, dummy_wav):
        """
        If translator.translate() raises any exception,
        a 'failed' progress message is emitted that starts with 'Error:'
        and finished is still emitted (no crash).
        """
        mock_transcriber.transcribe.return_value = "שלום"
        mock_translator.translate.side_effect = Exception("API connection refused")

        worker = self._make_worker(mock_transcriber, mock_translator, dummy_wav)
        worker.run()

        progress_texts = [c[0] for c in worker._spy_progress.calls]
        error_messages = [t for t in progress_texts if t.startswith("Error:")]
        assert len(error_messages) >= 1, f"Expected at least one 'Error:...' message, got: {progress_texts}"
        assert worker._spy_translation.count == 0
        assert worker._spy_finished.count == 1

    @patch("time.sleep")
    def test_worker_error_handling_transcriber_exception(self, _sleep, mock_transcriber, mock_translator, dummy_wav):
        """If the transcriber itself raises, Worker catches it and emits an error progress + finished."""
        mock_transcriber.transcribe.side_effect = RuntimeError("Model crashed")

        worker = self._make_worker(mock_transcriber, mock_translator, dummy_wav)
        worker.run()

        progress_texts = [c[0] for c in worker._spy_progress.calls]
        assert any(t.startswith("Error:") for t in progress_texts)
        assert worker._spy_finished.count == 1

    @patch("time.sleep")
    def test_worker_finished_emitted_exactly_once_on_success(self, _sleep, mock_transcriber, mock_translator, dummy_wav):
        """finished signal must be emitted exactly once — not twice."""
        mock_transcriber.transcribe.return_value = "מה שלומך"
        mock_translator.translate.return_value = "How are you?"

        worker = self._make_worker(mock_transcriber, mock_translator, dummy_wav)
        worker.run()

        assert worker._spy_finished.count == 1, "finished must fire exactly once on success"

    @patch("time.sleep")
    def test_worker_finished_emitted_exactly_once_on_error(self, _sleep, mock_transcriber, mock_translator, dummy_wav):
        """finished signal must be emitted exactly once even when an error occurs."""
        mock_transcriber.transcribe.return_value = "שלום"
        mock_translator.translate.side_effect = TimeoutError("Groq timeout")

        worker = self._make_worker(mock_transcriber, mock_translator, dummy_wav)
        worker.run()

        assert worker._spy_finished.count == 1, "finished must fire exactly once on error"

    # ── Long duration simulation ─────────────────────────────────────────────

    @patch("time.sleep")
    def test_worker_long_translation_still_emits_signals(self, mock_sleep, mock_transcriber, mock_translator, long_wav):
        """
        Simulates a slow Groq response (>10 s) by controlling time.sleep.
        Worker must still emit translation_finished and finished.
        """
        mock_transcriber.transcribe.return_value = "אני צריך עזרה"

        # Simulate a slow API: translate() sleeps 12 seconds (mocked)
        def slow_translate(text):
            time.sleep(12)   # mocked — returns instantly
            return "I need help"

        mock_translator.translate.side_effect = slow_translate

        worker = self._make_worker(mock_transcriber, mock_translator, long_wav)
        worker.run()

        assert worker._spy_translation.last_arg == "I need help"
        assert worker._spy_finished.count == 1


# ─────────────────────────────────────────────────────────────────────────────
# Class 2 — Overlay UI State Machine  (requires pytest-qt / qtbot)
# ─────────────────────────────────────────────────────────────────────────────

class TestOverlayStateMachine:
    """
    Tests the Overlay widget state transitions by emitting signals through
    the SignalHandler and asserting on the QLabel text and OverlayState enum.
    """

    def test_ui_state_transitions(self, qtbot, overlay, signal_handler):
        """
        Comprehensive state-machine transition test:
        LISTENING → label "Translating…"
        PROCESSING → label "Processing…"
        COMPLETED → label "Finished"
        """
        from h2n_bridge.ui.overlay import OverlayState

        # → LISTENING
        signal_handler.set_state.emit("listening")
        qtbot.wait(50)
        assert overlay._label.text() == "Translating…", (
            f"Expected 'Translating…' in LISTENING state, got '{overlay._label.text()}'"
        )
        assert overlay._state == OverlayState.LISTENING

        # → PROCESSING
        signal_handler.set_state.emit("processing")
        qtbot.wait(50)
        assert overlay._label.text() == "Processing…", (
            f"Expected 'Processing…' in PROCESSING state, got '{overlay._label.text()}'"
        )
        assert overlay._state == OverlayState.PROCESSING

        # → COMPLETED
        signal_handler.set_state.emit("completed")
        qtbot.wait(50)
        assert overlay._label.text() == "Finished", (
            f"Expected 'Finished' in COMPLETED state, got '{overlay._label.text()}'"
        )
        assert overlay._state == OverlayState.COMPLETED

    def test_overlay_hidden_initially(self, overlay):
        """Overlay must start hidden (not visible)."""
        assert not overlay.isVisible(), "Overlay should be hidden at construction"

    def test_show_window_makes_overlay_visible(self, qtbot, overlay, signal_handler):
        """show_window signal makes the overlay visible."""
        signal_handler.show_window.emit()
        qtbot.wait(50)
        assert overlay.isVisible()

    def test_update_text_changes_label(self, qtbot, overlay, signal_handler):
        """update_text signal updates the main label text."""
        signal_handler.update_text.emit("Custom status message")
        qtbot.wait(30)
        assert overlay._label.text() == "Custom status message"

    def test_set_amplitude_calls_waveform(self, qtbot, overlay, signal_handler):
        """set_amplitude signal feeds the waveform widget without errors."""
        signal_handler.set_amplitude.emit(0.75)
        qtbot.wait(30)
        # Amplitude is clamped to [0, 1]; no exception = pass
        assert overlay._waveform._amplitude == pytest.approx(0.75, abs=0.01)

    def test_set_amplitude_clamped(self, qtbot, overlay, signal_handler):
        """Amplitude values > 1.0 or < 0.0 are clamped safely."""
        signal_handler.set_amplitude.emit(5.0)
        qtbot.wait(30)
        assert overlay._waveform._amplitude <= 1.0

        signal_handler.set_amplitude.emit(-1.0)
        qtbot.wait(30)
        assert overlay._waveform._amplitude >= 0.0

    def test_listening_shows_waveform_hides_shimmer(self, qtbot, overlay, signal_handler):
        """In LISTENING state, waveform is visible and shimmer is hidden."""
        signal_handler.set_state.emit("listening")
        qtbot.wait(50)
        assert overlay._waveform.isVisible()
        assert not overlay._shimmer.isVisible()

    def test_processing_shows_shimmer_hides_waveform(self, qtbot, overlay, signal_handler):
        """In PROCESSING state, shimmer widget is not hidden; waveform widget is hidden."""
        # Show the overlay first so child isVisible() checks work correctly
        signal_handler.show_window.emit()
        signal_handler.set_state.emit("processing")
        qtbot.wait(50)
        # Use isHidden() which reflects the widget's own hidden flag, independent of parent
        assert not overlay._shimmer.isHidden(), "Shimmer should not be hidden in PROCESSING state"
        assert overlay._waveform.isHidden(), "Waveform should be hidden in PROCESSING state"

    def test_completed_shows_checkmark(self, qtbot, overlay, signal_handler):
        """In COMPLETED state, the check_container widget is not hidden."""
        signal_handler.show_window.emit()
        signal_handler.set_state.emit("completed")
        qtbot.wait(50)
        assert not overlay._check_container.isHidden(), "check_container should not be hidden in COMPLETED state"

    def test_unknown_state_name_does_not_crash(self, qtbot, overlay, signal_handler):
        """An unrecognised state name must not raise — falls back to HIDDEN."""
        from h2n_bridge.ui.overlay import OverlayState
        signal_handler.set_state.emit("__invalid_state__")
        qtbot.wait(30)
        assert overlay._state == OverlayState.HIDDEN


# ─────────────────────────────────────────────────────────────────────────────
# Class 3 — Translator Mocking  (Groq API)
# ─────────────────────────────────────────────────────────────────────────────

class TestTranslatorMocking:
    """
    Tests the Translator class with a fully mocked Groq client.
    No real network calls are made.
    """

    @pytest.fixture
    def translator(self):
        """
        Instantiate Translator with a mocked Groq client.
        We patch groq.Groq (already in sys.modules as a MagicMock via conftest).
        """
        from h2n_bridge.components.translator import Translator
        t = Translator()
        # Replace the real (mock) client with a fresh MagicMock we control
        t.client = MagicMock()
        return t

    def _make_response(self, text: str):
        """Build a minimal fake Groq response object."""
        choice = MagicMock()
        choice.message.content = text
        response = MagicMock()
        response.choices = [choice]
        return response

    # ── Success ──────────────────────────────────────────────────────────────

    def test_translate_success(self, translator):
        """translate() returns the stripped English string from a successful API call."""
        translator.client.chat.completions.create.return_value = self._make_response("  Hello World  ")
        result = translator.translate("שלום עולם")
        assert result == "Hello World"

    def test_translate_preserves_content(self, translator):
        """translate() does not alter the returned content."""
        translator.client.chat.completions.create.return_value = self._make_response(
            "I'll check and get back to you."
        )
        result = translator.translate("אני אבדוק ואחזור אליך")
        assert result == "I'll check and get back to you."

    # ── Empty input ──────────────────────────────────────────────────────────

    def test_translate_empty_input_returns_empty(self, translator):
        """translate('') returns '' without ever calling the API."""
        result = translator.translate("")
        translator.client.chat.completions.create.assert_not_called()
        assert result == ""

    def test_translate_none_input_handled(self, translator):
        """translate(None) returns '' without crashing (defensive guard)."""
        result = translator.translate(None)
        assert result == ""

    # ── API errors ───────────────────────────────────────────────────────────

    def test_translate_timeout_returns_error_string(self, translator):
        """A timeout exception returns '[Error in Translation]' and does not raise."""
        import requests
        translator.client.chat.completions.create.side_effect = Exception("Connection timed out")
        result = translator.translate("שלום")
        assert result == "[Error in Translation]"

    def test_translate_401_authentication_error(self, translator):
        """A 401-like auth exception returns '[Error in Translation]'."""
        translator.client.chat.completions.create.side_effect = Exception(
            "401 Unauthorized: invalid api key"
        )
        result = translator.translate("שלום")
        assert result == "[Error in Translation]"

    def test_translate_500_server_error(self, translator):
        """A 500-like server exception returns '[Error in Translation]'."""
        translator.client.chat.completions.create.side_effect = Exception(
            "500 Internal Server Error"
        )
        result = translator.translate("שלום")
        assert result == "[Error in Translation]"

    def test_translate_api_down_no_network(self, translator):
        """An 'unreachable' style exception returns '[Error in Translation]'."""
        translator.client.chat.completions.create.side_effect = ConnectionError(
            "Network is unreachable"
        )
        result = translator.translate("שלום")
        assert result == "[Error in Translation]"


# ─────────────────────────────────────────────────────────────────────────────
# Class 4 — Auto-Type / Output Logic
# ─────────────────────────────────────────────────────────────────────────────

class TestAutoTypeLogic:
    """
    Tests OutputHandler.insert — verifying the correct string is passed
    to the clipboard and keyboard automation, without touching real hardware.
    """

    @pytest.fixture
    def output_handler(self):
        from h2n_bridge.components.output import OutputHandler
        return OutputHandler()

    @patch("pyperclip.copy")
    @patch("time.sleep")
    def test_auto_type_logic(self, _sleep, mock_copy, output_handler):
        """insert('Hello World') calls pyperclip.copy with exactly 'Hello World'."""
        with patch("pynput.keyboard.Controller") as MockController:
            output_handler.insert("Hello World")
        mock_copy.assert_called_once_with("Hello World")

    @patch("pyperclip.copy")
    @patch("time.sleep")
    def test_auto_type_empty_string_skipped(self, _sleep, mock_copy, output_handler):
        """insert('') must NOT copy anything to the clipboard."""
        output_handler.insert("")
        mock_copy.assert_not_called()

    @patch("pyperclip.copy")
    @patch("time.sleep")
    def test_auto_type_none_skipped(self, _sleep, mock_copy, output_handler):
        """insert(None) must NOT copy anything — defensively safe."""
        output_handler.insert(None)
        mock_copy.assert_not_called()

    @patch("pyperclip.copy")
    @patch("time.sleep")
    def test_auto_type_unicode_hebrew(self, _sleep, mock_copy, output_handler):
        """Hebrew text passes through insert() without UnicodeEncodeError."""
        hebrew = "שלום עולם"
        with patch("pynput.keyboard.Controller"):
            output_handler.insert(hebrew)
        mock_copy.assert_called_once_with(hebrew)

    @patch("pyperclip.copy")
    @patch("time.sleep")
    def test_auto_type_long_text(self, _sleep, mock_copy, output_handler):
        """Long translated text (>500 chars) is passed without truncation."""
        long_text = "This is a very long translation. " * 20
        with patch("pynput.keyboard.Controller"):
            output_handler.insert(long_text)
        actual = mock_copy.call_args[0][0]
        assert actual == long_text
        assert len(actual) == len(long_text)

    @patch("pyperclip.copy")
    @patch("time.sleep")
    def test_copy_to_clipboard_returns_true_on_success(self, _sleep, mock_copy, output_handler):
        """copy_to_clipboard() returns True when pyperclip.copy succeeds."""
        result = output_handler.copy_to_clipboard("test")
        assert result is True

    @patch("pyperclip.copy", side_effect=Exception("Clipboard unavailable"))
    def test_copy_to_clipboard_returns_false_on_error(self, _mock_copy, output_handler):
        """copy_to_clipboard() returns False (no crash) when pyperclip fails."""
        result = output_handler.copy_to_clipboard("test")
        assert result is False


# ─────────────────────────────────────────────────────────────────────────────
# Class 5 — Edge Cases
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """
    End-to-end edge case tests that exercise the interaction between
    multiple components.
    """

    # ── Empty audio ──────────────────────────────────────────────────────────

    @patch("time.sleep")
    def test_empty_audio_no_speech_emits_no_translation(self, _sleep, mock_transcriber, mock_translator, dummy_wav):
        """Empty audio → transcriber returns '' → no translation signal, no crash."""
        from h2n_bridge.main import Worker
        mock_transcriber.transcribe.return_value = ""

        worker = Worker(dummy_wav, mock_transcriber, mock_translator)
        finished_spy = SignalCapture()
        translation_spy = SignalCapture()
        worker.finished.connect(finished_spy)
        worker.translation_finished.connect(translation_spy)

        worker.run()

        assert translation_spy.count == 0
        assert finished_spy.count == 1
        mock_translator.translate.assert_not_called()

    # ── Rapid-fire hotkey guard ──────────────────────────────────────────────

    def test_rapid_fire_guard_blocks_second_recording(self, mock_transcriber, mock_translator):
        """
        Simulates a user pressing Ctrl+K twice in rapid succession while a
        QThread is still active.  _start_recording should return early the
        second time without spawning a second thread.
        """
        from unittest.mock import MagicMock, patch

        # We need a real QApplication for QTimer / QThread
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])

        # Stub out components that have hardware side-effects
        with patch("h2n_bridge.main.AudioRecorder") as MockAudio, \
             patch("h2n_bridge.main.FasterTranscriber") as MockTranscriber, \
             patch("h2n_bridge.main.Translator") as MockTranslator, \
             patch("h2n_bridge.main.OutputHandler") as MockOutput, \
             patch("h2n_bridge.main.SignalHandler") as MockSH, \
             patch("h2n_bridge.main.Overlay") as MockOverlay, \
             patch("threading.Thread"):   # don't start pynput listener

            from h2n_bridge.main import AppController
            ctrl = AppController()
            ctrl._thread_busy = True    # simulate: a thread is already running

            initial_thread = ctrl._worker_thread  # should be None still

            # Simulate a second hotkey press
            ctrl._start_recording()

            # _worker_thread must remain unchanged — no new thread spawned
            assert ctrl._worker_thread == initial_thread, (
                "_start_recording() should be a no-op when _thread_busy is True"
            )

    # ── Hebrew encoding ──────────────────────────────────────────────────────

    def test_hebrew_encoding_preserved_through_format(self):
        """
        Hebrew characters must survive Python string formatting operations
        without UnicodeEncodeError or data loss.
        """
        hebrew = "אני אבדוק ואחזור אליך"
        system_prompt_template = (
            "You are a translator. Translate: {text}"
        )
        formatted = system_prompt_template.format(text=hebrew)
        assert hebrew in formatted

    def test_hebrew_encoding_no_mangling(self):
        """Hebrew string identity is preserved end-to-end through encode/decode round-trip."""
        hebrew = "שלום עולם"
        encoded = hebrew.encode("utf-8")
        decoded = encoded.decode("utf-8")
        assert decoded == hebrew

    @patch("time.sleep")
    def test_hebrew_reaches_api_unchanged(self, _sleep, mock_transcriber, mock_translator, dummy_wav):
        """
        The exact Hebrew string from the transcriber is the string passed
        to translator.translate() — no mangling in Worker.
        """
        from h2n_bridge.main import Worker
        hebrew = "אני אבדוק ואחזור אליך"
        mock_transcriber.transcribe.return_value = hebrew
        mock_translator.translate.return_value = "I'll check and get back to you."

        worker = Worker(dummy_wav, mock_transcriber, mock_translator)
        worker.run()

        mock_translator.translate.assert_called_once_with(hebrew)

    # ── Noisy audio ──────────────────────────────────────────────────────────

    @patch("time.sleep")
    def test_noisy_audio_non_empty_attempts_translation(self, _sleep, mock_transcriber, mock_translator, dummy_wav):
        """
        When Whisper returns a non-empty 'noisy' string (e.g. '...' or music note chars),
        the Worker should still attempt translation — it does not filter non-Hebrew content.
        """
        from h2n_bridge.main import Worker
        noisy = "... ♪ ... ♪"
        mock_transcriber.transcribe.return_value = noisy
        mock_translator.translate.return_value = "[non-speech]"

        worker = Worker(dummy_wav, mock_transcriber, mock_translator)
        translation_spy = SignalCapture()
        worker.translation_finished.connect(translation_spy)
        worker.run()

        mock_translator.translate.assert_called_once_with(noisy)
        assert translation_spy.count == 1

    # ── API timeout simulation ────────────────────────────────────────────────

    @patch("time.sleep")
    def test_api_timeout_worker_recovers(self, _sleep, mock_transcriber, mock_translator, dummy_wav):
        """
        When the Groq API call times out (exception), Worker emits an
        'Error:' progress message and still emits finished — no hang.
        """
        from h2n_bridge.main import Worker
        mock_transcriber.transcribe.return_value = "שלום"
        mock_translator.translate.side_effect = TimeoutError("Read timed out.")

        worker = Worker(dummy_wav, mock_transcriber, mock_translator)
        finished_spy = SignalCapture()
        progress_spy = SignalCapture()
        worker.finished.connect(finished_spy)
        worker.progress.connect(progress_spy)
        worker.run()

        progress_texts = [c[0] for c in progress_spy.calls]
        assert any("Error:" in t for t in progress_texts)
        assert finished_spy.count == 1
