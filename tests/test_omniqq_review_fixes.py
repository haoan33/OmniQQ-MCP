"""Regression checks for local runtime and protocol safety fixes."""
import tempfile
import subprocess
import sys
import os
import io
import unittest
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from napcat_mcp.client import NapCatClient
from napcat_mcp.message_buffer import MessageBuffer
from napcat_mcp.audit import record_activity
from napcat_mcp.config import kill_napcat_processes, set_current_account
from napcat_mcp.deployer import deploy_or_update_napcat
from napcat_mcp.server import NapCatMCPServer
from napcat_mcp.tools.env_lifecycle import check_napcat_environment
from napcat_mcp.tools.passthrough import NAPCAT_ALL_ACTIONS


class OmniQQReviewFixes(unittest.IsolatedAsyncioTestCase):
    async def test_protocol_negotiates_to_implemented_version(self):
        server = NapCatMCPServer(client=NapCatClient(auto_heal=False))
        result = await server.handle_request({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                                              'params': {'protocolVersion': '2099-01-01'}})
        self.assertEqual(result['result']['protocolVersion'], '2024-11-05')
        await server.client.close()

    async def test_stdio_processes_ping_during_slow_request(self):
        import asyncio
        server = NapCatMCPServer(client=NapCatClient(auto_heal=False))
        async def slow():
            await asyncio.sleep(0.15)
            return {'status': 'ok'}
        server.registry.tools_map['slow_test'] = {'name': 'slow_test', 'handler': lambda client: slow(),
                                                  'inputSchema': {'type': 'object', 'properties': {}}}
        source = io.StringIO(''.join(__import__('json').dumps(item) + '\n' for item in [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'slow_test'}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'ping'}]))
        output = io.StringIO()
        with patch('napcat_mcp.server.sys.stdin', source), patch('napcat_mcp.server.sys.stdout', output), \
             patch.object(server.client, 'start_background_ws'):
            await server.run_stdio()
        replies = [__import__('json').loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual([reply['id'] for reply in replies], [2, 1])

    async def test_cancel_notification_cancels_read_only_request(self):
        import asyncio
        import json
        server = NapCatMCPServer(client=NapCatClient(auto_heal=False))
        async def slow():
            await asyncio.sleep(1)
            return {'status': 'ok'}
        server.registry.tools_map['get_slow_test'] = {'name': 'get_slow_test',
            'handler': lambda client: slow(), 'inputSchema': {'type': 'object', 'properties': {}}}
        requests = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'get_slow_test'}},
            {'jsonrpc': '2.0', 'method': 'notifications/cancelled', 'params': {'requestId': 1}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'ping'}]
        source = io.StringIO(''.join(json.dumps(item) + '\n' for item in requests))
        output = io.StringIO()
        with patch('napcat_mcp.server.sys.stdin', source), patch('napcat_mcp.server.sys.stdout', output), \
             patch.object(server.client, 'start_background_ws'):
            await server.run_stdio()
        replies = {item['id']: item for item in map(json.loads, output.getvalue().splitlines())}
        self.assertEqual(replies[1]['error']['code'], -32800)
        self.assertEqual(replies[2]['result'], {})

    async def test_async_event_hooks_are_ordered_and_bounded(self):
        import asyncio
        buffer = MessageBuffer()
        observed = []
        async def hook(record):
            await asyncio.sleep(0.01)
            observed.append(record['message_id'])
        buffer.register_event_hook(hook)
        for index in range(3):
            await buffer.push_event_async({'post_type': 'message', 'message_type': 'private',
                                           'message_id': index, 'user_id': 123, 'message': 'x'})
        await buffer.close()
        self.assertEqual(observed, [0, 1, 2])

    async def test_external_url_skips_local_runtime(self):
        client = NapCatClient(http_url='https://onebot.example.org', auto_heal=True)
        self.assertFalse(client.uses_local_runtime())
        with patch.object(client, 'call_api', AsyncMock(return_value={'status': 'ok', 'retcode': 0})) as probe, \
             patch('napcat_mcp.tools.env_lifecycle.is_port_listening', side_effect=AssertionError('local port checked')):
            result = await check_napcat_environment(client)
        self.assertEqual(result['mode'], 'external')
        probe.assert_awaited_once()
        self.assertEqual((await client.start_napcat_process())['status'], 'failed')
        await client.close()

    async def test_config_failure_rolls_back_upgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root / 'shell_node'
            installed.mkdir()
            (installed / 'node.exe').write_bytes(b'old')
            (installed / 'index.js').write_bytes(b'old-index')
            archive = root / 'offline.zip'
            with zipfile.ZipFile(archive, 'w') as package:
                package.writestr('node.exe', b'new')
                package.writestr('index.js', b'new-index')
            with patch.multiple('napcat_mcp.deployer', RUNTIME_DIR=str(root), SHELL_NODE_DIR=str(installed),
                                NODE_EXE=str(installed / 'node.exe'), INDEX_JS=str(installed / 'index.js'),
                                LOCAL_RELEASE_ZIP=str(archive)), \
                 patch('napcat_mcp.deployer.fetch_github_latest_release', AsyncMock(return_value={})), \
                 patch('napcat_mcp.deployer.kill_napcat_processes'), \
                 patch('napcat_mcp.deployer.get_current_account', return_value='123456'), \
                 patch('napcat_mcp.deployer.ensure_onebot_config', return_value=False):
                result = await deploy_or_update_napcat(confirmed=True)
            self.assertEqual(result['status'], 'failed')
            self.assertTrue(result['rolled_back'])
            self.assertEqual((installed / 'node.exe').read_bytes(), b'old')

    async def test_health_failure_rolls_back_upgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root / 'shell_node'
            installed.mkdir()
            (installed / 'node.exe').write_bytes(b'old')
            (installed / 'index.js').write_bytes(b'old-index')
            archive = root / 'offline.zip'
            with zipfile.ZipFile(archive, 'w') as package:
                package.writestr('node.exe', b'new')
                package.writestr('index.js', b'new-index')
            with patch.multiple('napcat_mcp.deployer', RUNTIME_DIR=str(root), SHELL_NODE_DIR=str(installed),
                                NODE_EXE=str(installed / 'node.exe'), INDEX_JS=str(installed / 'index.js'),
                                LOCAL_RELEASE_ZIP=str(archive)), \
                 patch('napcat_mcp.deployer.fetch_github_latest_release', AsyncMock(return_value={})), \
                 patch('napcat_mcp.deployer.kill_napcat_processes'), \
                 patch('napcat_mcp.deployer.get_current_account', return_value=''), \
                 patch('napcat_mcp.deployer.check_installed_runtime', side_effect=RuntimeError('bad node')):
                result = await deploy_or_update_napcat(confirmed=True)
            self.assertEqual(result['status'], 'failed')
            self.assertTrue(result['rolled_back'])
            self.assertEqual((installed / 'node.exe').read_bytes(), b'old')


class OmniQQStaticReviewFixes(unittest.TestCase):
    def test_account_buffers_remain_isolated_after_switch(self):
        buffer = MessageBuffer()
        def event(account, message_id):
            return {'self_id': account, 'post_type': 'message', 'message_type': 'private',
                    'user_id': 123, 'message_id': message_id, 'message': 'hello'}
        buffer.push_event(event(111111, 1))
        buffer.select_account('222222')
        buffer.push_event(event(111111, 2))
        buffer.push_event(event(222222, 3))
        self.assertEqual([m['message_id'] for m in buffer.get_recent_messages()], [3])
        buffer.select_account('111111')
        self.assertEqual([m['message_id'] for m in buffer.get_recent_messages()], [1, 2])

    def test_audit_rotates_when_full(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'activity.jsonl'
            with patch.dict(os.environ, {'OMNIQQ_ACTIVITY_LOG': str(path)}), \
                 patch('napcat_mcp.audit._MAX_AUDIT_BYTES', 1):
                record_activity('ping', status='ok')
                record_activity('ping', status='ok')
            self.assertTrue(path.exists())
            self.assertTrue(Path(f'{path}.1').exists())

    def test_audit_rejects_free_text_in_identifier_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'activity.jsonl'
            with patch.dict(os.environ, {'OMNIQQ_ACTIVITY_LOG': str(path)}):
                record_activity('secret message', target='private text', task_id='private text',
                                status='ok', reason='private text')
            self.assertNotIn('private text', path.read_text(encoding='utf-8'))
            self.assertNotIn('secret message', path.read_text(encoding='utf-8'))

    def test_stdio_survives_malformed_requests(self):
        entry = Path(__file__).resolve().parent.parent / 'run_mcp.py'
        result = subprocess.run([sys.executable, str(entry)], input='{broken\n[]\n{"jsonrpc":"2.0","id":7,"method":"ping"}\n',
                                text=True, capture_output=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        import json
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([reply.get('error', {}).get('code') for reply in replies[:2]], [-32700, -32600])
        self.assertEqual(replies[2]['result'], {})

    def test_failed_webui_write_does_not_commit_account(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            account = root / 'current.txt'
            account.write_text('111111\n', encoding='utf-8')
            (root / 'webui.json').write_text('{}', encoding='utf-8')
            with patch('napcat_mcp.config.CURRENT_ACCOUNT_FILE', str(account)), \
                 patch('napcat_mcp.config.NAPCAT_CONFIG_DIR', str(root)), \
                 patch('napcat_mcp.config.ensure_onebot_config', return_value=True), \
                 patch('napcat_mcp.config.atomic_json', side_effect=OSError('read only')):
                self.assertFalse(set_current_account('222222'))
            self.assertEqual(account.read_text(encoding='utf-8'), '111111\n')

    def test_process_cleanup_requires_exact_exe_and_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            exe, entry = root / 'node.exe', root / 'index.js'
            correct = Mock(info={'name': 'node.exe', 'exe': str(exe), 'cwd': str(root),
                                 'cmdline': [str(exe), str(entry)]})
            unrelated = Mock(info={'name': 'node.exe', 'exe': str(exe), 'cwd': str(root),
                                   'cmdline': [str(exe), str(root / 'other.js')]})
            with patch('napcat_mcp.config.NODE_EXE', str(exe)), \
                 patch('napcat_mcp.config.INDEX_JS', str(entry)), \
                 patch('psutil.process_iter', return_value=[correct, unrelated]), \
                 patch('napcat_mcp.config.time.sleep'):
                self.assertEqual(kill_napcat_processes(), 1)
            correct.kill.assert_called_once()
            unrelated.kill.assert_not_called()

    def test_catalog_contains_named_actions(self):
        import ast
        tools = Path(__file__).resolve().parent.parent / 'napcat_mcp' / 'tools'
        named = {call.args[0].value for path in tools.glob('*.py')
                 for call in ast.walk(ast.parse(path.read_text(encoding='utf-8')))
                 if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                 and call.func.attr == 'call_api' and call.args
                 and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str)}
        listed = {action for actions in NAPCAT_ALL_ACTIONS.values() for action in actions}
        self.assertFalse(named - listed, named - listed)


if __name__ == '__main__':
    unittest.main()
