# CLAUDE.md

## Project Overview

Bili-Streamer is a cross-platform Bilibili live stream management tool that simulates the official Android BiliLive client. It provides both a PyQt6 GUI and a CLI interface.

## Architecture

- `bilibili_stream.py` — Core API layer. All Bilibili API interactions live here (login, start/stop live, category/title management, device fingerprint). Both GUI and CLI consume this as a library.
- `gui.py` — PyQt6 GUI application. Imports functions from `bilibili_stream.py`. All network calls run in `QThread` workers to keep the UI responsive.
- `bili_config/` — Runtime config directory. `config.json` (credentials, gitignored), `device.json` (fingerprint, gitignored), `settings.json` (preferences, tracked).

## Key Design Decisions

- **Single global DeviceFingerprint instance** — accessed via `get_device_fp()` singleton. All functions share the same device identity for consistency.
- **Single global requests.Session** — accessed via `get_http_session()`. Reuses TCP connections and enforces 30s default timeout.
- **Device fingerprint is persisted to `device.json`** — generated once, reused across sessions. All header fields (BUVID, Display-ID, Session-ID, network type) are stable per device.
- **BUVID format** — must be `XX` + 32-char lowercase hex (MD5). Never use `random.sample` with uppercase chars.
- **Build number consistency** — all API calls must read `build` from `device_fp.fingerprint["build_number"]`, never hardcode.

## Anti-Detection / Risk Control Rules

These are critical for avoiding account bans:

- Never randomize per-request fields that real clients keep stable (Display-ID, Session-ID, network type in UA)
- User-Agent must not contain identifiable third-party markers (no hardcoded emails, tool names)
- Use `except Exception:` not bare `except:` — bare except catches KeyboardInterrupt/SystemExit
- All HTTP requests must go through `get_http_session()` with timeout
- APP_KEY `1d8b6e7d45233436` and APP_SECRET are the standard Android client keys — do not change unless Bilibili revokes them

## Development Commands

```bash
# Activate virtual environment
source venv/bin/activate   # Windows: venv\Scripts\activate

# Run GUI
python gui.py

# Run CLI
python bilibili_stream.py

# Syntax check
python -c "import py_compile; py_compile.compile('bilibili_stream.py', doraise=True)"
python -c "import py_compile; py_compile.compile('gui.py', doraise=True)"

# Build standalone executable
pip install pyinstaller
pyinstaller --onefile --windowed --name "Bili-Streamer" gui.py
```

## Sensitive Files (gitignored)

- `bili_config/config.json` — contains SESSDATA, bili_jct cookies
- `bili_config/device.json` — contains device fingerprint

Never commit these files. Never log cookie values in print/log output.
