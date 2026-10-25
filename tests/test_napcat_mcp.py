"""
NapCat MCP Server 自动化单元测试与 stdio 协议端到端验证套件
"""
import os
import sys
import json
import subprocess
import unittest
from unittest.mock import AsyncMock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from napcat_mcp.server import NapCatMCPServer
from napcat_mcp.message_buffer import MessageBuffer


class TestNapCatMCP(unittest.IsolatedAsyncioTestCase):

    async def test_structured_message_segments_are_forwarded_unchanged(self):
        from napcat_mcp.tools.messaging import send_private_msg, send_group_msg
        client = type('Client', (), {'call_api': AsyncMock(return_value={'status':'ok'})})()
        message = [{'type':'face','data':{'id':'14'}},
                   {'type':'mface','data':{'emoji_id':'77','key':'k','summary':'微笑'}}]
        await send_private_msg(client, 103, message)
        client.call_api.assert_awaited_with('send_private_msg',
            {'user_id':103,'message':message,'auto_escape':False})
        await send_group_msg(client, 999, message)
        client.call_api.assert_awaited_with('send_group_msg',
            {'group_id':999,'message':message,'auto_escape':False})
        tools = self.server.registry.list_tools()
        send_schema = next(tool['inputSchema'] for tool in tools if tool['name'] == 'send_private_msg')
        self.assertEqual({part['type'] for part in send_schema['properties']['message']['anyOf']},
                         {'string','array'})
        cleaned = MessageBuffer.extract_clean_text({'message': message})
        self.assertIn('表情:14', cleaned)
        self.assertIn('商城表情:微笑', cleaned)

    async def asyncSetUp(self):
        self.release_patch = patch('napcat_mcp.deployer.fetch_github_latest_release', AsyncMock(return_value={'reachable':False,'error':'offline test'}))
        self.release_patch.start()
        self.addCleanup(self.release_patch.stop)
        self.port_patch = patch('napcat_mcp.tools.env_lifecycle.is_port_listening',return_value=False)
        self.port_patch.start()
        self.addCleanup(self.port_patch.stop)
        self.server = NapCatMCPServer()
        # 测试中禁用自动拉起真实进程，防止单元测试产生副作用
        self.server.client.auto_heal = False

    async def asyncTearDown(self):
        await self.server.client.close()

    async def test_01_initialize_and_ping(self):
        """验证 MCP initialize 与 ping 协议响应"""
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            }
        }
        resp = await self.server.handle_request(init_req)
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "omniqq-mcp")
        self.assertIn("tools", resp["result"]["capabilities"])

        # Notification 不应返回响应
        notif_resp = await self.server.handle_request({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        })
        self.assertIsNone(notif_resp)

        # Ping
        ping_resp = await self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "ping"
        })
        self.assertEqual(ping_resp["result"], {})

    async def test_02_tools_list_and_schemas(self):
        """验证默认 14 个核心工具与全量 74 个工具的注册、Annotations、OutputSchema 及 JSON Schema 合法性"""
        resp = await self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/list"
        })
        core_tools = resp["result"]["tools"]
        self.assertEqual(len(core_tools), 14)

        core_names = {t["name"] for t in core_tools}
        expected_core = {
            "check_napcat_environment",
            "deploy_or_update_napcat",
            "login_new_qq_by_qrcode",
            "switch_qq_account",
            "send_private_msg",
            "send_group_msg",
            "delete_msg",
            "upload_private_file",
            "upload_group_file",
            "get_login_info",
            "get_group_list",
            "get_recent_messages",
            "call_napcat_api",
            "list_supported_napcat_actions"
        }
        self.assertEqual(core_names, expected_core)

        # 验证 OMNIQQ_TOOL_PROFILE=full 全量模式下暴露全部 74 个工具
        with patch.dict(os.environ, {"OMNIQQ_TOOL_PROFILE": "full"}):
            full_resp = await self.server.handle_request({
                "jsonrpc": "2.0",
                "id": 30,
                "method": "tools/list"
            })
        all_tools = full_resp["result"]["tools"]
        self.assertEqual(len(all_tools), 74)

        all_names = {t["name"] for t in all_tools}
        self.assertTrue({
            "list_qq_accounts",
            "get_login_qrcode_image",
            "start_napcat_service",
            "stop_napcat_service",
            "restart_napcat_service",
            "set_group_kick",
            "set_group_ban",
        }.issubset(all_names))

        for t in core_tools:
            self.assertNotIn("start_napcat_service", t["description"])
            self.assertNotIn("get_recent_notices_and_requests", t["description"])

        for t in all_tools:
            self.assertTrue(t["description"], f"Tool {t['name']} 缺少描述")
            self.assertNotIn(":param ", t["description"], f"Tool {t['name']} 描述中残留重复的 :param 行")
            self.assertEqual(t["inputSchema"]["type"], "object")
            self.assertIn("properties", t["inputSchema"])
            for p_name, p_schema in t["inputSchema"]["properties"].items():
                self.assertTrue(p_schema.get("description"), f"Tool {t['name']} 参数 {p_name} 缺少 schema 描述")
            self.assertIn("outputSchema", t)
            self.assertEqual(t["outputSchema"]["type"], "object")
            self.assertIn("annotations", t)
            for hint in ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"):
                self.assertIsInstance(t["annotations"].get(hint), bool)

    async def test_03_deploy_safety_gate(self):
        """验证 deploy_or_update_napcat 在 confirmed=False 时严格拦截并返回预览"""
        resp = await self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "deploy_or_update_napcat",
                "arguments": {
                    "action": "deploy",
                    "confirmed": False
                }
            }
        })
        self.assertFalse(resp["result"]["isError"])
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(payload["status"], "confirmation_required")
        self.assertTrue(payload["requires_user_permission"])

    async def test_04_account_list_and_qrcode_tools(self):
        """验证多账号列表查询与二维码信息工具"""
        resp = await self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "list_qq_accounts",
                "arguments": {}
            }
        })
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertEqual(payload["status"], "ok")
        self.assertIn("cached_accounts", payload)
        self.assertIn("default_account", payload)

        qr_resp = await self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "get_login_qrcode_image",
                "arguments": {"open_image": False}
            }
        })
        qr_payload = json.loads(qr_resp["result"]["content"][0]["text"])
        self.assertIn(qr_payload["status"], ("ok", "not_found"))

    async def test_05_list_supported_actions(self):
        """验证 140+ 原生接口目录查询工具"""
        resp = await self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "list_supported_napcat_actions",
                "arguments": {"category": "all"}
            }
        })
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertGreaterEqual(payload["total_count"], 125)
        self.assertIn("messaging", payload["categories"])
        self.assertIn("group_management", payload["categories"])

    async def test_06_message_buffer_and_hooks(self):
        """验证实时消息缓存池、CQ码净化、条件过滤与事件钩子机制"""
        buf = MessageBuffer(maxlen=50)
        hook_received = []
        buf.register_event_hook(lambda ev: hook_received.append(ev))

        # 模拟私聊事件
        buf.push_event({
            "post_type": "message",
            "message_id": 1001,
            "message_type": "private",
            "user_id": 10001,
            "sender": {"user_id": 10001, "nickname": "测试好友"},
            "message": [
                {"type": "text", "data": {"text": "请把汇总表发我"}},
                {"type": "file", "data": {"file": "模板.xlsx", "file_id": "/f123", "file_size": 10240}}
            ],
            "raw_message": "请把汇总表发我",
            "time": 1700000000
        })

        # 模拟群聊事件
        buf.push_event({
            "post_type": "message",
            "message_id": 1002,
            "message_type": "group",
            "group_id": 999888,
            "user_id": 10002,
            "sender": {"user_id": 10002, "card": "班长"},
            "message": [
                {"type": "at", "data": {"qq": "all", "name": "全体成员"}},
                {"type": "text", "data": {"text": "下午三点开班会"}}
            ],
            "raw_message": "[CQ:at,qq=all] 下午三点开班会",
            "time": 1700000010
        })

        self.assertEqual(len(hook_received), 2)

        all_msgs = buf.get_recent_messages(count=10)
        self.assertEqual(len(all_msgs), 2)
        self.assertIn("模板.xlsx", all_msgs[0]["clean_text"])
        self.assertIn("@全体成员", all_msgs[1]["clean_text"])

        # 按群号过滤
        grp_msgs = buf.get_recent_messages(chat_type="group", target_id=999888)
        self.assertEqual(len(grp_msgs), 1)
        self.assertEqual(grp_msgs[0]["message_id"], 1002)

        # 按关键词过滤
        kw_msgs = buf.get_recent_messages(keyword="汇总表")
        self.assertEqual(len(kw_msgs), 1)
        self.assertEqual(kw_msgs[0]["user_id"], 10001)

        # 验证异步协程事件钩子与 raw_event / target_id 字段
        async_received = []

        async def async_hook(ev):
            async_received.append(ev)

        buf.register_event_hook(async_hook)
        buf.push_event({
            "post_type": "message_sent",
            "message_id": 1003,
            "message_type": "private",
            "user_id": 10000,
            "target_id": 10001,
            "message": [{"type": "text", "data": {"text": "收到"}}],
            "raw_message": "收到",
            "time": 1700000020
        })
        import asyncio
        await asyncio.sleep(0.05)
        self.assertEqual(len(async_received), 1)
        self.assertEqual(async_received[0]["target_id"], 10001)
        self.assertIn("raw_event", async_received[0])

    async def test_07_stdio_subprocess_end_to_end(self):
        """验证通过子进程 stdio 管道与 run_mcp.py 进行真实 JSON-RPC 交互"""
        run_script = os.path.join(PROJECT_ROOT, "napcat_mcp", "run_mcp.py")
        proc = subprocess.Popen(
            [sys.executable, run_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )
        try:
            init_line = json.dumps({
                "jsonrpc": "2.0",
                "id": 10,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"}
            }) + "\n"
            proc.stdin.write(init_line)
            proc.stdin.flush()

            out_line = proc.stdout.readline()
            self.assertTrue(out_line)
            resp = json.loads(out_line)
            self.assertEqual(resp["id"], 10)
            self.assertEqual(resp["result"]["serverInfo"]["name"], "omniqq-mcp")
        finally:
            proc.terminate()
            proc.wait(timeout=5)
            for pipe in (proc.stdin, proc.stdout, proc.stderr):
                if pipe:
                    pipe.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
