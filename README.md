# Transcriber

Production-quality, cross-platform, fully local transcription tool that converts **MP3** and **MP4** files into **plain text** (`.txt`) using the offline **faster-whisper** speech-to-text engine (no cloud APIs).

## Features

- Offline transcription with `faster-whisper`
- Supports **MP3** (direct input) and **MP4** (audio extracted automatically)
- Outputs **plain text only** (`.txt`) — no timestamps, subtitles, or diarization
- Cross-platform paths via `pathlib` (Windows + Linux)
- Clean engine abstraction (future engines can be added without changing CLI logic)

## Requirements

- Python **3.10+**
- **FFmpeg** installed and available on `PATH` (used to extract/convert audio)
- Whisper model files available locally (downloaded automatically on first use if missing)

## Offline notes (models)

Transcriber runs inference fully offline. If you pass a model **name** (like `small`), `faster-whisper` will download the model the first time it’s used *unless it’s already cached*. For strictly offline environments, pre-download the model once (while online) or set `--model` (or `[engine].model`) to a local model directory.

## Installation

### 1) Install FFmpeg

Windows (pick one):

- Winget: `winget install Gyan.FFmpeg`
- Chocolatey: `choco install ffmpeg`

Linux (examples):

- Debian/Ubuntu: `sudo apt-get update && sudo apt-get install -y ffmpeg`
- Fedora: `sudo dnf install -y ffmpeg`
- Arch: `sudo pacman -S ffmpeg`

Verify:

```bash
ffmpeg -version
```

### 2) Install Transcriber (editable)

From the project root:

```bash
pip install -e .
```

## Usage

Transcribe a single file:

```bash
transcriber run input.mp3
```

Specify output directory:

```bash
transcriber run input.mp4 --out ./transcripts
```

Specify model size:

```bash
transcriber run input.mp3 --model small
```

Override device (optional):

```bash
transcriber run input.mp3 --device cpu
```

### Output behavior

- Output files are written as `<input-stem>.txt` (e.g., `meeting.mp4` → `meeting.txt`).
- By default, the output is placed next to the input file unless `--out` is provided.

## Configuration (TOML)

Transcriber loads an optional TOML config file:

- Linux: `~/.config/transcriber/config.toml`
- Windows: `%APPDATA%\\transcriber\\config.toml`

Example:

```toml
[engine]
model = "small"
device = "cpu"

[output]
extension = "txt"
```

Notes:

- CLI options override config values (e.g., `--model` overrides `[engine].model`).
- Only `.txt` output is supported; if `[output].extension` is set to anything else, Transcriber will error.

## Whisper model sizes

Approximate guide (trade-offs vary by hardware and audio quality):

| Model | Size (params) | Speed | Accuracy |
|------:|---------------:|:------|:---------|
| tiny  | ~39M  | Fastest | Lowest |
| base  | ~74M  | Faster  | Low |
| small | ~244M | Medium  | Good |
| medium| ~769M | Slower  | Better |
| large | ~1550M| Slowest | Best |

Default: `small`.

## Project structure

```
transcriber/
├── app/
│   ├── __init__.py
│   ├── main.py          # entry point
│   ├── cli.py           # argument parsing
│   ├── config.py        # config handling
│   └── logging.py
├── engine/
│   ├── __init__.py
│   ├── base.py          # transcription engine interface
│   └── faster_whisper.py
├── media/
│   ├── __init__.py
│   └── audio.py         # mp3/mp4 handling and ffmpeg integration
├── output/
│   ├── __init__.py
│   └── text.py
├── tests/
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

## Development roadmap

- Add a **TUI (terminal UI)** for browsing media files and managing transcription jobs
- Add progress reporting and better UX around long transcriptions
- Add additional offline engines behind the same engine interface

## GitHub setup (first time)

1) Create an empty repository on GitHub:

- `https://github.com/<your-username>/transcriber`

2) Initialize git locally and push:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/transcriber.git
git push -u origin main
```

## License

MIT License. See `LICENSE`.
