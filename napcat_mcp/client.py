"""
NapCat OneBot 11 异步通信客户端 (HTTP API 调用 + WebSocket 实时事件监听 + 混合自愈启动)
"""
import os
import json
import asyncio
import logging
import subprocess
from urllib.parse import urlsplit
from typing import Any, Optional
import aiohttp
import websockets

from .config import (
    DEFAULT_HTTP_URL,
    DEFAULT_WS_URL,
    DEFAULT_HTTP_PORT,
    DEFAULT_WS_PORT,
    SHELL_NODE_DIR,
    NODE_EXE,
    INDEX_JS,
    is_port_listening,
    get_current_account,
    ensure_onebot_config,
)
from .message_buffer import MessageBuffer
from .token_store import load_onebot_token, ensure_onebot_token, save_verified_onebot_token

logger = logging.getLogger("NapCatMCP.Client")


class NapCatClient:
    """OneBot 11 标准与扩展协议通信核心客户端"""

    def __init__(
        self,
        http_url: str = DEFAULT_HTTP_URL,
        ws_url: str = DEFAULT_WS_URL,
        token: Optional[str] = None,
        auto_heal: bool = True,
        buffer_maxlen: int = 200
    ):
        self.http_url = http_url.rstrip("/")
        self.ws_url = ws_url.rstrip("/")
        self.token = load_onebot_token() if token is None else token
        self.auto_heal = auto_heal
        self.buffer = MessageBuffer(maxlen=buffer_maxlen)

        self._session: Optional[aiohttp.ClientSession] = None
        self._ws_task: Optional[asyncio.Task] = None
        self.on_ws_connected = None
        self.on_close = None
        self._running = False
        self._ws_connected = False
        self._start_lock = asyncio.Lock()

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if not self.token:
            self.token = load_onebot_token()
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def uses_local_runtime(self) -> bool:
        endpoint = urlsplit(self.http_url)
        return endpoint.hostname in ('localhost', '127.0.0.1', '::1') and (endpoint.port or 80) == DEFAULT_HTTP_PORT

    async def ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _recover_local_token(self) -> bool:
        """Use a changed local NapCat config only after it authenticates a read-only probe."""
        from .config import NAPCAT_CONFIG_DIR
        account = get_current_account()
        if not account:
            return False
        try:
            with open(os.path.join(NAPCAT_CONFIG_DIR, f'onebot11_{account}.json'), encoding='utf-8') as stream:
                network = json.load(stream).get('network', {})
            servers = network.get('httpServers') or []
            candidate = next((item.get('token') for item in servers if item.get('name') == 'httpServer'), None)
            if not candidate or candidate == self.token:
                return False
            session = await self.ensure_session()
            async with session.post(self.http_url + '/get_login_info', json={},
                                    headers={'Authorization': f'Bearer {candidate}'},
                                    timeout=aiohttp.ClientTimeout(total=5)) as response:
                data = await response.json()
                if response.status != 200 or data.get('status') != 'ok' or data.get('retcode', 0) != 0:
                    return False
                if str((data.get('data') or {}).get('user_id')) != account:
                    return False
            save_verified_onebot_token(candidate)
            self.token = candidate
            logger.warning('检测到 OneBot Token 已变化，已用只读查询验证并同步本地凭据')
            return True
        except Exception as exc:
            logger.warning('OneBot Token 校准失败：%s', type(exc).__name__)
            return False

    async def start_napcat_process(self, uin: Optional[str] = None, wait_seconds: int = 25) -> dict[str, Any]:
        if not self.uses_local_runtime():
            return {'status': 'failed', 'error': '当前使用外部 OneBot URL，不能启动本地 NapCat'}
        async with self._start_lock:
            return await self._start_napcat_process(uin, wait_seconds)

    async def _start_napcat_process(self, uin: Optional[str], wait_seconds: int) -> dict[str, Any]:
        """
        启动本地 NapCat 沙箱进程 (混合自愈能力)
        若端口已监听则直接返回就绪；否则拉起本地沙箱 Node。
        """
        if is_port_listening(DEFAULT_HTTP_PORT):
            return {
                "status": "already_running",
                "http_port": DEFAULT_HTTP_PORT,
                "ws_port": DEFAULT_WS_PORT,
                "message": "NapCat 服务已在运行中，无需重复启动。"
            }

        if not (os.path.exists(NODE_EXE) and os.path.exists(INDEX_JS)):
            return {
                "status": "not_installed",
                "error": f"未找到 NapCat 运行时文件 ({NODE_EXE})，请先调用 check_napcat_environment 或 deploy_or_update_napcat 进行部署。"
            }

        self.token = ensure_onebot_token()
        account = str(uin or get_current_account()).strip()
        if account:
            if not ensure_onebot_config(account, token=self.token):
                return {'status': 'failed', 'error': '无法写入带 Token 的 OneBot 配置'}

        cmd = [NODE_EXE, INDEX_JS]
        if account:
            cmd.extend(["-q", account])

        try:
            if os.name == "nt":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = 7  # SW_SHOWMINNOACTIVE: 最小化无焦点启动，不打扰用户工作窗口
                subprocess.Popen(
                    cmd,
                    cwd=SHELL_NODE_DIR,
                    startupinfo=si,
                    creationflags=0x00000010  # CREATE_NEW_CONSOLE
                )
            else:
                subprocess.Popen(cmd, cwd=SHELL_NODE_DIR)
        except Exception as e:
            return {
                "status": "failed",
                "error": f"拉起 NapCat 进程失败: {e}"
            }

        # 等待端口就绪
        for _ in range(wait_seconds * 2):
            if is_port_listening(DEFAULT_HTTP_PORT):
                return {
                    "status": "started",
                    "uin": account,
                    "http_port": DEFAULT_HTTP_PORT,
                    "ws_port": DEFAULT_WS_PORT,
                    "message": f"NapCat 服务已成功拉起并监听端口 {DEFAULT_HTTP_PORT}/{DEFAULT_WS_PORT}。"
                }
            await asyncio.sleep(0.5)

        return {
            "status": "starting_pending_login",
            "uin": account,
            "message": "NapCat 进程已启动，但 OneBot 端口尚未就绪（可能需要扫码登录或正在初始化，请检查最小化的 NapCat 窗口）。"
        }

    async def call_api(
        self,
        action: str,
        params: Optional[dict[str, Any]] = None,
        timeout: float = 30.0,
        _auth_retry: bool = True,
    ) -> dict[str, Any]:
        """
        调用任意 NapCat OneBot 11 HTTP API 接口
        :param action: 接口名称 (如 'send_private_msg', 'get_group_list' 等)
        :param params: JSON 参数字典
        :param timeout: 超时时间（秒）
        """
        action_clean = action.strip().lstrip("/")
        payload = params or {}

        # 清理 payload 中值为 None 的可选字段，避免部分严格校验接口报错
        clean_payload = {k: v for k, v in payload.items() if v is not None}


        # 若本地端口未监听且开启了混合自愈，尝试自动拉起
        local_default = self.uses_local_runtime()
        if self.auto_heal and local_default and not await asyncio.to_thread(is_port_listening, DEFAULT_HTTP_PORT):
            heal_res = await self.start_napcat_process(wait_seconds=15)
            if heal_res.get("status") in ("not_installed", "failed"):
                return {
                    "status": "failed",
                    "retcode": -1,
                    "action": action_clean,
                    "error": heal_res.get("error"),
                    "environment_hint": "请调用 check_napcat_environment 查看详情，或调用 deploy_or_update_napcat 部署环境。"
                }

        url = f"{self.http_url}/{action_clean}"
        session = await self.ensure_session()

        try:
            async with session.post(
                url,
                json=clean_payload,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                text = await resp.text()
                if resp.status == 403 and local_default and _auth_retry and await self._recover_local_token():
                    return await self.call_api(action, params, timeout, _auth_retry=False)
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    return {
                        "status": "failed",
                        "retcode": resp.status,
                        "action": action_clean,
                        "error": f"非 JSON 响应 (HTTP {resp.status}): {text[:300]}"
                    }
                if not isinstance(data, dict):
                    return {'status':'failed','retcode':-103,'action':action_clean,'error':'OneBot 响应必须为 JSON 对象'}
                if resp.status >= 400:
                    return {**data,'status':'failed','retcode':resp.status,'action':action_clean}
                return data
        except (aiohttp.ClientConnectorError, ConnectionRefusedError) as e:
            return {
                "status": "failed",
                "retcode": -100,
                "action": action_clean,
                "error": f"无法连接到 NapCat HTTP 服务 ({self.http_url}): {e}",
                "advice": "请确认 NapCat 已启动并登录 QQ，或调用 start_napcat_service / check_napcat_environment。"
            }
        except asyncio.TimeoutError:
            return {
                "status": "failed",
                "retcode": -101,
                "action": action_clean,
                "error": f"调用接口 {action_clean} 超时 ({timeout}s)"
            }
        except Exception as e:
            return {
                "status": "failed",
                "retcode": -102,
                "action": action_clean,
                "error": f"调用接口 {action_clean} 发生异常: {e}"
            }

    async def _ws_loop(self):
        """后台 WebSocket 实时事件监听协程 (支持自动断线重连)"""
        while self._running:
            try:
                headers = self._get_headers()
                async with websockets.connect(
                    self.ws_url,
                    additional_headers=headers if headers else None,
                    ping_interval=20,
                    ping_timeout=20
                ) as ws:
                    self._ws_connected = True
                    logger.info(f"成功连接 NapCat WebSocket 事件流: {self.ws_url}")
                    if self.on_ws_connected:
                        await self.on_ws_connected()
                    async for raw_msg in ws:
                        if not self._running:
                            break
                        try:
                            event = json.loads(raw_msg)
                            if isinstance(event, dict) and event.get('retcode') == 1403:
                                self._ws_connected = False
                                if not await self._recover_local_token():
                                    await asyncio.sleep(3)
                                break
                            await self.buffer.push_event_async(event)
                        except Exception as e:
                            logger.warning(f"解析 WS 事件失败: {e}")
                self._ws_connected = False
            except Exception as e:
                self._ws_connected = False
                logger.warning(f"WebSocket 连接中断 ({e})，3 秒后尝试重连...")
                await asyncio.sleep(3)

    def start_background_ws(self):
        """启动后台 WebSocket 监听任务"""
        if not self._running:
            self._running = True
            self._ws_task = asyncio.create_task(self._ws_loop())

    async def close(self):
        """优雅关闭客户端连接与后台任务"""
        self._running = False
        self._ws_connected = False
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        if self._session and not self._session.closed:
            await self._session.close()
        await self.buffer.close()
        if self.on_close:
            self.on_close()

    @property
    def is_ws_connected(self) -> bool:
        return self._ws_connected
