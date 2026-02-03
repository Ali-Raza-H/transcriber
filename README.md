# Transcriber

Cross-platform, fully local transcription tool that converts **MP3** and **MP4** files into **plain text** (`.txt`) using the offline **faster-whisper** speech-to-text engine (no cloud APIs).

## Features

- Offline transcription with `faster-whisper` (local inference)
- Supports **MP3** input directly
- Supports **MP4** input (audio extracted automatically via FFmpeg)
- Outputs **plain text only** (`.txt`) - no timestamps, subtitles, or diarization
- Cross-platform paths via `pathlib` (Windows + Linux)
- Clean engine abstraction (future engines can be added without changing CLI logic)
- Interactive modern TUI menu (Textual) for prompts, settings, and system stats

## Requirements

- Python **3.10+**
- **FFmpeg** installed and available on `PATH` (used to extract/convert audio)
- Python deps are installed via `pip install -e .` (includes `psutil` and `textual`)

## Installation

### Windows

1. Install Python 3.10+
2. Install FFmpeg (see below)
3. From the project root (the folder containing `pyproject.toml`):

```powershell
pip install -e .
```

### Linux

1. Install Python 3.10+
2. Install FFmpeg (see below)
3. From the project root (the folder containing `pyproject.toml`):

```bash
pip install -e .
```

Install all dependencies (runtime + dev/test):

```bash
pip install -e ".[dev]"
```

Install dependencies only (does not install the `transcriber` CLI entrypoint):

```bash
pip install -r requirements.txt
```

## Installing FFmpeg

Transcriber uses FFmpeg to extract/convert audio.

### Windows

Pick one:

- Winget:
  ```powershell
  winget install Gyan.FFmpeg
  ```
- Chocolatey:
  ```powershell
  choco install ffmpeg
  ```

Verify:

```powershell
ffmpeg -version
```

### Linux

Examples (pick the one for your distro):

- Debian/Ubuntu:
  ```bash
  sudo apt-get update && sudo apt-get install -y ffmpeg
  ```
- Fedora:
  ```bash
  sudo dnf install -y ffmpeg
  ```
- Arch:
  ```bash
  sudo pacman -S ffmpeg
  ```

Verify:

```bash
ffmpeg -version
```

## Usage

Launch the interactive menu (default when no args):

```bash
transcriber
```

Launch the menu explicitly:

```bash
transcriber menu
```

Show all available commands:

```bash
transcriber --help
```

Show help for the `run` command:

```bash
transcriber run --help
```

Run tests:

```bash
transcriber test
```

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

Enable verbose logging:

```bash
transcriber run input.mp3 --verbose
```

Run without installing (from the `transcriber/` folder):

```bash
python -m app.main run input.mp3
```

### Command reference

`transcriber run`:

- Argument: `INPUT_FILE` (required) - path to an `.mp3` or `.mp4` file
- Options:
  - `-o, --out DIR` - output directory (defaults to the input file's directory)
  - `--model MODEL` - model size/name or local model directory (defaults to config; `small` by default)
  - `--device DEVICE` - inference device (defaults to config; `cpu` by default)
  - `--verbose` - enable debug logging
  - `--help` - show help

`transcriber menu`:

- Launches the modern TUI menu (Textual-based flow for transcription, settings, and system stats)

`transcriber test`:

- Runs the test suite (requires dev deps)

### Output behavior

- Output files are written as `<input-stem>.txt` (example: `meeting.mp4` -> `meeting.txt`).
- By default, output is placed next to the input file unless `--out` is provided.

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

- CLI options override config values (for example, `--model` overrides `[engine].model`).
- Only `.txt` output is supported; if `[output].extension` is set to anything else, Transcriber will error.

## Offline model notes

Transcriber runs inference fully offline. However, if you pass a model **name** (like `small`), `faster-whisper` may download model files the first time it's used unless the model is already cached.

For strictly offline environments:

- Download the model once ahead of time (while online), or
- Set `--model` (or `[engine].model`) to a local model directory path.

## Whisper model sizes

Approximate guide (trade-offs vary by hardware and audio quality):

| Model  | Relative speed | Relative accuracy | Typical CPU RAM |
|--------|-----------------|-------------------|-----------------|
| tiny   | fastest         | lowest            | low             |
| base   | fast            | low               | low             |
| small  | medium          | good              | medium          |
| medium | slow            | better            | higher          |
| large  | slowest         | best              | highest         |

Default: `small`.

## Project structure

```text
transcriber/
|-- app/        # entry point, CLI, config, logging
|-- engine/     # engine interface + faster-whisper implementation
|-- media/      # MP3/MP4 handling and FFmpeg integration
|-- output/     # plain text output writer
|-- tests/      # unit tests (no model downloads required)
|-- pyproject.toml
|-- README.md
|-- LICENSE
`-- .gitignore
```

## Development roadmap

- Add a TUI (terminal UI) for browsing media files and managing transcription jobs
- Add progress reporting and better UX around long transcriptions
- Add additional offline engines behind the same engine interface

## Development commands

Install dev dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

## License

MIT License. See `LICENSE`.

## GitHub setup (first time)

1. Create an empty repository on GitHub:
   `https://github.com/<your-username>/transcriber`

2. Initialize git locally and push (replace placeholders):

```bash
git init  # if you already have a .git folder, skip this
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/transcriber.git
git push -u origin main
```
