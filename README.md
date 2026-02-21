# H2N Bridge

<div align="center">
  <h3>Hebrew-to-English Real-Time Translation Bridge</h3>
  <p>An advanced, low-latency desktop utility for macOS that captures Hebrew speech, transcribes it locally, translates it to English using LLMs, and seamlessly injects the result into your active workflow.</p>
</div>

---

## 📖 Overview

H2N Bridge is an intrusive, floating-widget desktop application designed for power users who frequently switch between Hebrew thoughts and English typing. Initiated by a customizable global hotkey, the application records audio directly from the system microphone, transcribes it privately on-device using `faster-whisper`, translates the Hebrew context into fluent English via the Groq Llama-3 API, and securely auto-pastes the text into whichever window is currently active.

## ✨ Core Features & Interface

* **Pristine Overlay Interface (PyQt6)**: Features a minimalist, frameless, and purely-painted `QWidget` overlay that remains always-on-top. It utilizes a custom state machine (Hidden → Listening → Processing → Completed) with dynamic fading (`windowOpacity`), a simulated voice waveform, and fluid tick-mark animations, completely avoiding macOS window compositing artifacts.
* **Settings Dashboard**: A clean UI to manage user preferences, including a dynamic hotkey recorder that intercepts and saves combinations safely.
* **Native Global Hotkeys**: Implements low-level macOS API hooks (`AppKit`/`PyObjC`) to guarantee hotkey registration outside the active application, circumventing common PyQt focus-stealing issues.
* **Smart Auto-Paste**: Integrates `pyperclip` paired with programmatic `Cmd+V` simulated keystrokes to instantly deliver text to the user's cursor.
* **Deep Hardware Mocking**: Built for stability—the testing suite completely stubs out hardware dependencies (microphones, clipboards, APIs) using `unittest.mock`.

## 🛠️ Technology Stack & Libraries

The architecture relies on a highly specialized stack for speed, local processing, and native OS integration:

### Core OS & UI

* **[PyQt6](https://riverbankcomputing.com/software/pyqt/)**: Drives the complex GUI overlay, the settings window, and, crucially, the application's underlying Event Loop and multi-threading architecture (`QThread` & `pyqtSignal`).
* **[PyObjC (AppKit)](https://pyobjc.readthedocs.io/)**: Provides deep macOS integrations. It is uniquely utilized here to instantiate an `NSEvent.addGlobalMonitorForEventsMatchingMask_handler_` loop, bypassing standard library limitations when capturing shortcuts while the Qt application is out-of-focus or hidden from the Dock.
* **[pynput](https://pynput.readthedocs.io/)**: Used strictly for executing the simulated keystrokes (`Cmd+V`) across the OS to perform the auto-paste, and serves as a fallback interface.

### Audio & AI Processing

* **[sounddevice](https://python-sounddevice.readthedocs.io/) & [numpy](https://numpy.org/)**: Captures raw audio streams from the hardware microphone in real-time, buffering PCM data efficiently without disk I/O.
* **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)**: CTranslate2-based implementation of OpenAI's Whisper. Runs entirely on-device to transcribe the captured Hebrew audio, prioritizing user privacy and zero-latency text chunking.
* **[Groq API](https://groq.com/)**: Connects to the ultra-fast Llama-3 70B models for context-aware, highly fluent language translation from Hebrew to English.

## 🖥️ Operating System Specifics (macOS Environment)

H2N Bridge is highly tailored and optimized for **macOS (Apple Silicon & Intel)**. Working with global hotkeys and transparent GUI overlays on macOS requires managing specific system protections:

1. **System Integrity Protection (SIP) & Accessibility**: The application must be granted permissions in *System Settings > Privacy & Security > Accessibility* and *Microphone* for the global hotkeys and audio recording to function.
2. **Qt Layer Backend (`QT_MAC_WANTS_LAYER`)**: macOS 13+ broke certain legacy rendering pipelines. The application bootstrap explicitly sets `export QT_MAC_WANTS_LAYER=1` to ensure the frameless, transparent overlay renders custom `QPainter` shapes correctly.
3. **Background Accessory Mode**: The primary `NSApplication` policy is forced to `1` (`NSApplicationActivationPolicyAccessory`). This hides the application icon from the macOS Dock and Cmd+Tab switcher, treating it as a true background daemon.

## 🏗️ Architecture & Folder Structure

The project strictly follows the modern Python **`src`-layout**, ensuring isolated namespaces, clean imports, and testability.

```text
draft/
├── config.json             # Runtime settings and hotkey maps
├── requirements.txt        # Pinned dependencies
├── run.sh                  # Safely bootstraps the environment
├── src/                    # Isolated Application Source
│   └── h2n_bridge/         
│       ├── __init__.py 
│       ├── main.py         # Application root, signal router, thread manager
│       ├── config.py       # Configuration parser
│       ├── components/     # Decoupled logical backend services
│       │   ├── audio.py           (Microphone stream management)
│       │   ├── mac_hotkeys.py     (PyObjC native listener)
│       │   ├── transcriber.py     (faster-whisper logic)
│       │   └── translator.py      (Groq LLM REST wrapper)
│       └── ui/             # Presentation layer
│           ├── overlay.py         (Pure-paint visual state machine)
│           └── settings.py        (User preference window)
└── tests/                  # Pytest suite with hardware mocks (41/41 passing)
```

**Thread Safety:** The `main.py` controller runs on the primary Qt GUI thread. Heavy blocking tasks (Audio Recording, AI Transcription, LLM Network requests) are strictly delegated to a background `QThread` (the `Worker` class). Communication between the background worker and the UI elements is handled asynchronously via thread-safe `pyqtSignal` events, preventing the famed "beachball of death".

## 🚀 Installation & Build

### Prerequisites

* macOS 13+ (Ventura or newer recommended)
* Python 3.11+

### Setup

1. Clone the repository and navigate to the root directory.
2. Initialize and activate a virtual environment:

   ```bash
   python3.11 -m venv .venv311
   source .venv311/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Define your Groq API key in a `.env` file or export it:

   ```bash
   export GROQ_API_KEY="gsk_your_key_here"
   ```

### Running the Application

Always use the bootstrap wrapper to ensure macOS Qt variables are set:

```bash
./run.sh
```

### Running the Test Suite

Tests execute securely without hitting physical APIs or requiring microphone permissions:

```bash
./.venv311/bin/python -m pytest tests/
```
