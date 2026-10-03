"""
NapCat OneBot 11 异步通信客户端 (HTTP API 调用 + WebSocket 实时事件监听 + 混合自愈启动)
"""
import os
import json
import asyncio
import logging
import subprocess
from typing import Any, Optional
import aiohttp
import websockets

from .config import (
    DEFAULT_HTTP_URL,
    DEFAULT_WS_URL,
    DEFAULT_HTTP_PORT,
    DEFAULT_WS_PORT,
    DEFAULT_TOKEN,
    SHELL_NODE_DIR,
    NODE_EXE,
    INDEX_JS,
    is_port_listening,
    get_current_account,
    ensure_onebot_config,
)
from .message_buffer import MessageBuffer

logger = logging.getLogger("NapCatMCP.Client")


class NapCatClient:
    """OneBot 11 标准与扩展协议通信核心客户端"""

    def __init__(
        self,
        http_url: str = DEFAULT_HTTP_URL,
        ws_url: str = DEFAULT_WS_URL,
        token: str = DEFAULT_TOKEN,
        auto_heal: bool = True,
        buffer_maxlen: int = 200
    ):
        self.http_url = http_url.rstrip("/")
        self.ws_url = ws_url.rstrip("/")
        self.token = token
        self.auto_heal = auto_heal
        self.buffer = MessageBuffer(maxlen=buffer_maxlen)

        self._session: Optional[aiohttp.ClientSession] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._running = False
        self._ws_connected = False

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def start_napcat_process(self, uin: Optional[str] = None, wait_seconds: int = 25) -> dict[str, Any]:
        """
        启动本地 NapCat 沙箱进程 (混合自愈能力)
        若端口已监听则直接返回就绪；否则拉起 napcat_runtime\shell_node\node.exe。
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

        account = str(uin or get_current_account()).strip()
        if account:
            ensure_onebot_config(account)

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
        timeout: float = 30.0
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
        if self.auto_heal and not is_port_listening(DEFAULT_HTTP_PORT):
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
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    return {
                        "status": "failed",
                        "retcode": resp.status,
                        "action": action_clean,
                        "error": f"非 JSON 响应 (HTTP {resp.status}): {text[:300]}"
                    }
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
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        while self._running:
            if not is_port_listening(DEFAULT_WS_PORT):
                self._ws_connected = False
                await asyncio.sleep(3)
                continue

            try:
                async with websockets.connect(
                    self.ws_url,
                    additional_headers=headers if headers else None,
                    ping_interval=20,
                    ping_timeout=20
                ) as ws:
                    self._ws_connected = True
                    logger.info(f"成功连接 NapCat WebSocket 事件流: {self.ws_url}")
                    async for raw_msg in ws:
                        if not self._running:
                            break
                        try:
                            event = json.loads(raw_msg)
                            self.buffer.push_event(event)
                        except Exception as e:
                            logger.debug(f"解析 WS 事件失败: {e}")
            except Exception as e:
                self._ws_connected = False
                logger.debug(f"WebSocket 连接断开 ({e})，3 秒后重连...")
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

    @property
    def is_ws_connected(self) -> bool:
        return self._ws_connected
