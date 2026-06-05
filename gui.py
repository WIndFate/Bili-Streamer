import sys
import io
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QDialog, QMessageBox, QSplitter, QGroupBox, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage, QFont, QColor, QIcon
import qrcode
from PIL import Image as PILImage

import bilibili_stream as api


# ──────────────────────────────────────────────
# Worker threads for non-blocking network calls
# ──────────────────────────────────────────────

class LoginPollWorker(QThread):
    """Poll QR code login status in background"""
    status_changed = pyqtSignal(int, str)   # code, message
    login_success = pyqtSignal(dict)        # cookies dict

    def __init__(self, qrcode_key):
        super().__init__()
        self.qrcode_key = qrcode_key
        self._running = True

    def run(self):
        status_msgs = {
            0: "登录成功",
            86101: "等待扫码...",
            86090: "已扫码，请在手机上确认",
            86038: "二维码已失效",
        }
        last_code = None
        while self._running:
            try:
                result = api.check_login_status(self.qrcode_key)
                code = result["code"]
                if code != last_code:
                    last_code = code
                    self.status_changed.emit(code, status_msgs.get(code, f"未知状态: {code}"))
                if code == 0:
                    self.login_success.emit(result["cookies"])
                    return
                if code == 86038:
                    return
            except Exception as e:
                self.status_changed.emit(-1, f"网络错误: {e}")
            self.msleep(2000)

    def stop(self):
        self._running = False


class ApiWorker(QThread):
    """Run an arbitrary API call in background"""
    finished = pyqtSignal(object)  # result
    error = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ──────────────────────────────────────────────
# Login dialog with QR code
# ──────────────────────────────────────────────

class LoginDialog(QDialog):
    """QR code scan login dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("扫码登录")
        self.setFixedSize(320, 400)
        self.cookies = None
        self.poll_worker = None

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("请使用B站APP扫描二维码")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("", 13, QFont.Weight.Bold))
        layout.addWidget(title)

        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setFixedSize(250, 250)
        layout.addWidget(self.qr_label)

        self.status_label = QLabel("正在生成二维码...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        # Start QR generation in background
        self.gen_worker = ApiWorker(api.generate_qrcode)
        self.gen_worker.finished.connect(self._on_qr_generated)
        self.gen_worker.error.connect(lambda e: self.status_label.setText(f"生成失败: {e}"))
        self.gen_worker.start()

    def _on_qr_generated(self, qr_info):
        url = qr_info["url"]
        qrcode_key = qr_info["qrcode_key"]

        # Generate QR image
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L,
                            box_size=8, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        pil_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        # PIL -> QPixmap
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        qimage = QImage.fromData(buf.getvalue())
        pixmap = QPixmap.fromImage(qimage).scaled(
            250, 250, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        self.qr_label.setPixmap(pixmap)
        self.status_label.setText("等待扫码...")

        # Start polling
        self.poll_worker = LoginPollWorker(qrcode_key)
        self.poll_worker.status_changed.connect(self._on_status)
        self.poll_worker.login_success.connect(self._on_login_ok)
        self.poll_worker.start()

    def _on_status(self, code, msg):
        self.status_label.setText(msg)
        if code == 86038:
            self.status_label.setText("二维码已失效，请重新打开登录窗口")

    def _on_login_ok(self, cookies):
        self.cookies = cookies
        uid = int(cookies["DedeUserID"])
        # Save config
        config = api.ConfigManager(uid)
        config.update(cookies)
        config = api.ConfigManager(0)
        config.update(cookies)
        self.accept()

    def reject(self):
        if self.poll_worker:
            self.poll_worker.stop()
            self.poll_worker.wait(2000)
        super().reject()


# ──────────────────────────────────────────────
# Main window
# ──────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("B站直播工具")
        self.setMinimumSize(750, 520)
        self.resize(800, 560)

        self.cookie_str = None
        self.uid = None
        self.room_id = None
        self.is_live = False
        self.selected_area_id = None
        self.selected_area_name = None
        self._workers = []  # prevent GC

        self._build_ui()
        self._try_auto_login()

    # ── UI Construction ──

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 10, 10, 10)

        # --- Top: info bar ---
        info_box = QGroupBox("账号信息")
        info_layout = QHBoxLayout(info_box)
        self.uid_label = QLabel("UID: 未登录")
        self.room_label = QLabel("直播间: -")
        self.status_indicator = QLabel("● 未登录")
        self.status_indicator.setStyleSheet("color: gray; font-weight: bold;")
        self.login_btn = QPushButton("登录")
        self.login_btn.setFixedWidth(70)
        self.login_btn.clicked.connect(self._do_login)
        info_layout.addWidget(self.uid_label)
        info_layout.addWidget(self.room_label)
        info_layout.addStretch()
        info_layout.addWidget(self.status_indicator)
        info_layout.addWidget(self.login_btn)
        root_layout.addWidget(info_box)

        # --- Middle: splitter (area tree | controls) ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: area tree
        left_box = QGroupBox("分区选择")
        left_layout = QVBoxLayout(left_box)
        self.area_tree = QTreeWidget()
        self.area_tree.setHeaderLabels(["分区名称", "ID"])
        self.area_tree.setColumnWidth(0, 180)
        self.area_tree.itemClicked.connect(self._on_area_selected)
        left_layout.addWidget(self.area_tree)
        refresh_area_btn = QPushButton("刷新分区列表")
        refresh_area_btn.clicked.connect(self._load_areas)
        left_layout.addWidget(refresh_area_btn)
        splitter.addWidget(left_box)

        # Right: controls + log
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Title input
        title_group = QGroupBox("直播标题")
        title_layout = QHBoxLayout(title_group)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("输入直播标题...")
        title_layout.addWidget(self.title_input)
        right_layout.addWidget(title_group)

        # Action buttons
        btn_group = QGroupBox("操作")
        btn_layout = QHBoxLayout(btn_group)

        self.start_btn = QPushButton("开始直播")
        self.start_btn.setStyleSheet("QPushButton { background-color: #00a1d6; color: white; padding: 8px; font-weight: bold; border-radius: 4px; }"
                                     "QPushButton:hover { background-color: #0090c0; }"
                                     "QPushButton:disabled { background-color: #cccccc; }")
        self.start_btn.clicked.connect(self._do_start_live)

        self.stop_btn = QPushButton("停止直播")
        self.stop_btn.setStyleSheet("QPushButton { background-color: #fb7299; color: white; padding: 8px; font-weight: bold; border-radius: 4px; }"
                                    "QPushButton:hover { background-color: #e0607f; }"
                                    "QPushButton:disabled { background-color: #cccccc; }")
        self.stop_btn.clicked.connect(self._do_stop_live)

        self.change_area_btn = QPushButton("更换分区")
        self.change_area_btn.clicked.connect(self._do_change_area)

        self.refresh_btn = QPushButton("刷新状态")
        self.refresh_btn.clicked.connect(self._refresh_status)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.change_area_btn)
        btn_layout.addWidget(self.refresh_btn)
        right_layout.addWidget(btn_group)

        # Log area
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Menlo", 11) if sys.platform == "darwin" else QFont("Consolas", 10))
        log_layout.addWidget(self.log_text)
        right_layout.addWidget(log_group)

        splitter.addWidget(right_widget)
        splitter.setSizes([280, 470])
        root_layout.addWidget(splitter)

        self._set_buttons_enabled(False)

    def _set_buttons_enabled(self, logged_in):
        self.start_btn.setEnabled(logged_in)
        self.stop_btn.setEnabled(logged_in)
        self.change_area_btn.setEnabled(logged_in)
        self.refresh_btn.setEnabled(logged_in)

    # ── Logging ──

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{ts}] {msg}")

    # ── Login ──

    def _try_auto_login(self):
        config = api.ConfigManager(0)
        cookies = config.check()
        if cookies:
            self._set_logged_in(cookies)
        else:
            self.log("未找到登录信息，请点击「登录」按钮")

    def _do_login(self):
        dlg = LoginDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.cookies:
            self._set_logged_in(dlg.cookies)
            self.log("登录成功！")
        else:
            self.log("登录取消")

    def _set_logged_in(self, cookies):
        self.uid = int(cookies["DedeUserID"])
        self.cookie_str = api.dict2cookieformat(cookies)
        self.uid_label.setText(f"UID: {self.uid}")
        self.login_btn.setText("重新登录")
        self._set_buttons_enabled(True)

        # Load saved title
        cm = api.ConfigManager(self.uid)
        last_title = cm.get_last_title()
        if last_title:
            self.title_input.setText(last_title)

        # Load areas and status
        self._load_areas()
        self._refresh_status()

    # ── Area tree ──

    def _load_areas(self):
        self.log("正在加载分区列表...")
        w = ApiWorker(api.get_area_list)
        w.finished.connect(self._on_areas_loaded)
        w.error.connect(lambda e: self.log(f"加载分区列表失败: {e}"))
        self._workers.append(w)
        w.start()

    def _on_areas_loaded(self, area_list):
        self.area_tree.clear()
        if not area_list:
            self.log("分区列表为空")
            return

        # Get last saved area for highlighting
        saved_area = None
        if self.uid:
            cm = api.ConfigManager(self.uid)
            saved_area = cm.get_last_area()

        target_item = None
        for parent_data in area_list:
            parent_item = QTreeWidgetItem([parent_data["name"], ""])
            parent_item.setFlags(parent_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            font = parent_item.font(0)
            font.setBold(True)
            parent_item.setFont(0, font)
            self.area_tree.addTopLevelItem(parent_item)

            for child_data in parent_data["list"]:
                child_item = QTreeWidgetItem([child_data["name"], str(child_data["id"])])
                child_item.setData(0, Qt.ItemDataRole.UserRole, int(child_data["id"]))
                child_item.setData(1, Qt.ItemDataRole.UserRole, f"{parent_data['name']} - {child_data['name']}")
                parent_item.addChild(child_item)

                # Highlight saved area
                if saved_area and int(child_data["id"]) == saved_area.get("id"):
                    target_item = child_item
                    self.selected_area_id = int(child_data["id"])
                    self.selected_area_name = f"{parent_data['name']} - {child_data['name']}"

        if target_item:
            target_item.parent().setExpanded(True)
            self.area_tree.setCurrentItem(target_item)

        self.log(f"分区列表加载完成（{sum(len(p['list']) for p in area_list)} 个分区）")

    def _on_area_selected(self, item, column):
        area_id = item.data(0, Qt.ItemDataRole.UserRole)
        if area_id is None:
            return  # clicked parent node
        self.selected_area_id = area_id
        self.selected_area_name = item.data(1, Qt.ItemDataRole.UserRole)
        self.log(f"已选择分区: {self.selected_area_name} (ID: {area_id})")

    # ── Status refresh ──

    def _refresh_status(self):
        if not self.uid:
            return
        w = ApiWorker(self._fetch_status)
        w.finished.connect(self._on_status_refreshed)
        w.error.connect(lambda e: self.log(f"刷新状态失败: {e}"))
        self._workers.append(w)
        w.start()

    def _fetch_status(self):
        room_info = api.get_room_info(self.uid)
        live_status = 0
        room_id = 0
        has_room = room_info.get("roomStatus", 0) == 1
        if has_room:
            room_id = room_info.get("roomid", 0)
            for key in ["live_status", "liveStatus", "LiveStatus"]:
                if key in room_info:
                    live_status = room_info[key]
                    break
            # Fallback: query room API directly
            if live_status == 0 and room_id:
                try:
                    device_fp = api.get_device_fp()
                    headers = device_fp.get_headers(with_cookie=self.cookie_str)
                    resp = api.get_http_session().get(
                        f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}",
                        headers=headers).json()
                    if resp.get("code") == 0 and "data" in resp:
                        live_status = resp["data"].get("live_status", 0)
                except Exception:
                    pass
        return {"has_room": has_room, "room_id": room_id, "live_status": live_status}

    def _on_status_refreshed(self, info):
        self.room_id = info["room_id"]
        self.is_live = info["live_status"] == 1

        if not info["has_room"]:
            self.room_label.setText("直播间: 未开通")
            self.status_indicator.setText("● 无直播间")
            self.status_indicator.setStyleSheet("color: gray; font-weight: bold;")
        else:
            self.room_label.setText(f"直播间: {info['room_id']}")
            if self.is_live:
                self.status_indicator.setText("● 直播中")
                self.status_indicator.setStyleSheet("color: #00c853; font-weight: bold;")
            else:
                self.status_indicator.setText("● 未开播")
                self.status_indicator.setStyleSheet("color: #fb7299; font-weight: bold;")

        self.log(f"状态已刷新 — 直播间: {info['room_id']}  {'直播中' if self.is_live else '未开播'}")

    # ── Start live ──

    def _do_start_live(self):
        if not self.cookie_str:
            return
        if not self.selected_area_id:
            QMessageBox.warning(self, "提示", "请先在左侧选择一个直播分区")
            return

        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "提示", "请输入直播标题")
            return

        # Save title and area
        if self.uid:
            cm = api.ConfigManager(self.uid)
            cm.save_title(title)
            cm.save_area(self.selected_area_id, self.selected_area_name)

        # If already live, stop first
        if self.is_live:
            ret = QMessageBox.question(self, "确认", "当前正在直播中，需要先停播再重新开播。\n是否继续？")
            if ret != QMessageBox.StandardButton.Yes:
                return
            self.log("正在停止当前直播...")
            self._set_buttons_enabled(False)
            w = ApiWorker(self._stop_then_start, title)
            w.finished.connect(self._on_start_result)
            w.error.connect(lambda e: (self.log(f"操作失败: {e}"), self._set_buttons_enabled(True)))
            self._workers.append(w)
            w.start()
        else:
            self.log(f"正在开播「{title}」...")
            self._set_buttons_enabled(False)
            w = ApiWorker(api.start_live, self.cookie_str, self.selected_area_id, title)
            w.finished.connect(self._on_start_result)
            w.error.connect(lambda e: (self.log(f"开播失败: {e}"), self._set_buttons_enabled(True)))
            self._workers.append(w)
            w.start()

    def _stop_then_start(self, title):
        stop_r = api.stop_live(self.cookie_str)
        if stop_r.get("code") != 0:
            return {"code": -1, "message": f"停播失败: {stop_r.get('message', '未知错误')}"}
        import time
        time.sleep(1)
        return api.start_live(self.cookie_str, self.selected_area_id, title)

    def _on_start_result(self, result):
        self._set_buttons_enabled(True)
        if result and result.get("code") == 0:
            self.log("开播成功！")
            if result.get("title_warning"):
                self.log(f"标题同步可能未生效: {result['title_warning']}")
            elif result.get("title_update"):
                self.log("直播标题已同步")
            self._refresh_status()
        else:
            self.log(f"开播失败: {result.get('message', '未知错误') if result else '无响应'}")

    # ── Stop live ──

    def _do_stop_live(self):
        if not self.cookie_str:
            return
        ret = QMessageBox.question(self, "确认", "确定要停止直播吗？")
        if ret != QMessageBox.StandardButton.Yes:
            return

        self.log("正在停止直播...")
        self._set_buttons_enabled(False)
        w = ApiWorker(api.stop_live, self.cookie_str)
        w.finished.connect(self._on_stop_result)
        w.error.connect(lambda e: (self.log(f"停播失败: {e}"), self._set_buttons_enabled(True)))
        self._workers.append(w)
        w.start()

    def _on_stop_result(self, result):
        self._set_buttons_enabled(True)
        if result and result.get("code") == 0:
            self.log("直播已停止")
            self._refresh_status()
        else:
            self.log(f"停播失败: {result.get('message', '未知错误') if result else '无响应'}")

    # ── Change area ──

    def _do_change_area(self):
        if not self.cookie_str:
            return
        if not self.selected_area_id:
            QMessageBox.warning(self, "提示", "请先在左侧选择一个直播分区")
            return

        self.log(f"正在更换分区为「{self.selected_area_name}」...")
        if self.uid:
            cm = api.ConfigManager(self.uid)
            cm.save_area(self.selected_area_id, self.selected_area_name)

        self._set_buttons_enabled(False)
        w = ApiWorker(api.update_live_area, self.cookie_str, self.selected_area_id)
        w.finished.connect(self._on_change_area_result)
        w.error.connect(lambda e: (self.log(f"更换分区失败: {e}"), self._set_buttons_enabled(True)))
        self._workers.append(w)
        w.start()

    def _on_change_area_result(self, result):
        self._set_buttons_enabled(True)
        if result and result.get("code") == 0:
            self.log("分区更换成功！")
        else:
            self.log(f"更换分区失败: {result.get('message', '未知错误') if result else '无响应'}")


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("B站直播工具")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
