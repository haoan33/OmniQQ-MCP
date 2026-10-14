"""
NapCat MCP Server 全局配置、多账号管理、扫码登录与进程控制模块
"""
import os
import time
import json
import glob
import socket
import logging
import subprocess
import queue
import threading
import tempfile
from pathlib import Path
from typing import Any, Optional
from .token_store import ensure_onebot_token

logger = logging.getLogger("NapCatMCP.Config")

# 路径常量定义
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)
USER_DATA_DIR = os.path.join(os.environ.get('LOCALAPPDATA') or os.path.join(Path.home(), '.local', 'share'), 'OmniQQ-MCP')
_legacy_runtime = os.path.join(PROJECT_ROOT, "napcat_runtime")
RUNTIME_DIR = os.environ.get('OMNIQQ_RUNTIME_DIR') or (_legacy_runtime if os.path.isdir(_legacy_runtime) else os.path.join(USER_DATA_DIR, 'napcat_runtime'))
SHELL_NODE_DIR = os.path.join(RUNTIME_DIR, "shell_node")
NODE_EXE = os.path.join(SHELL_NODE_DIR, "node.exe")
INDEX_JS = os.path.join(SHELL_NODE_DIR, "index.js")
NAPCAT_CONFIG_DIR = os.path.join(SHELL_NODE_DIR, "napcat", "config")
QR_CACHE_IMAGE = os.path.join(SHELL_NODE_DIR, "napcat", "cache", "qrcode.png")
_legacy_account = os.path.join(PROJECT_ROOT, 'current_account.txt')
CURRENT_ACCOUNT_FILE = os.environ.get('OMNIQQ_CURRENT_ACCOUNT_FILE') or os.path.join(USER_DATA_DIR, 'current_account.txt')
LOCAL_RELEASE_ZIP = os.path.join(RUNTIME_DIR, "NapCat.Shell.Windows.Node.zip")


def atomic_json(path, data, private=False):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data,stream,ensure_ascii=False,indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        if private:
            from .token_store import restrict_credential_acl
            restrict_credential_acl(Path(temporary))
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def is_within(path, root):
    if not path:
        return False
    try:
        return os.path.commonpath([os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(root))]) == os.path.normcase(os.path.abspath(root))
    except ValueError:
        return False

# 默认通信端点 (支持通过环境变量覆盖)
DEFAULT_HTTP_PORT = int(os.environ.get("NAPCAT_HTTP_PORT", "3000"))
DEFAULT_WS_PORT = int(os.environ.get("NAPCAT_WS_PORT", "3001"))
DEFAULT_HTTP_URL = os.environ.get("NAPCAT_HTTP_URL", f"http://127.0.0.1:{DEFAULT_HTTP_PORT}")
DEFAULT_WS_URL = os.environ.get("NAPCAT_WS_URL", f"ws://127.0.0.1:{DEFAULT_WS_PORT}")


def is_port_listening(port: int, host: str = "127.0.0.1", timeout: float = 0.8) -> bool:
    """检测本地指定端口是否处于监听状态"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, OSError, TimeoutError):
        return False


def get_current_account() -> str:
    """读取当前默认激活的 QQ 账号 UIN"""
    account_file = CURRENT_ACCOUNT_FILE if os.path.exists(CURRENT_ACCOUNT_FILE) else _legacy_account
    if os.path.exists(account_file):
        try:
            with open(account_file, "r", encoding="utf-8") as f:
                uin = f.read().strip()
                if uin:
                    return uin
        except Exception as e:
            logger.warning(f"读取 current_account.txt 失败: {e}")

    accounts = get_available_accounts()
    return accounts[0] if accounts else ""


def get_available_accounts() -> list[str]:
    """获取沙箱中已配置或保存过登录凭证的所有 QQ 账号列表"""
    accounts = set()
    if os.path.exists(NAPCAT_CONFIG_DIR):
        for pattern in ("onebot11_*.json", "napcat_*.json"):
            for fp in glob.glob(os.path.join(NAPCAT_CONFIG_DIR, pattern)):
                basename = os.path.basename(fp)
                uin = basename.replace("onebot11_", "").replace("napcat_", "").replace(".json", "")
                if uin.isdigit():
                    accounts.add(uin)

    account_file = CURRENT_ACCOUNT_FILE if os.path.exists(CURRENT_ACCOUNT_FILE) else _legacy_account
    if os.path.exists(account_file):
        try:
            with open(account_file, "r", encoding="utf-8") as f:
                cur = f.read().strip()
                if cur.isdigit():
                    accounts.add(cur)
        except Exception:
            pass

    return sorted(accounts)


def ensure_onebot_config(
    uin: str,
    http_port: int = DEFAULT_HTTP_PORT,
    ws_port: int = DEFAULT_WS_PORT,
    token: Optional[str] = None
) -> bool:
    """确保指定 UIN 的 OneBot 11 配置文件已开启 HTTP 与 WebSocket 端口"""
    if not str(uin).isdigit():
        return False
    if token is None:
        token = ensure_onebot_token()
    if not token:
        raise ValueError('OneBot Token 不能为空')
    cfg_path = os.path.join(NAPCAT_CONFIG_DIR, f"onebot11_{uin}.json")
    default_cfg = {
        "network": {
            "httpServers": [
                {
                    "name": "httpServer",
                    "enable": True,
                    "host": "127.0.0.1",
                    "port": int(http_port),
                    "token": token,
                    "enableCors": True,
                    "enableWebsocket": False
                }
            ],
            "httpSseServers": [],
            "httpClients": [],
            "websocketServers": [
                {
                    "name": "websocketServer",
                    "enable": True,
                    "host": "127.0.0.1",
                    "port": int(ws_port),
                    "reportSelfMessage": True,
                    "messagePostFormat": "array",
                    "token": token,
                    "debug": False,
                    "heartInterval": 30000
                }
            ],
            "websocketClients": [],
            "plugins": []
        },
        "musicSignUrl": "",
        "enableLocalFile2Url": False,
        "parseMultMsg": False,
        "imageDownloadProxy": "",
        "timeout": {
            "baseTimeout": 10000,
            "uploadSpeedKBps": 256,
            "downloadSpeedKBps": 256,
            "maxTimeout": 1800000
        }
    }
    try:
        os.makedirs(NAPCAT_CONFIG_DIR, exist_ok=True)
        if os.path.exists(cfg_path):
            with open(cfg_path,encoding='utf-8') as stream:
                existing = json.load(stream)
            # Preserve unrelated plugins and clients. Secure the two managed local servers.
            network = existing.setdefault('network',{})
            for key in ('httpServers','websocketServers'):
                defaults = default_cfg['network'][key][0]
                servers = network.setdefault(key,[])
                current = next((item for item in servers if item.get('name') == defaults['name']),None)
                if current is None:
                    servers.append(defaults)
                else:
                    current.update(defaults)
                    current.pop('secret', None)  # Legacy key is ignored by current NapCat.
            default_cfg = existing
        atomic_json(cfg_path,default_cfg,private=True)
        return True
    except Exception as e:
        logger.error(f"写入 OneBot11 配置失败: {e}")
        return False


def set_current_account(uin: str) -> bool:
    """设置当前默认登录 QQ 账号，并同步更新 webui.json 与 onebot11_<uin>.json"""
    uin = str(uin).strip()
    if not uin.isdigit():
        return False
    try:
        if not ensure_onebot_config(uin):
            return False
        webui_path = os.path.join(NAPCAT_CONFIG_DIR, "webui.json")
        if os.path.exists(webui_path):
            with open(webui_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["autoLoginAccount"] = uin
            atomic_json(webui_path,data)

        account_path = os.path.abspath(CURRENT_ACCOUNT_FILE)
        os.makedirs(os.path.dirname(account_path), exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=os.path.dirname(account_path))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(uin + "\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, account_path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)
        return True
    except Exception as e:
        logger.error(f"设置当前账号失败: {e}")
        return False


def clear_auto_login_account() -> bool:
    """清除 webui.json 中的 autoLoginAccount，使下次启动时强制生成新登录二维码"""
    webui_path = os.path.join(NAPCAT_CONFIG_DIR, "webui.json")
    if not os.path.exists(webui_path):
        return True
    try:
        with open(webui_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["autoLoginAccount"] = ""
        atomic_json(webui_path,data)
        return True
    except Exception as e:
        logger.warning(f"清除 autoLoginAccount 失败: {e}")
        return False


def kill_napcat_processes() -> int:
    """
    精准停止后台运行中的 NapCat 沙箱进程 (仅终止路径位于 shell_node 下的 node.exe，绝不误杀系统其他 node 进程)
    返回终止的进程数量。
    """
    killed_count = 0
    try:
        import psutil
        target_exe = os.path.normcase(os.path.abspath(NODE_EXE))
        target_script = os.path.normcase(os.path.abspath(INDEX_JS))
        for proc in psutil.process_iter(["pid", "name", "exe", "cwd", "cmdline"]):
            try:
                exe_path = os.path.normcase(os.path.abspath(proc.info.get("exe") or ""))
                cmdline = proc.info.get("cmdline") or []
                process_cwd = proc.info.get('cwd') or ''
                scripts = [os.path.normcase(os.path.abspath(os.path.join(process_cwd, arg)))
                           for arg in cmdline[1:] if arg and not arg.startswith('-')]
                if exe_path == target_exe and target_script in scripts:
                    proc.kill()
                    killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        raise RuntimeError('缺少 psutil，无法安全确认进程所属路径')

    time.sleep(1.0)
    return killed_count


kill_existing_napcat = kill_napcat_processes


def start_qrcode_login_session(
    open_image: bool = True,
    wait_scan_seconds: int = 45
) -> dict[str, Any]:
    """
    启动扫码登录新 QQ 账号流程：
    1. 停止现有 NapCat 进程；
    2. 清空 autoLoginAccount 与旧二维码缓存；
    3. 启动沙箱获取新二维码并自动打开图片供用户手机扫码；
    4. 在 wait_scan_seconds 内监听扫码完成事件：
       - 若用户已完成扫码：自动为新账号配置 3000/3001 端口，切换为后台常驻服务并返回新账号；
       - 若等待超时用户尚未扫完：保留二维码图片路径提示用户继续扫码，随后调用 finalize_qrcode_login 完成绑定。
    """
    if not (os.path.exists(NODE_EXE) and os.path.exists(INDEX_JS)):
        return {
            "status": "not_installed",
            "error": f"未检测到 NapCat 运行时 ({NODE_EXE})，请先部署环境。"
        }

    before_accounts = set(get_available_accounts())
    kill_napcat_processes()
    clear_auto_login_account()

    # 清理旧二维码文件以便准确检测新生成的二维码
    if os.path.exists(QR_CACHE_IMAGE):
        try:
            os.remove(QR_CACHE_IMAGE)
        except Exception:
            pass

    proc = subprocess.Popen(
        [NODE_EXE, INDEX_JS],
        cwd=SHELL_NODE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    qr_opened = False
    logged_in_uin: Optional[str] = None
    start_ts = time.time()
    output_lines = queue.Queue(maxsize=1000)
    def drain_output():
        for line in iter(proc.stdout.readline, ''):
            try:
                output_lines.put_nowait(line)
            except queue.Full:
                pass
    reader = threading.Thread(target=drain_output,daemon=True)
    reader.start()
    login_confirmed = False

    try:
        while time.time() - start_ts < max(10, int(wait_scan_seconds)):
            if proc.poll() is not None:
                break

            # 检测二维码文件生成
            if not qr_opened and os.path.exists(QR_CACHE_IMAGE) and os.path.getsize(QR_CACHE_IMAGE) > 100:
                qr_opened = True
                if open_image and os.name == "nt":
                    try:
                        os.startfile(QR_CACHE_IMAGE)
                    except Exception:
                        pass

            try:
                line = output_lines.get(timeout=0.2)
            except queue.Empty:
                line = ''
            if line:
                if "二维码已保存到" in line and not qr_opened:
                    if os.path.exists(QR_CACHE_IMAGE):
                        qr_opened = True
                        if open_image and os.name == "nt":
                            try:
                                os.startfile(QR_CACHE_IMAGE)
                            except Exception:
                                pass

                if "快速登录" in line or "登录成功" in line:
                    login_confirmed = login_confirmed or '登录成功' in line
                    for token in line.replace("[", " ").replace("]", " ").split():
                        if token.isdigit() and 5 <= len(token) <= 12:
                            logged_in_uin = token

                if (
                    "Worker进程已登录成功" in line
                    or "已通知主进程登录成功" in line
                    or "OneBot11 适配器初始化完成" in line
                    or "HTTP服务" in line
                ):
                    time.sleep(1.5)
                    break
            else:
                time.sleep(0.2)

        # 检查是否有新生成的账号配置
        after_accounts = set(get_available_accounts())
        new_diff = sorted(list(after_accounts - before_accounts))
        target_uin = logged_in_uin or (new_diff[0] if len(new_diff) == 1 else None)

        if target_uin and login_confirmed:
            # 扫码成功：关闭临时前台管道进程，配置 OneBot 端口并以常驻模式启动
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:
                pass

            if not set_current_account(target_uin):
                return {'status':'failed','error':'账号配置写入失败'}
            return {
                "status": "logged_in_and_configured",
                "new_uin": target_uin,
                "qrcode_path": QR_CACHE_IMAGE,
                "available_accounts": get_available_accounts(),
                "message": f"扫码登录成功！已绑定新 QQ 账号 {target_uin} 并配置好 OneBot 11 端口，正在启动后台常驻服务。"
            }

        # 如果超时仍未完成扫码，终止管道进程并返回二维码信息提示
        try:
            proc.kill()
            proc.wait(timeout=3)
        except Exception:
            pass

        return {
            "status": "scan_timed_out",
            "qrcode_generated": os.path.exists(QR_CACHE_IMAGE),
            "qrcode_path": QR_CACHE_IMAGE if os.path.exists(QR_CACHE_IMAGE) else None,
            "qrcode_opened_on_screen": qr_opened,
            "message": (
                f"二维码已生成 ({QR_CACHE_IMAGE}) 并在屏幕弹出，但在 {wait_scan_seconds} 秒内尚未检测到扫码完成。"
                "该登录会话已关闭，原二维码不能继续登录，请重新调用 `login_new_qq_by_qrcode` 生成二维码。"
            )
        }
    except Exception as e:
        try:
            proc.kill()
        except Exception:
            pass
        return {
            "status": "failed",
            "error": f"扫码登录过程发生异常: {e}"
        }
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)
        reader.join(timeout=2)
        if proc.stdout:
            proc.stdout.close()
