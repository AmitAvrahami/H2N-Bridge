
# H2N Bridge

**Hebrew-to-English Real-Time Translation Bridge**

H2N Bridge is a desktop utility that listens for a global hotkey, records Hebrew speech, transcribes it locally (using `faster-whisper`), translates it to English (using Groq LLM), and automatically pastes the result into your active application.

## Features

- **Global Hotkey**: Toggle recording from anywhere (Default: `Ctrl+K`).
- **Floating Overlay**: Minimalist UI showing recording status and audio visualization.
- **Local Transcription**: Fast and private speech-to-text using `faster-whisper`.
- **Smart Translation**: Context-aware translation using Groq's Llama 3 models.
- **Auto-Paste**: Inserts text directly into your workflow.

## Installation

1. **Clone the repository**:

    ```bash
    git clone https://github.com/yourusername/h2n-bridge.git
    cd h2n-bridge
    ```

2. **Set up Virtual Environment**:

    ```bash
    python3.11 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3. **Configuration**:
    Create a `.env` file in the project root:

    ```bash
    GROQ_API_KEY=gsk_your_groq_api_key_here
    ```

## Usage

### Running the Application

Use the provided helper script to handle environment paths correctly:

```bash
./run.sh
```

Or run manually as a module:

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python -m h2n_bridge.main
```

### workflow

1. Focus on a text field (e.g., Slack, Notepad, Browser).
2. Press **Ctrl+K** (or whatever is configured).
3. Speak in Hebrew.
4. Press **Ctrl+K** again to stop.
5. Watch the overlay process the audio and paste the English translation.

## Development

The project uses a standard `src`-layout.

- **Source Code**: `src/h2n_bridge/`
- **Tests**: `tests/`
- **Scripts**: `scripts/`
- **Documentation**: `docs/`

### Running Tests

```bash
pytest tests/
```

### Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a detailed technical overview.
