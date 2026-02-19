# H2N Bridge - Architecture Documentation

## System Overview

H2N Bridge is a **Hebrew-to-English Real-Time Translation** application designed for desktop use. It listens for a global hotkey, captures audio, transcribes it locally, translates it via an LLM, and pastes the result into the active application.

## High-Level Architecture

The application follows a **Controller-Worker** pattern with a **Floating UI Overlay**.

### Components

1. **AppController (`h2n_bridge.main`)**:
    - The central brain of the application.
    - Manages the application lifecycle (IDLE -> LISTENING -> PROCESSING -> COMPLETED).
    - Handles global hotkeys via `pynput` (on a daemon thread) and bridges them to the Main Qt Thread.
    - Manages the UI Overlay.

2. **Worker (`h2n_bridge.main.Worker`)**:
    - Runs on a background `QThread` to prevent UI freezing.
    - Performs the heavy lifting:
        - **Transcription**: Uses `faster-whisper` to convert audio to Hebrew text.
        - **Translation**: Sends the text to Groq API for translation to English.
    - Emits signals (`progress`, `translation_finished`, `finished`) back to the Controller.

3. **UI Overlay (`h2n_bridge.ui.overlay`)**:
    - A transparent, always-on-top widget.
    - Visualizes the application state:
        - **Mic Icon**: Listening mode.
        - **Waveform**: Real-time audio amplitude visualization.
        - **Spinner/Shimmer**: Processing state.
        - **Checkmark**: Completion state.

4. **AudioRecorder (`h2n_bridge.components.audio`)**:
    - Uses `sounddevice` and `numpy` to capture high-quality audio.
    - Detects voice activity and silence silence.

5. **OutputHandler (`h2n_bridge.components.output`)**:
    - Pastes the final text into the active window using `pyperclip` (clipboard) and `pynput` (simulating Ctrl+V).

## Directory Structure

The project uses a standard `src`-layout:

```text
project_root/
├── docs/                     # Documentation
│   └── ARCHITECTURE.md
├── scripts/                  # Utility scripts (setup checks, stress tests)
├── src/
│   └── h2n_bridge/           # Main Package
│       ├── __init__.py
│       ├── main.py           # Entry point
│       ├── config.py         # Configuration (keys, models)
│       ├── components/       # Logic modules (audio, stt, translation)
│       └── ui/               # Qt Widgets
├── tests/                    # Pytest suite
└── run.sh                    # Launcher script
```

## Threading Model

- **Main Thread**: Runs the Qt Event Loop. All UI updates **must** happen here.
- **GlobalHotKeys Thread**: A daemon thread spawned by `pynput`. It **never** touches the UI directly. It emits a signal via `HotkeyBridge` which is connected to the Main Thread via a `Qt.QueuedConnection`.
- **Worker Thread**: Ephemeral `QThread` spawned when processing audio. Handles network requests and heavy computation.

## Setup & Deployment

### Prerequisites

- Python 3.11+
- FFmpeg (for `faster-whisper`)
- Groq API Key

### Installation

1. Create a virtual environment: `python -m venv .venv`
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in `.env`:

    ```
    GROQ_API_KEY=gsk_...
    ```

### Running

Use the provided script to ensure `PYTHONPATH` and Qt plugins are set up correctly:

```bash
./run.sh
```

Or manually:

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python -m h2n_bridge.main
```
