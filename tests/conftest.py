"""
conftest.py — Shared pytest fixtures for the H2N Bridge test suite.

All heavy imports (faster-whisper, groq, sounddevice, pynput) are mocked
at the module level via sys.modules so the test session never tries to load
real hardware-dependent libraries.
"""

import io
import os
import sys
import wave
import struct
from unittest.mock import MagicMock, patch

import pytest

# Add the src directory to the python path so tests can find h2n_bridge
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# ─────────────────────────────────────────────────────────────────────────────
# Stub out hardware / cloud dependencies BEFORE any src.* import
# ─────────────────────────────────────────────────────────────────────────────
def _make_stub(name):
    mod = MagicMock()
    sys.modules[name] = mod
    return mod

_make_stub("sounddevice")
_make_stub("pynput")
_make_stub("pynput.keyboard")
_make_stub("faster_whisper")
_make_stub("groq")
_make_stub("pyperclip")

# Ensure GROQ_API_KEY is set so Translator.__init__ doesn't raise
os.environ.setdefault("GROQ_API_KEY", "test-key-fixture")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def make_wav_buffer(duration_seconds: float = 0.1, sample_rate: int = 16000) -> io.BytesIO:
    """Return a minimal valid WAV buffer — no real audio hardware required."""
    num_samples = int(sample_rate * duration_seconds)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)          # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{num_samples}h", *([0] * num_samples)))
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def qapp():
    """
    Session-scoped QApplication — pytest-qt creates one automatically,
    but we expose it here so non-Qt tests that still need it can request it.
    """
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def dummy_wav():
    """A tiny silent WAV buffer (100 ms) representing captured audio."""
    return make_wav_buffer(0.1)


@pytest.fixture
def long_wav():
    """A 12-second silent WAV buffer to simulate a long recording."""
    return make_wav_buffer(12.0)


@pytest.fixture
def mock_transcriber():
    """
    A mock FasterTranscriber whose .transcribe() returns 'שלום עולם' by default.
    Override return_value in individual tests as needed.
    """
    m = MagicMock()
    m.transcribe.return_value = "שלום עולם"
    return m


@pytest.fixture
def mock_translator():
    """
    A mock Translator whose .translate() returns 'Hello World' by default.
    Override return_value or side_effect in individual tests as needed.
    """
    m = MagicMock()
    m.translate.return_value = "Hello World"
    return m


@pytest.fixture
def mock_output():
    """A mock OutputHandler.insert that records calls without touching the clipboard."""
    m = MagicMock()
    return m


@pytest.fixture
def signal_handler(qapp):
    """A real SignalHandler living on the main Qt thread."""
    from h2n_bridge.ui.overlay import SignalHandler
    return SignalHandler()


@pytest.fixture
def overlay(qtbot, signal_handler):
    """
    A real Overlay widget managed by qtbot (pytest-qt).
    Started hidden; tests can show/hide via signal_handler signals.
    """
    from h2n_bridge.ui.overlay import Overlay
    w = Overlay(signal_handler)
    qtbot.addWidget(w)
    return w
