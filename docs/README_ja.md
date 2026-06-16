# Bili-Streamer

Bilibiliライブ配信を管理するクロスプラットフォームツール。Bilibili LiveHime互換のPC APIを使用し、配信の開始・停止、カテゴリ変更、タイトル更新をGUIとCLIの両方で操作できます。

**[English](../README.md) | [中文](README_zh.md)**

---

## 機能

- **QRコードログイン** — Bilibiliアプリでスキャンして認証
- **ワンクリック配信制御** — 開始・停止をボタン一つで
- **カテゴリ選択** — ツリー表示で簡単選択、前回の選択を記憶
- **タイトル管理** — 前回使用したタイトルを自動保存
- **LiveHime PC API** — 現行のPC互換ライブ制御フローを使用
- **デュアルインターフェース** — PyQt6 GUI またはコマンドライン

## 動作環境

- Python 3.11+
- 依存パッケージ：`requests`、`qrcode[pil]`、`Pillow`、`PyQt6`

## インストール

```bash
git clone https://github.com/WIndFate/Bili-Streamer.git
cd Bili-Streamer
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 使い方

### GUI（推奨）

```bash
python gui.py
```

### コマンドライン

```bash
# 対話式で配信開始
python bilibili_stream.py

# タイトル指定で配信開始
python bilibili_stream.py -t "配信タイトル"

# 強制再開始
python bilibili_stream.py -r

# カテゴリ変更（配信中）
python bilibili_stream.py -c

# 配信停止
python bilibili_stream.py -q

# 全カテゴリ一覧
python bilibili_stream.py -l
```

## ダウンロード

[Releases](https://github.com/WIndFate/Bili-Streamer/releases) ページから **macOS** と **Windows** の実行ファイルをダウンロードできます。Pythonのインストールは不要です。

## ソースからビルド

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "Bili-Streamer" gui.py
```

出力は `dist/` フォルダに生成されます。

## 免責事項

本ツールは**個人的な学習・研究目的のみ**を対象としています。使用は自己責任で行ってください。本ツールの使用により生じたアカウント制限について、作者は一切の責任を負いません。

## ライセンス

MIT
