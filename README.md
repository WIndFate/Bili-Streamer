# Bili-Streamer

A cross-platform tool for managing Bilibili live streams. Uses Bilibili LiveHime-compatible PC APIs to start/stop broadcasts, change stream categories, and update titles — with both a GUI and CLI interface.

**[中文文档](docs/README_zh.md) | [日本語ドキュメント](docs/README_ja.md)**

---

## Features

- **QR Code Login** — Scan with the Bilibili app to authenticate
- **Start / Stop Live** — One-click broadcast control
- **Category Selection** — Tree-view picker for stream categories with history
- **Title Management** — Auto-remembers your last used title
- **LiveHime PC API** — Uses the current PC-compatible live control flow
- **Dual Interface** — PyQt6 GUI or command-line

## Screenshots

> *Coming soon*

## Requirements

- Python 3.11+
- Dependencies: `requests`, `qrcode[pil]`, `Pillow`, `PyQt6`

## Installation

```bash
git clone https://github.com/WIndFate/Bili-Streamer.git
cd Bili-Streamer
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### GUI (Recommended)

```bash
python gui.py
```

### CLI

```bash
# Start stream (interactive)
python bilibili_stream.py

# Start with specific title
python bilibili_stream.py -t "Stream Title"

# Force restart stream
python bilibili_stream.py -r

# Change category while live
python bilibili_stream.py -c

# Stop stream
python bilibili_stream.py -q

# List all categories
python bilibili_stream.py -l
```

## Download

Pre-built executables for **macOS** and **Windows** are available on the [Releases](https://github.com/WIndFate/Bili-Streamer/releases) page. No Python installation required.

## Build from Source

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "Bili-Streamer" gui.py
```

The output will be in the `dist/` folder.

## Project Structure

```
├── gui.py                  # PyQt6 GUI application
├── bilibili_stream.py      # Core API layer (CLI + library)
├── requirements.txt        # Python dependencies
├── bili_config/
│   └── settings.json       # Saved preferences (category, title)
├── docs/
│   ├── README_zh.md        # 中文文档
│   └── README_ja.md        # 日本語ドキュメント
└── .gitignore
```

## Disclaimer

This tool is for **personal and educational use only**. Use at your own risk. The author is not responsible for any account restrictions that may result from using this tool.

## License

MIT
