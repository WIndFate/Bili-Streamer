import argparse
import base64
import io
import json
import os
import qrcode
import requests
import sys
import time
import random
import string
import hashlib
import uuid
import platform
import re
from pathlib import Path
from urllib.parse import urlencode, quote
from datetime import datetime, timedelta


APP_KEY = "1d8b6e7d45233436"
APP_SECRET = "560c52ccd288fed045859ed18bffd973"

# Global instances (lazy-initialized in main)
_device_fp = None
_http_session = None


def get_device_fp():
    """Get or create the global DeviceFingerprint singleton"""
    global _device_fp
    if _device_fp is None:
        _device_fp = DeviceFingerprint()
    return _device_fp


def get_http_session():
    """Get or create the global requests.Session with default timeout"""
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        _http_session.request = _wrap_timeout(_http_session.request)
    return _http_session


def _wrap_timeout(original_request):
    """Wrap session.request to enforce a default timeout of 30s"""
    def wrapper(*args, **kwargs):
        kwargs.setdefault("timeout", 30)
        return original_request(*args, **kwargs)
    return wrapper

def sign_params(params: dict) -> dict:
    """
    为 B站 APP 接口参数生成 sign 字段（签名）
    @param params: 要发送的请求参数字典
    @return: 添加 sign 的完整参数字典
    """
    # 添加 appkey
    params["appkey"] = APP_KEY

    # 对参数按 key 升序排序
    sorted_items = sorted(params.items())
    query_str = urlencode(sorted_items)

    # 拼接 app_secret
    sign_str = f"{query_str}{APP_SECRET}"

    # 计算 md5
    sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest()

    # 加入 sign 参数
    params["sign"] = sign
    return params

# 添加随机延迟函数
def random_delay(min_seconds=0.5, max_seconds=2.5):
    """添加随机延迟，模拟人类行为"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def is_success_response(response: dict) -> bool:
    return isinstance(response, dict) and response.get("code") == 0


def response_message(response: dict, default: str = "未知错误") -> str:
    if not isinstance(response, dict):
        return default
    return response.get("message") or response.get("msg") or default


# 生成随机设备标识
class DeviceFingerprint:
    """生成和管理持久化的设备指纹"""
    
    def __init__(self, dirname="bili_config"):
        self.config_dir = Path(dirname)
        self.fingerprint_path = self.config_dir / "device.json"
        if not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)
        self.fingerprint = self._load_or_create()
    
    def _generate_fingerprint(self):
        """生成一套一致的设备指纹"""
        # 生成持久化的设备ID
        device_id = str(uuid.uuid4())

        # Popular Android flagship models (2024-2025)
        android_models = [
            "Xiaomi 14 Ultra", "Xiaomi 15",
            "Samsung Galaxy S24", "Samsung Galaxy S24 Ultra", "Samsung Galaxy S25",
            "OnePlus 12", "OnePlus 13",
            "Google Pixel 9 Pro",
        ]
        device_model = random.choice(android_models)

        android_versions = ["14", "15"]
        android_version = random.choice(android_versions)

        # Matching screen resolutions for each model
        screen_resolutions = {
            "Xiaomi 14 Ultra": "1440x3200",
            "Xiaomi 15": "1440x3200",
            "Samsung Galaxy S24": "1080x2340",
            "Samsung Galaxy S24 Ultra": "1440x3120",
            "Samsung Galaxy S25": "1080x2340",
            "OnePlus 12": "1440x3168",
            "OnePlus 13": "1440x3168",
            "Google Pixel 9 Pro": "1280x2856",
        }
        screen_resolution = screen_resolutions[device_model]

        # Matching screen densities (dpi)
        screen_densities = {
            "Xiaomi 14 Ultra": "522",
            "Xiaomi 15": "522",
            "Samsung Galaxy S24": "425",
            "Samsung Galaxy S24 Ultra": "505",
            "Samsung Galaxy S25": "425",
            "OnePlus 12": "510",
            "OnePlus 13": "510",
            "Google Pixel 9 Pro": "486",
        }
        screen_density = screen_densities[device_model]

        # Recent BiliDroid versions
        app_versions = ["7.82.0", "7.81.0", "7.80.0"]
        app_version = random.choice(app_versions)
        
        # Generate BUVID in real format: XX + 32-char lowercase MD5 hex
        buvid = "XX" + hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()
        
        # 构建指纹字典
        return {
            # 基本标识符
            "device_id": device_id,
            "buvid": buvid,
            
            # 设备信息
            "model": device_model,
            "brand": device_model.split(" ")[0],  # 提取品牌名称(Xiaomi/OnePlus等)
            "manufacturer": device_model.split(" ")[0],
            
            # 系统信息
            "android_version": android_version,
            "build_id": f"T{random.choice('ABCDEFGHIJKLMN')}{random.randint(1,9)}{random.randint(0,9)}A.{random.randint(100,999)}{random.choice('ABCDEF')}",  # 如 TKQ1A.230829D
            
            # 显示信息
            "screen_resolution": screen_resolution,
            "screen_density": screen_density,
            "display": f"{screen_resolution}, {screen_density}dpi",
            
            # 应用信息
            "app_version": app_version,
            "build_number": app_version.replace(".", "") + "00",
            "channel": "bili",
            
            # 设备硬件信息
            "cpu_abi": "arm64-v8a",  # 现代设备都使用64位CPU
            "memory": f"{random.choice([6, 8, 12, 16])}GB",  # 内存大小
            
            # 地区和语言
            "timezone": "GMT+08:00",  # 中国时区
            "language": "zh-CN",
            "region": "CN",
            
            # Network info
            "network_type": random.choice(["WIFI", "5G", "4G"]),

            # Timestamps and fingerprints (generated once, persisted)
            "created_at": time.time(),
            "fp_local": hashlib.md5((device_id + buvid).encode()).hexdigest() + str(int(time.time()))[:8],
            "fp_remote": hashlib.md5((device_id + buvid + "bilibili").encode()).hexdigest() + str(int(time.time()))[:8],

            # Bilibili-specific fingerprint params (stable per device)
            "session_id": ''.join(random.choices(string.ascii_lowercase + string.digits, k=8)),
            "guest_id": ''.join(random.choices(string.digits, k=15)),
            "display_id": f"{random.randint(10000000, 99999999)}-{int(time.time())}",
        }
    
    def _load_or_create(self):
        """加载现有指纹或创建新指纹"""
        try:
            if os.path.exists(self.fingerprint_path):
                with open(self.fingerprint_path, 'r', encoding='utf-8') as f:
                    fingerprint = json.load(f)
                    # 检查指纹是否完整
                    required_keys = ["device_id", "buvid", "model", "android_version",
                                    "app_version", "build_number", "fp_local", "fp_remote"]
                    if all(key in fingerprint for key in required_keys):
                        # Backfill fields added in newer versions
                        updated = False
                        if "display_id" not in fingerprint:
                            fingerprint["display_id"] = f"{random.randint(10000000, 99999999)}-{int(time.time())}"
                            updated = True
                        if "session_id" not in fingerprint:
                            fingerprint["session_id"] = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                            updated = True
                        if updated:
                            self._save_fingerprint(fingerprint)
                        return fingerprint
        except Exception as e:
            print(f"读取设备指纹出错，将创建新指纹: {str(e)}")
        
        # 创建新指纹
        fingerprint = self._generate_fingerprint()
        self._save_fingerprint(fingerprint)
        return fingerprint
    
    def _save_fingerprint(self, fingerprint):
        """保存指纹到文件"""
        try:
            with open(self.fingerprint_path, 'w', encoding='utf-8') as f:
                json.dump(fingerprint, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存设备指纹出错: {str(e)}")
    
    def get_headers(self, with_cookie=None):
        """Generate request headers based on persisted device fingerprint"""
        # Map network_type to numeric code used in UA (stable per session)
        network_map = {"WIFI": 2, "4G": 1, "5G": 3}
        network_code = network_map.get(self.fingerprint.get("network_type", "WIFI"), 2)

        headers = {
            "User-Agent": f"Mozilla/5.0 BiliDroid/{self.fingerprint['app_version']} "
                        f"os/android model/{self.fingerprint['model']} mobi_app/android "
                        f"build/{self.fingerprint['build_number']} channel/{self.fingerprint.get('channel', 'bili')} "
                        f"innerVer/{self.fingerprint['build_number']} osVer/{self.fingerprint['android_version']} "
                        f"network/{network_code}",
            "Buvid": self.fingerprint["buvid"],
            "Device-ID": self.fingerprint["device_id"],
            "Display-ID": self.fingerprint.get("display_id", f"{random.randint(10000000, 99999999)}-{int(time.time())}"),
            "App-Key": "android64",
            "x-from-bilibili": "true",
            "env": "prod",
            "Accept-Encoding": "gzip",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "Connection": "Keep-Alive",
            "Screen-Density": f"{self.fingerprint.get('screen_density', '480')}dpi",
            "Device-Brand": self.fingerprint.get('brand', self.fingerprint['model'].split(" ")[0]),
            "Device-Model": self.fingerprint['model'],
            "os": "android",
            "os_ver": self.fingerprint['android_version'],
            "fp_local": self.fingerprint["fp_local"],
            "fp_remote": self.fingerprint["fp_remote"],
            "Session-ID": self.fingerprint["session_id"],
        }
        
        if with_cookie:
            headers["cookie"] = with_cookie
        
        return headers
    
    def get_common_params(self):
        """获取通用请求参数"""
        return {
            "platform": "android",
            "build": self.fingerprint["build_number"],
            "mobi_app": "android",
            "device": "android",
            "channel": "bili",
            "statistics": json.dumps({
                "appId": 1,
                "platform": 3,
                "version": self.fingerprint["app_version"],
                "abtest": ""
            })
        }

# 原有工具类函数
class ConfigManager:
    """配置文件的查找和更新"""

    def __init__(self, uid=0, dirname="bili_config"):
        # 字符串化UID
        self.uid = str(uid)
        # 配置文件路径
        self.config_dir = Path(dirname)
        self.config_path = self.config_dir / "config.json"
        if not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)

    def update(self, cookies: dict):
        """
        记录uid和cookie到配置文件中
        @param cookies: 登录获取的cookies
        """
        uid = self.uid
        # 判断配置文件是否存在，不存在则创建
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                f.read()
        except Exception:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
        
        # 更新配置
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                config[uid] = cookies
                output_config = config
        except Exception:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                input_config = f.read()
                output_config = {uid: cookies}
            # 备份违规文件
            backup_path = self.config_dir / f"{time.strftime('%Y%m%d%H%M%S')}_config.json"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(input_config)
        
        # 更新uid和cookie到配置文件中
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(output_config, f, ensure_ascii=False, indent=4)

    def check(self) -> dict:
        """
        查询配置文件中保存的uid对应的cookies
        @return: uid对应的cookies，uid不存在会返回{}
        """
        cookies = {}
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)[self.uid]
        except Exception:
            pass
        return cookies
        
    def save_area(self, area_id: int, area_name: str):
        """
        保存上次选择的分区
        @param area_id: 分区ID
        @param area_name: 分区名称
        """
        settings_path = self.config_dir / "settings.json"
        settings = {}
        
        # 读取现有设置
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except Exception:
            pass
            
        # 更新设置
        if 'last_area' not in settings:
            settings['last_area'] = {}
            
        settings['last_area']['id'] = area_id
        settings['last_area']['name'] = area_name
        
        # 保存设置
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
            
    def get_last_area(self) -> dict:
        """
        获取上次选择的分区
        @return: 分区信息，不存在返回None
        """
        settings_path = self.config_dir / "settings.json"
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                if 'last_area' in settings:
                    return settings['last_area']
        except Exception:
            pass
        return None

    def save_title(self, title: str):
        """
        Save the last used live stream title
        @param title: live stream title
        """
        settings_path = self.config_dir / "settings.json"
        settings = {}
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except Exception:
            pass
        settings['last_title'] = title
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)

    def get_last_title(self) -> str:
        """
        Get the last used live stream title
        @return: title string, or None if not found
        """
        settings_path = self.config_dir / "settings.json"
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return settings.get('last_title')
        except Exception:
            pass
        return None


def url_decoded(url_string: str) -> str:
    """
    将UTF-8解码成URL编码
    @param url_string: 要解码的UTF-8编码字符串
    @return: URL编码
    """
    utf8_encoded = quote(url_string, encoding='utf-8')
    return utf8_encoded


def dict2cookieformat(json_dict: dict) -> str:
    """
    将dict转换为cookie格式
    @param json_dict: 字典
    @return: cookie格式的字典
    """
    cookie = ''
    for key in json_dict:
        value = json_dict[key]
        cookie += url_decoded(str(key)) + '=' + url_decoded(str(value)) + '; '
    cookie = cookie.strip()
    if cookie.endswith(";"):
        cookie = cookie[:-1]
    return cookie


def cookie2dict(cookie: str) -> dict:
    """
    将cookie字典化
    @param cookie: cookie字符串
    @return: cookie字典
    """
    # 用分号分隔输入字符串
    key_value_pairs = cookie.split('; ')
    # 初始化空字典
    result_dict = {}
    # 遍历每个键值对
    for pair in key_value_pairs:
        if '=' in pair:
            # 将pair拆分为key和value
            key, value = pair.split('=', 1)
            # 删除任何前导或尾随空格
            key = key.strip()
            value = value.strip()
            # 将键值对添加到字典中
            result_dict[key] = value
    return result_dict


def print_qrcode(qr_str: str):
    """
    在终端打印二维码
    @param qr_str: 二维码文本
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_str)
    qr.make(fit=True)
    
    # 保存原始标准输出
    old_stdout = sys.stdout
    # 创建StringIO对象捕获输出
    output = io.StringIO()
    sys.stdout = output
    qr.print_ascii(invert=True)
    sys.stdout = old_stdout
    
    # 打印二维码
    print(output.getvalue())


# 登录相关函数
def generate_qrcode() -> dict:
    """
    申请登录二维码
    @return: {'url': 二维码文本, 'qrcode_key': 扫描秘钥}
    """
    # 创建设备指纹
    device_fp = get_device_fp()
    headers = device_fp.get_headers()
    
    api = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate'
    response = get_http_session().get(api, headers=headers).json()
    data = response['data']
    url = data['url']
    qrcode_key = data['qrcode_key']
    return {'url': url, 'qrcode_key': qrcode_key}


def check_login_status(qrcode_key: str) -> dict:
    """
    获取登录状态，登录成功获取cookies
    @param qrcode_key: 扫描秘钥
    @return: {'code': 状态码, 'cookies': cookies字典}
    状态码: 0-成功，86038-二维码已失效，86090-已扫码未确认，86101-未扫码
    """
    # 创建设备指纹
    device_fp = get_device_fp()
    headers = device_fp.get_headers()
    
    api = f'https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={qrcode_key}'
    
    # 添加随机延迟使请求模式更自然
    random_delay(0.8, 2.0)
    
    response = get_http_session().get(api, headers=headers).json()
    data = response['data']
    
    cookies = {}
    code = data['code']
    if code == 0:
        def url_to_dict(url: str):
            """将URL参数转换成dict"""
            url_data = url.split('?', 1)[1]
            data_list = url_data.split('&')
            data_dict = {}
            for item in data_list:
                item = item.split('=')
                data_dict[item[0]] = item[1]
            return data_dict

        data_dict = url_to_dict(data['url'])
        cookies["DedeUserID"] = data_dict['DedeUserID']
        cookies["DedeUserID__ckMd5"] = data_dict['DedeUserID__ckMd5']
        cookies["SESSDATA"] = data_dict['SESSDATA']
        cookies["bili_jct"] = data_dict['bili_jct']
        
        # 补充cookie
        # 使用我们自己的请求头，不用B站返回的额外cookie，减少特征
        response = get_http_session().get('https://www.bilibili.com/video/', headers=headers)
        # 只提取必要的cookie，减少指纹
        for key in ['sid', 'buvid3', 'buvid4']:
            if key in response.cookies:
                cookies[key] = response.cookies[key]
    
    return {'code': code, 'cookies': cookies}


# 直播功能相关函数
def get_room_info(uid: int) -> dict:
    """
    获取直播间基本信息
    @param uid: B站UID
    @return: 直播间信息
    """
    # 创建设备指纹
    device_fp = get_device_fp()
    headers = device_fp.get_headers()
    
    # 添加随机延迟
    random_delay(0.3, 1.0)
    
    api = "https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld"
    params = {
        "mid": uid,
        **device_fp.get_common_params(),
        "ts": int(time.time())
    }
    response = get_http_session().get(api, headers=headers, params=params).json()
    return response["data"]


def get_room_id(cookie: str) -> int:
    """
    获取直播间号
    @param cookie: 登录cookie
    @return: 直播间号
    """
    # 创建设备指纹
    device_fp = get_device_fp()
    headers = device_fp.get_headers(with_cookie=cookie)
    common_params = device_fp.get_common_params()
    
    # 添加随机延迟
    random_delay(0.5, 1.5)
    
    # 尝试使用直播姬特有的API获取房间ID
    api = "https://api.live.bilibili.com/xlive/app-blink/v1/highlight/getRoomHighlightState"
    params = {
        **common_params,
        "ts": int(time.time())
    }
    
    try:
        response = get_http_session().get(api, headers=headers, params=params).json()
        if response["code"] == 0 and "data" in response and "room_id" in response["data"]:
            return response["data"]["room_id"]
        else:
            print(f"尝试获取直播间ID: {response.get('message', '未知错误')}")
    except Exception as e:
        print(f"尝试获取直播间ID出错: {str(e)}")
    
    # 备用方法: 从通用API获取房间ID
    try:
        cookies = cookie2dict(cookie)
        uid = int(cookies["DedeUserID"])
        room_info = get_room_info(uid)
        if room_info and 'roomid' in room_info:
            return room_info['roomid']
    except Exception as e:
        print(f"备用方法获取直播间ID出错: {str(e)}")
        
    print("无法获取直播间ID，请确认您的账号已开通直播间")
    return 0


def start_live(cookie: str, area_id: int, title: str = "") -> dict:

    # 创建设备指纹（假设你的 DeviceFingerprint 仍然工作）
    device_fp = get_device_fp()
    headers = device_fp.get_headers(with_cookie=cookie)

    # 提取 csrf
    cookies = cookie2dict(cookie)
    csrf = cookies.get("bili_jct")

    # 获取 room_id
    room_id = get_room_id(cookie)
    if not room_id:
        return {"code": -1, "message": "无法获取直播间ID"}

    title = title.strip()
    pre_live_title_response = None
    if title:
        # 先同步预开播信息，避免 startLive 使用旧标题创建本场直播。
        pre_live_title_response = update_pre_live_title(cookie, title)
        if not is_success_response(pre_live_title_response):
            room_title_response = update_room_title(cookie, title)
            if not is_success_response(room_title_response):
                return {
                    "code": -1,
                    "message": (
                        "标题同步失败，已取消开播: "
                        f"{response_message(pre_live_title_response)}; "
                        f"{response_message(room_title_response)}"
                    ),
                    "title_update": {
                        "pre_live": pre_live_title_response,
                        "room_update": room_title_response,
                    },
                }

    # 构建请求参数
    params = {
        "area_v2": area_id,
        "room_id": room_id,
        "csrf": csrf,
        "csrf_token": csrf,
        "build": device_fp.fingerprint["build_number"],
        "platform": "android_link",
        "mobi_app": "android",
        "ts": int(time.time())
    }

    # 添加签名
    signed_params = sign_params(params)

    # 发送 POST 请求
    api = "https://api.live.bilibili.com/room/v1/Room/startLive"
    try:
        response = get_http_session().post(api, headers=headers, data=signed_params).json()

        if title:
            response["title_update"] = {"pre_live": pre_live_title_response}

        # 开播成功后再补一次直播间标题更新，并把结果返回给调用方。
        if title and is_success_response(response):
            random_delay(0.8, 1.5)
            room_title_response = update_room_title(cookie, title)
            response["title_update"]["room_update"] = room_title_response
            if not is_success_response(room_title_response):
                response["title_warning"] = response_message(room_title_response)

        return response
    except Exception as e:
        return {"code": -1, "message": f"开播失败: {str(e)}"}


def stop_live(cookie: str) -> dict:
    """
    结束直播（模拟 Android 直播姬）
    @param cookie: 登录cookie
    @return: 结果
    """

    device_fp = get_device_fp()
    headers = device_fp.get_headers(with_cookie=cookie)

    cookies = cookie2dict(cookie)
    csrf = cookies.get("bili_jct")

    room_id = get_room_id(cookie)
    if not room_id:
        return {"code": -1, "message": "无法获取直播间ID"}

    random_delay(0.8, 2.0)

    api = "https://api.live.bilibili.com/room/v1/Room/stopLive"
    params = {
        "room_id": room_id,
        "csrf": csrf,
        "csrf_token": csrf,
        "build": device_fp.fingerprint["build_number"],
        "platform": "android_link",
        "mobi_app": "android",
        "ts": int(time.time())
    }

    signed_params = sign_params(params)

    try:
        response = get_http_session().post(api, headers=headers, data=signed_params).json()
        return response
    except Exception as e:
        print(f"停播请求出错: {str(e)}")
        return {"code": -1, "message": str(e)}


def update_room_title(cookie: str, title: str) -> dict:
    """
    更新直播间标题
    @param cookie: 登录cookie
    @param title: 新标题
    @return: 结果
    """

    device_fp = get_device_fp()
    headers = device_fp.get_headers(with_cookie=cookie)

    cookies = cookie2dict(cookie)
    csrf = cookies.get("bili_jct")
    if not csrf:
        return {"code": -1, "message": "缺少 bili_jct，无法更新直播标题"}

    room_id = get_room_id(cookie)
    if not room_id:
        return {"code": -1, "message": "无法获取直播间ID"}

    random_delay(0.5, 1.5)

    api = "https://api.live.bilibili.com/room/v1/Room/update"
    params = {
        "room_id": room_id,
        "title": title,
        "csrf": csrf,
        "csrf_token": csrf,
        "platform": "web",
        "visit_id": "",
    }

    try:
        response = get_http_session().post(api, headers=headers, data=params).json()
        return response
    except Exception as e:
        print(f"更新标题请求出错: {str(e)}")
        return {"code": -1, "message": str(e)}


def update_pre_live_title(cookie: str, title: str) -> dict:
    """
    更新预开播标题，让 startLive 使用最新标题创建直播场次
    @param cookie: 登录cookie
    @param title: 新标题
    @return: 结果
    """

    device_fp = get_device_fp()
    headers = device_fp.get_headers(with_cookie=cookie)

    cookies = cookie2dict(cookie)
    csrf = cookies.get("bili_jct")
    if not csrf:
        return {"code": -1, "message": "缺少 bili_jct，无法同步预开播标题"}

    random_delay(0.5, 1.5)

    api = "https://api.live.bilibili.com/xlive/app-blink/v1/preLive/UpdatePreLiveInfo"
    params = {
        "title": title,
        "csrf": csrf,
        "csrf_token": csrf,
        "platform": "web",
        "mobi_app": "web",
        "build": "1",
        "visit_id": "",
    }

    try:
        response = get_http_session().post(api, headers=headers, data=params).json()
        return response
    except Exception as e:
        print(f"同步预开播标题出错: {str(e)}")
        return {"code": -1, "message": str(e)}


def get_area_list() -> list:
    """
    获取直播分区列表
    @return: 分区列表
    """
    # 创建设备指纹
    device_fp = get_device_fp()
    headers = device_fp.get_headers()
    common_params = device_fp.get_common_params()
    
    # 添加随机延迟
    random_delay(0.3, 1.0)
    
    api = "https://api.live.bilibili.com/room/v1/Area/getList"
    params = {
        **common_params,
        "ts": int(time.time())
    }
    
    try:
        response = get_http_session().get(api, headers=headers, params=params).json()
        if response["code"] == 0:
            return response["data"]
        else:
            print(f"获取分区列表失败: {response.get('message', '未知错误')}")
            return []
    except Exception as e:
        print(f"获取分区列表出错: {str(e)}")
        return []


def login() -> dict:
    """
    登录流程
    @return: 登录结果，包含uid、cookies和cookie字符串
    """
    print("正在生成二维码...")
    qr_info = generate_qrcode()
    url = qr_info['url']
    qrcode_key = qr_info['qrcode_key']
    
    # 显示二维码
    print("\n请使用B站APP扫描以下二维码登录：")
    print_qrcode(url)
    
    # 轮询登录状态
    status_msgs = {
        0: "登录成功",
        86101: "未扫码",
        86090: "二维码已扫码未确认",
        86038: "二维码已失效"
    }
    
    print("\n等待扫码中...")
    last_status = None
    while True:
        result = check_login_status(qrcode_key)
        code = result['code']
        
        # 只在状态改变时打印消息
        if code != last_status:
            last_status = code
            if code in status_msgs:
                print(f"状态: {status_msgs[code]}")
        
        if code == 0:
            cookies = result['cookies']
            uid = int(cookies['DedeUserID'])
            cookie_str = dict2cookieformat(cookies)
            
            # 保存配置
            config = ConfigManager(uid)
            config.update(cookies)
            config = ConfigManager(0)  # 默认配置
            config.update(cookies)
            
            print(f"\n登录成功！UID: {uid}")
            return {'uid': uid, 'cookies': cookies, 'cookie': cookie_str}
        
        elif code == 86038:  # 二维码已失效
            print("\n二维码已失效，请重新运行程序")
            sys.exit(1)
        
        # 添加随机延迟，使轮询更自然
        random_delay(1.5, 3.0)


def print_area_list(area_list):
    """打印分区列表"""
    if not area_list:
        print("获取分区列表失败")
        return
        
    print("\n======= 直播分区列表 =======")
    for i, parent in enumerate(area_list):
        print(f"{i+1}. {parent['name']}")
        for j, child in enumerate(parent['list']):
            print(f"  {j+1} {child['name']} ")
    print("==========================\n")


def select_area(config_manager=None):
   """
   交互式选择直播分区
   @param config_manager: 配置管理器，用于获取上次分区
   @return: [area_id, area_name]
   """
   area_list = get_area_list()
   if not area_list:
       print("无法获取分区列表，使用默认分区")
       return [192, "聊天电台"]
   
   # 显示上次的选择
   last_area = None
   if config_manager:
       last_area = config_manager.get_last_area()
       if last_area:
           print(f"\n上次选择的分区: {last_area['name']} (ID: {last_area['id']})")
           use_last = input("是否使用上次的分区？(y/n，默认y): ").strip().lower()
           if use_last == "" or use_last == "y":
               return [last_area['id'], last_area['name']]
   
   print_area_list(area_list)
   
   try:
       parent_idx = int(input("请选择一级分区（输入序号）: ")) - 1
       if parent_idx < 0 or parent_idx >= len(area_list):
           print("输入序号无效，使用默认分区")
           return [192, "聊天电台"]
           
       child_idx = int(input(f"请选择{area_list[parent_idx]['name']}下的二级分区（输入序号）: ")) - 1
       if child_idx < 0 or child_idx >= len(area_list[parent_idx]['list']):
           print("输入序号无效，使用默认分区")
           return [192, "聊天电台"]
           
       area_id = int(area_list[parent_idx]['list'][child_idx]['id'])
       area_name = f"{area_list[parent_idx]['name']} - {area_list[parent_idx]['list'][child_idx]['name']}"
       print(f"已选择: {area_name}")
       return [area_id, area_name]
   except ValueError:
       print("输入无效，使用默认分区")
       return [192, "聊天电台"]
   except Exception as e:
       print(f"选择分区出错: {str(e)}，使用默认分区")
       return [192, "聊天电台"]


def update_live_area(cookie: str, area_id: int) -> dict:
    """
    尝试在不停止直播的情况下更新直播分区
    @param cookie: 登录cookie
    @param area_id: 二级分区id
    @return: 结果
    """
    # 创建设备指纹
    device_fp = get_device_fp()
    headers = device_fp.get_headers(with_cookie=cookie)
    
    cookies = cookie2dict(cookie)
    csrf = cookies.get("bili_jct")
    if not csrf:
        return {"code": -1, "message": "缺少 bili_jct，无法更新直播分区"}
    
    room_id = get_room_id(cookie)
    if not room_id:
        return {"code": -1, "message": "无法获取直播间ID"}
    
    # API地址 - 尝试更新直播分区
    api = "https://api.live.bilibili.com/room/v1/Room/update"
    
    params = {
        "room_id": room_id,
        "area_id": area_id,
        "csrf": csrf,
        "csrf_token": csrf,
        "platform": "web",
        "visit_id": "",
    }
    
    try:
        response = get_http_session().post(api, headers=headers, data=params).json()
        return response
    except Exception as e:
        print(f"更新分区请求出错: {str(e)}")
        return {"code": -1, "message": str(e)}


def get_stream_key(cookie_str, force_restart=False, custom_title=""):
    """
    主逻辑：获取流密钥，必要时开播
    """
    uid = int(cookie2dict(cookie_str)["DedeUserID"])
    config_manager = ConfigManager(uid)
    
    # 获取用户信息
    room_info = get_room_info(uid)
    
    print(f"\n用户UID: {uid}")
    print(f"直播间状态: {'有直播间' if room_info['roomStatus'] == 1 else '无直播间'}")
    
    if room_info['roomStatus'] == 1:
        room_id = room_info['roomid']
        # 修复：API可能返回 'liveStatus' 而非 'live_status'
        # 尝试从不同可能的键名获取直播状态
        live_status = None
        for possible_key in ['live_status', 'liveStatus', 'LiveStatus']:
            if possible_key in room_info:
                live_status = room_info[possible_key]
                break
        
        # 如果仍未找到直播状态，尝试通过其他API获取
        if live_status is None:
            # 尝试通过额外的API调用获取直播状态
            try:
                # 创建设备指纹
                device_fp = get_device_fp()
                headers = device_fp.get_headers(with_cookie=cookie_str)
                
                live_status_api = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}"
                status_response = get_http_session().get(live_status_api, headers=headers).json()
                if status_response['code'] == 0 and 'data' in status_response:
                    live_status = status_response['data'].get('live_status', 0)
                else:
                    # 如果API调用失败，默认为未开播
                    live_status = 0
            except Exception as e:
                print(f"获取直播状态出错: {str(e)}")
                live_status = 0
        
        print(f"直播间ID: {room_id}")
        print(f"直播状态: {'直播中' if live_status == 1 else '未开播'}")
        
        # 是否已经在直播
        is_live = (live_status == 1)
        
        # 如果直播中且用户不想重新开播，询问是否结束当前直播
        if is_live and not force_restart:
            stop_current = input("\n您当前正在直播中，是否结束当前直播？(y/n，默认n): ").strip().lower()
            if stop_current == "y":
                print("正在结束当前直播...")
                stop_result = stop_live(cookie_str)
                if stop_result['code'] == 0:
                    print("已结束当前直播")
                    is_live = False
                    force_restart = True
                else:
                    print(f"结束直播失败: {stop_result.get('message', '未知错误')}")
                    return
        
        # 总是选择分区，不管是否已经在直播
        area_result = select_area(config_manager)
        area_id = area_result[0]
        area_name = area_result[1]
        
        # 保存分区选择
        config_manager.save_area(area_id, area_name)
        
        # 如果已经在直播，询问是否要更换分区
        if is_live and not force_restart:
            change_area = input(f"\n是否要更换当前直播分区为 {area_name}？(y/n，默认n): ").strip().lower()
            if change_area == "y":
                print(f"正在尝试直接更新直播分区为「{area_name}」...")
                update_result = update_live_area(cookie_str, area_id)
                
                if update_result['code'] == 0:
                    print("直播分区更新成功，无需重启直播！")
                else:
                    print(f"直接更新分区失败: {update_result.get('message', '未知错误')}")
                    retry = input("是否通过停播重启的方式更换分区？(y/n，默认n): ").strip().lower()
                    if retry == "y":
                        # 先停播再开播来更换分区
                        print("正在结束当前直播以更换分区...")
                        stop_result = stop_live(cookie_str)
                        if stop_result['code'] == 0:
                            print("已结束当前直播")
                            is_live = False
                            force_restart = True
                        else:
                            print(f"结束直播失败: {stop_result.get('message', '未知错误')}")
                            return
        
        # 获取输入标题
        title = custom_title
        if not title:
            last_title = config_manager.get_last_title()
            default_title = last_title or "直播中"
            title_input = input(f"请输入直播标题（直接回车使用上次标题: {default_title}）: ")
            title = title_input.strip() or default_title

        # Save title for next time
        config_manager.save_title(title)

        # 如果已经在直播且不重新开播，询问是否要更新标题
        if is_live and not force_restart:
            update_title = input(f"\n是否要更新当前直播标题为 {title}？(y/n，默认n): ").strip().lower()
            if update_title == "y":
                print(f"正在更新直播标题为「{title}」...")
                update_result = update_room_title(cookie_str, title)
                if update_result['code'] == 0:
                    print("直播标题更新成功")
                else:
                    print(f"更新标题失败: {update_result.get('message', '未知错误')}")
        
        # 如果需要开播或重新开播
        if force_restart or not is_live:
            if is_live:
                print("正在结束当前直播...")
                stop_result = stop_live(cookie_str)
                if stop_result['code'] != 0:
                    print(f"结束直播失败: {stop_result.get('message', '未知错误')}")
                    return
                print("已结束当前直播")
                
            print(f"正在使用标题「{title}」开始直播...")
            start_result = start_live(cookie_str, area_id, title)
            
            if start_result['code'] == 0:
                print("开播成功！")
                if start_result.get("title_warning"):
                    print(f"标题同步可能未生效: {start_result['title_warning']}")
                elif start_result.get("title_update"):
                    print("直播标题已同步")
                
            else:
                print(f"开播失败: {start_result.get('message', '未知错误')}")
                return
    else:
        print("您没有直播间，请使用其他账号尝试")
        return


def change_area_only(cookie_str):
    """
    只修改分区的功能，适用于已经在直播中
    @param cookie_str: 登录cookie
    """
    uid = int(cookie2dict(cookie_str)["DedeUserID"])
    config_manager = ConfigManager(uid)
    
    # 获取用户信息
    room_info = get_room_info(uid)
    
    if room_info['roomStatus'] != 1:
        print("您没有直播间，无法修改分区")
        return
    
    # 获取直播状态
    room_id = room_info['roomid']
    live_status = None
    for possible_key in ['live_status', 'liveStatus', 'LiveStatus']:
        if possible_key in room_info:
            live_status = room_info[possible_key]
            break
    
    # 如果仍未找到直播状态，尝试通过其他API获取
    if live_status is None:
        try:
            device_fp = get_device_fp()
            headers = device_fp.get_headers(with_cookie=cookie_str)
            
            live_status_api = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}"
            status_response = get_http_session().get(live_status_api, headers=headers).json()
            if status_response['code'] == 0 and 'data' in status_response:
                live_status = status_response['data'].get('live_status', 0)
            else:
                live_status = 0
        except Exception as e:
            print(f"获取直播状态出错: {str(e)}")
            live_status = 0
    
    print(f"\n用户UID: {uid}")
    print(f"直播间ID: {room_id}")
    print(f"直播状态: {'直播中' if live_status == 1 else '未开播'}")
    
    if live_status != 1:
        print("您当前未在直播中，请先开播")
        return
    
    # 选择新分区
    print("请选择要更改的新分区：")
    area_result = select_area(config_manager)
    area_id = area_result[0]
    area_name = area_result[1]
    
    # 保存分区选择
    config_manager.save_area(area_id, area_name)
    
    # 执行分区修改
    print(f"正在尝试直接更新直播分区为「{area_name}」...")
    update_result = update_live_area(cookie_str, area_id)
    
    if update_result['code'] == 0:
        print("直播分区更新成功！")
    else:
        print(f"直播分区更新失败: {update_result.get('message', '未知错误')}")
        print("提示: 部分分区可能需要停止直播后再更换")


def quit_live_only(cookie_str):
    """
    只关闭直播的功能
    @param cookie_str: 登录cookie
    """
    uid = int(cookie2dict(cookie_str)["DedeUserID"])
    
    # 获取用户信息
    room_info = get_room_info(uid)
    
    if room_info['roomStatus'] != 1:
        print("您没有直播间")
        return
    
    # 获取直播状态
    room_id = room_info['roomid']
    live_status = None
    for possible_key in ['live_status', 'liveStatus', 'LiveStatus']:
        if possible_key in room_info:
            live_status = room_info[possible_key]
            break
    
    print(f"\n用户UID: {uid}")
    print(f"直播间ID: {room_id}")
    print(f"直播状态: {'直播中' if live_status == 1 else '未开播'}")
    
    if live_status != 1:
        print("您当前未在直播中，无需关闭")
        return
    
    # 确认是否要关闭直播
    confirm = input("确认要关闭当前直播吗？(y/n，默认n): ").strip().lower()
    if confirm != "y":
        print("取消关闭直播")
        return
    
    # 执行关闭直播
    print("正在关闭直播...")
    stop_result = stop_live(cookie_str)
    
    if stop_result['code'] == 0:
        print("直播已成功关闭！")
    else:
        print(f"关闭直播失败: {stop_result.get('message', '未知错误')}")

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='B站直播推流码获取工具 - 模拟直播姬版')
    parser.add_argument('-r', '--restart', action='store_true', help='强制重新开播获取推流码')
    parser.add_argument('-t', '--title', type=str, default='', help='指定直播标题')
    parser.add_argument('-l', '--list-areas', action='store_true', help='仅列出分区列表并退出')
    parser.add_argument('-c', '--change-area', action='store_true', help='仅修改直播分区(适用于正在直播)')
    parser.add_argument('-q', '--quit-live', action='store_true', help='关闭当前直播')
    args = parser.parse_args()
    
    print("B站直播推流码获取工具 - 增强版")
    print("==========================")
    
    # 如果仅需列出分区
    if args.list_areas:
        area_list = get_area_list()
        print_area_list(area_list)
        return
    
    # 检查是否已有配置
    config = ConfigManager(0)
    cookies = config.check()
    
    if not cookies:
        print("未找到已保存的登录信息，请登录...")
        login_info = login()
        cookies = login_info['cookies']
    
    # 将cookies转为字符串格式
    cookie_str = dict2cookieformat(cookies)
    
    # 如果只需要修改分区
    if args.change_area:
        change_area_only(cookie_str)
        return
    
    # 如果只需要关闭直播
    if args.quit_live:
        quit_live_only(cookie_str)
        return
    
    # 获取推流码，必要时开播
    get_stream_key(cookie_str, args.restart, args.title)
    
    print("\n操作完成！")
    input("按回车键退出...")

if __name__ == "__main__":
   try:
       main()
   except KeyboardInterrupt:
       print("\n程序被用户中断")
   except Exception as e:
       print(f"\n程序出错: {str(e)}")
       import traceback
       traceback.print_exc()
       input("按回车键退出...")
