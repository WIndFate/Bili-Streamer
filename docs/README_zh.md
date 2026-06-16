# Bili-Streamer

跨平台的B站直播管理工具。使用兼容 B 站直播姬 PC 的接口，支持开播/停播、切换分区、修改标题，提供 GUI 图形界面和命令行两种使用方式。

**[English](../README.md) | [日本語](README_ja.md)**

---

## 功能

- **扫码登录** — 使用B站APP扫码即可登录
- **一键开播/停播** — 简单的直播控制
- **分区选择** — 树形分区列表，自动记忆上次选择
- **标题管理** — 自动保存上次使用的标题
- **直播姬 PC 接口** — 使用当前可用的 PC 兼容直播控制链路
- **双界面** — PyQt6 图形界面或命令行

## 环境要求

- Python 3.11+
- 依赖库：`requests`、`qrcode[pil]`、`Pillow`、`PyQt6`

## 安装

```bash
git clone https://github.com/WIndFate/Bili-Streamer.git
cd Bili-Streamer
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 使用方法

### 图形界面（推荐）

```bash
python gui.py
```

### 命令行

```bash
# 交互式开播
python bilibili_stream.py

# 指定标题开播
python bilibili_stream.py -t "直播标题"

# 强制重新开播
python bilibili_stream.py -r

# 切换分区（直播中）
python bilibili_stream.py -c

# 停止直播
python bilibili_stream.py -q

# 列出所有分区
python bilibili_stream.py -l
```

## 下载

可以在 [Releases](https://github.com/WIndFate/Bili-Streamer/releases) 页面直接下载 **macOS** 和 **Windows** 的可执行文件，无需安装 Python。

## 从源码打包

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "Bili-Streamer" gui.py
```

生成的文件在 `dist/` 目录下。

## 免责声明

本工具仅供**个人学习和研究使用**，使用风险自负。作者不对因使用本工具导致的任何账号限制承担责任。

## 许可证

MIT
