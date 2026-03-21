# Bili-Streamer

A cross-platform tool for managing Bilibili live streams. Simulates the official Android streaming client to start/stop broadcasts, change stream categories, and update titles — with both a GUI and CLI interface.

**[中文](#中文) | [日本語](#日本語)**

---

## Features

- **QR Code Login** — Scan with the Bilibili app to authenticate
- **Start / Stop Live** — One-click broadcast control
- **Category Selection** — Tree-view picker for stream categories with history
- **Title Management** — Auto-remembers your last used title
- **Device Fingerprint** — Persistent, realistic device identity to reduce risk
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

## Build Standalone Executable

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
└── .gitignore
```

## Disclaimer

This tool is for **personal and educational use only**. Use at your own risk. The author is not responsible for any account restrictions that may result from using this tool.

## License

MIT

---

<a id="中文"></a>

## 中文

# Bili-Streamer

跨平台的B站直播管理工具。模拟官方 Android 直播姬客户端，支持开播/停播、切换分区、修改标题，提供 GUI 图形界面和命令行两种使用方式。

### 功能

- **扫码登录** — 使用B站APP扫码即可登录
- **一键开播/停播** — 简单的直播控制
- **分区选择** — 树形分区列表，自动记忆上次选择
- **标题管理** — 自动保存上次使用的标题
- **设备指纹** — 持久化的真实设备标识，降低风控风险
- **双界面** — PyQt6 图形界面或命令行

### 安装

```bash
git clone https://github.com/WIndFate/Bili-Streamer.git
cd Bili-Streamer
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 使用

```bash
# 图形界面（推荐）
python gui.py

# 命令行 - 交互式开播
python bilibili_stream.py

# 命令行 - 指定标题开播
python bilibili_stream.py -t "直播标题"

# 切换分区（直播中）
python bilibili_stream.py -c

# 停止直播
python bilibili_stream.py -q
```

### 打包为独立程序

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "Bili-Streamer" gui.py
```

生成的文件在 `dist/` 目录下。

### 免责声明

本工具仅供**个人学习和研究使用**，使用风险自负。作者不对因使用本工具导致的任何账号限制承担责任。

---

<a id="日本語"></a>

## 日本語

# Bili-Streamer

Bilibiliライブ配信を管理するクロスプラットフォームツール。公式Androidクライアントをシミュレートし、配信の開始・停止、カテゴリ変更、タイトル更新をGUIとCLIの両方で操作できます。

### 機能

- **QRコードログイン** — Bilibiliアプリでスキャンして認証
- **ワンクリック配信制御** — 開始・停止をボタン一つで
- **カテゴリ選択** — ツリー表示で簡単選択、前回の選択を記憶
- **タイトル管理** — 前回使用したタイトルを自動保存
- **デバイスフィンガープリント** — リスク軽減のための永続的なデバイスID
- **デュアルインターフェース** — PyQt6 GUI またはコマンドライン

### インストール

```bash
git clone https://github.com/WIndFate/Bili-Streamer.git
cd Bili-Streamer
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 使い方

```bash
# GUI（推奨）
python gui.py

# CLI - 対話式で配信開始
python bilibili_stream.py

# CLI - タイトル指定で配信開始
python bilibili_stream.py -t "配信タイトル"

# カテゴリ変更（配信中）
python bilibili_stream.py -c

# 配信停止
python bilibili_stream.py -q
```

### スタンドアロン実行ファイルのビルド

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "Bili-Streamer" gui.py
```

出力は `dist/` フォルダに生成されます。

### 免責事項

本ツールは**個人的な学習・研究目的のみ**を対象としています。使用は自己責任で行ってください。本ツールの使用により生じたアカウント制限について、作者は一切の責任を負いません。
