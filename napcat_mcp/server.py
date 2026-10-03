"""
NapCat MCP Server 核心协议调度器 (标准 JSON-RPC 2.0 over stdio)
100% 遵循 Model Context Protocol 官方规范，无需外部重量级框架依赖。
"""
import os
import sys
import json
import asyncio
import logging
import traceback
from typing import Any, Dict, Optional

from . import __version__
from .client import NapCatClient
from .deployer import check_napcat_environment
from .tools import registry

# 导入所有工具子模块以触发 @registry.register() 装饰器注册
from .tools import (  # noqa: F401
    env_lifecycle,
    messaging,
    group_admin,
    files,
    friends_account,
    queries,
    realtime,
    passthrough,
)

logger = logging.getLogger("NapCatMCP.Server")


class NapCatMCPServer:
    """标准 MCP (Model Context Protocol) 服务端实现"""

    def __init__(self, client: Optional[NapCatClient] = None):
        self.client = client or NapCatClient()
        self.server_info = {
            "name": "omniqq-mcp",
            "version": __version__
        }

    async def handle_request(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """处理单条 JSON-RPC 2.0 消息；若是 Notification (无 id) 则返回 None"""
        msg_id = message.get("id")
        method = message.get("method", "")
        params = message.get("params") or {}

        # Notification 通知无需返回响应包
        if msg_id is None:
            if method == "notifications/initialized":
                logger.info("MCP 客户端已完成初始化握手 (notifications/initialized)")
            return None

        try:
            if method == "initialize":
                client_proto = params.get("protocolVersion", "2024-11-05")
                result = {
                    "protocolVersion": client_proto,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False}
                    },
                    "serverInfo": self.server_info,
                    "instructions": (
                        "OmniQQ-MCP (NapCat OneBot 11) 全功能控制与感知 MCP 服务。"
                        "支持发送私聊/群聊消息、合并转发、撤回、群管控制、群文件上传下载、OCR、"
                        "好友与资料管理、二维码扫码登录、多账号热切换、实时消息读取以及 144+ 原生接口透传。"
                        "若连接失败，请先调用 check_napcat_environment 诊断环境。"
                    )
                }
                return self._ok_response(msg_id, result)

            elif method == "ping":
                return self._ok_response(msg_id, {})

            elif method == "tools/list":
                return self._ok_response(msg_id, {
                    "tools": registry.list_tools()
                })

            elif method == "tools/call":
                tool_name = params.get("name", "")
                arguments = params.get("arguments") or {}
                return await self._handle_tool_call(msg_id, tool_name, arguments)

            elif method == "resources/list":
                return self._ok_response(msg_id, {
                    "resources": [
                        {
                            "uri": "napcat://messages/recent",
                            "name": "近期收到的实时 QQ 消息流",
                            "description": "后台 WebSocket 实时监听并滚动缓存的最新 QQ 私聊与群聊消息",
                            "mimeType": "application/json"
                        },
                        {
                            "uri": "napcat://environment/status",
                            "name": "NapCat 环境与运行状态诊断",
                            "description": "本地 NapCat 运行时安装情况、端口状态与版本信息",
                            "mimeType": "application/json"
                        }
                    ]
                })

            elif method == "resources/read":
                uri = params.get("uri", "")
                if uri == "napcat://messages/recent":
                    msgs = self.client.buffer.get_recent_messages(count=50)
                    data_str = json.dumps(msgs, ensure_ascii=False, indent=2)
                elif uri == "napcat://environment/status":
                    env_data = await check_napcat_environment()
                    data_str = json.dumps(env_data, ensure_ascii=False, indent=2)
                else:
                    return self._error_response(msg_id, -32602, f"未知 Resource URI: {uri}")

                return self._ok_response(msg_id, {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": data_str
                        }
                    ]
                })

            elif method == "prompts/list":
                return self._ok_response(msg_id, {
                    "prompts": [
                        {
                            "name": "omniqq_control_guide",
                            "description": "获取使用 OmniQQ-MCP 控制 QQ 的最佳实践指南与常用工作流",
                            "arguments": []
                        }
                    ]
                })

            elif method == "prompts/get":
                pname = params.get("name", "")
                if pname in ("omniqq_control_guide", "napcat_control_guide"):
                    return self._ok_response(msg_id, {
                        "description": "OmniQQ-MCP 控制指南",
                        "messages": [
                            {
                                "role": "user",
                                "content": {
                                    "type": "text",
                                    "text": (
                                        "请使用 omniqq-mcp / napcat-mcp 工具控制 QQ：\n"
                                        "1. 首选调用 `check_napcat_environment` 或 `get_login_info` 确认连接状态；\n"
                                        "2. 若环境未安装，询问用户许可后调用 `deploy_or_update_napcat(confirmed=True)`；\n"
                                        "3. 支持 `login_new_qq_by_qrcode` 扫码登录新账号，或 `switch_qq_account` 免扫码热切换已保存账号；\n"
                                        "4. 查看新消息使用 `get_recent_messages`，查历史使用 `get_friend_msg_history` / `get_group_msg_history`；\n"
                                        "5. 任何未单独列出的扩展接口均可通过 `call_napcat_api` 直接调用。"
                                    )
                                }
                            }
                        ]
                    })
                return self._error_response(msg_id, -32602, f"未知 Prompt: {pname}")

            else:
                return self._error_response(msg_id, -32601, f"未支持的方法: {method}")

        except Exception as e:
            logger.error(f"处理请求 {method} 发生异常: {e}\n{traceback.format_exc()}")
            return self._error_response(msg_id, -32603, f"服务器内部错误: {e}")

    async def _handle_tool_call(
        self,
        msg_id: Any,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        tool = registry.get_tool(tool_name)
        if not tool:
            return self._ok_response(msg_id, {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "status": "error",
                            "error": f"未找到名为 '{tool_name}' 的工具。请检查工具名称或使用 call_napcat_api。"
                        }, ensure_ascii=False)
                    }
                ],
                "isError": True
            })

        handler = tool["handler"]
        try:
            res = await handler(client=self.client, **arguments)
            is_err = isinstance(res, dict) and res.get("status") in ("failed", "error")
            text_out = json.dumps(res, ensure_ascii=False, indent=2)
            return self._ok_response(msg_id, {
                "content": [
                    {
                        "type": "text",
                        "text": text_out
                    }
                ],
                "isError": bool(is_err)
            })
        except TypeError as te:
            return self._ok_response(msg_id, {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "status": "error",
                            "tool": tool_name,
                            "error": f"参数类型或必填项不匹配: {te}",
                            "expected_schema": tool["inputSchema"]
                        }, ensure_ascii=False, indent=2)
                    }
                ],
                "isError": True
            })
        except Exception as e:
            return self._ok_response(msg_id, {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({
                            "status": "error",
                            "tool": tool_name,
                            "error": f"工具执行异常: {e}"
                        }, ensure_ascii=False, indent=2)
                    }
                ],
                "isError": True
            })

    @staticmethod
    def _ok_response(msg_id: Any, result: Any) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result
        }

    @staticmethod
    def _error_response(msg_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": code,
                "message": message
            }
        }

    async def run_stdio(self):
        """以标准 stdio 模式运行 MCP 服务主循环"""
        # 启动后台 WebSocket 实时消息监听任务
        self.client.start_background_ws()
        loop = asyncio.get_running_loop()

        try:
            while True:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                line_str = line.strip()
                if not line_str:
                    continue

                try:
                    req = json.loads(line_str)
                except json.JSONDecodeError as je:
                    err_resp = self._error_response(None, -32700, f"JSON 解析错误: {je}")
                    sys.stdout.write(json.dumps(err_resp, ensure_ascii=False) + "\n")
                    sys.stdout.flush()
                    continue

                resp = await self.handle_request(req)
                if resp is not None:
                    sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                    sys.stdout.flush()
        finally:
            await self.client.close()


def export_antigravity_schemas(target_dir: str) -> int:
    """
    导出 Antigravity 宿主环境所需的独立工具 JSON Schema 文件与 instructions.md
    """
    os.makedirs(target_dir, exist_ok=True)
    count = 0
    for tool in registry.list_tools():
        t_name = tool["name"]
        params_schema = dict(tool["inputSchema"])
        params_schema["additionalProperties"] = False
        schema_doc = {
            "name": t_name,
            "description": tool["description"],
            "parameters": params_schema
        }
        fp = os.path.join(target_dir, f"{t_name}.json")
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(schema_doc, f, ensure_ascii=False)
        count += 1

    instructions_path = os.path.join(target_dir, "instructions.md")
    instructions_content = (
        "# NapCat MCP Server 使用指南\n\n"
        "本服务提供完整的 NapCatQQ (OneBot 11) 控制与感知能力，无任何硬编码业务过滤规则。\n\n"
        "## 核心建议\n"
        "- **环境诊断与自动部署**：首次使用或连接异常时，优先调用 `check_napcat_environment`。若未安装，征得用户同意后调用 `deploy_or_update_napcat(confirmed=True)`。\n"
        "- **实时消息获取**：调用 `get_recent_messages` 获取后台 WebSocket 实时监听到的最新私聊/群聊消息。\n"
        "- **全量接口调用**：除 46 个高频具名工具外，可通过 `call_napcat_api` 调用全部 144+ 项 NapCat 原生接口。\n"
    )
    with open(instructions_path, "w", encoding="utf-8") as f:
        f.write(instructions_content)

    return count
