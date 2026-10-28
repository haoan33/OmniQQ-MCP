"""Offline reproductions for the October 2026 robustness review."""
import asyncio
import io
import json
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from napcat_mcp.client import NapCatClient
from napcat_mcp.message_buffer import MessageBuffer
from napcat_mcp.server import NapCatMCPServer
from napcat_mcp.deployer import deploy_or_update_napcat
from napcat_mcp.tools.env_lifecycle import switch_qq_account


def event(account=111111, message_id=1, **values):
    result = dict(self_id=account, post_type='message', message_type='private',
                  message_id=message_id, user_id=333333, message='hello')
    result.update(values)
    return result


class BufferHardeningTests(unittest.IsolatedAsyncioTestCase):
    async def test_queued_hooks_do_not_cross_account_switch(self):
        buffer = MessageBuffer()
        observed = []
        buffer.register_event_hook(lambda record: observed.append(record['message_id']))
        await buffer.push_event_async(event(message_id=1))
        buffer.select_account('222222')
        await buffer.push_event_async(event(account=222222, message_id=2))
        await buffer.close()
        self.assertEqual(observed, [2])

    async def test_switching_away_and_back_invalidates_old_queued_hooks(self):
        buffer = MessageBuffer()
        observed = []
        buffer.register_event_hook(lambda record: observed.append(record['message_id']))
        await buffer.push_event_async(event(message_id=1))
        buffer.select_account('222222')
        buffer.select_account('111111')
        await buffer.push_event_async(event(message_id=2))
        await buffer.close()
        self.assertEqual(observed, [2])

    async def test_clear_removes_all_current_account_event_types_only(self):
        buffer = MessageBuffer()
        buffer.push_event(event())
        buffer.push_event(event(post_type='notice'))
        buffer.push_event(event(post_type='request'))
        buffer.push_event(event(account=222222, message_id=2))
        self.assertEqual(buffer.clear(), 3)
        self.assertEqual(buffer.get_recent_notices_and_requests(), {'notices': [], 'requests': []})
        buffer.select_account('222222')
        self.assertEqual(len(buffer.get_recent_messages()), 1)
        await buffer.close()

    async def test_explicit_group_filter_does_not_match_member_in_other_group(self):
        buffer = MessageBuffer()
        buffer.push_event(event(message_type='group', group_id=444444))
        self.assertEqual(buffer.get_recent_messages(chat_type='group', target_id=333333), [])
        self.assertEqual(len(buffer.get_recent_messages(chat_type='all', target_id=333333)), 1)
        await buffer.close()

    async def test_malformed_optional_fields_do_not_drop_message(self):
        for values in ({'sender': ['invalid']}, {'time': 'not-a-timestamp'},
                       {'time': 1e100}, {'message': [{'type': 'text', 'data': {'text': 123}}]},
                       {'message': [{'type': 'text', 'data': 'invalid'}]}):
            with self.subTest(values=values):
                buffer = MessageBuffer()
                result = buffer.push_event(event(**values))
                self.assertIsNotNone(result)
                self.assertIsInstance(result['clean_text'], str)
                self.assertIsInstance(result['datetime'], str)
                await buffer.close()


class ProtocolHardeningTests(unittest.IsolatedAsyncioTestCase):
    async def run_requests(self, requests, configure=None):
        server = NapCatMCPServer(client=NapCatClient(token='test', auto_heal=False))
        if configure:
            configure(server)
        source = io.StringIO(''.join(json.dumps(value) + '\n' for value in requests))
        output = io.StringIO()
        with patch('napcat_mcp.server.sys.stdin', source), \
             patch('napcat_mcp.server.sys.stdout', output), \
             patch.object(server.client, 'start_background_ws'):
            await server.run_stdio()
        return [json.loads(line) for line in output.getvalue().splitlines()]

    async def test_invalid_ids_cannot_kill_following_ping(self):
        requests = [{'jsonrpc': '2.0', 'id': value, 'method': 'ping'}
                    for value in ([], {}, True, 1.5)]
        replies = await self.run_requests(requests + [{'jsonrpc': '2.0', 'id': 99, 'method': 'ping'}])
        self.assertEqual(sum(reply.get('error', {}).get('code') == -32600 for reply in replies), 4)
        self.assertEqual(next(reply for reply in replies if reply['id'] == 99)['result'], {})

    async def test_invalid_tool_names_cannot_kill_following_ping(self):
        requests = [{'jsonrpc': '2.0', 'id': index, 'method': 'tools/call', 'params': {'name': value}}
                    for index, value in enumerate(([], {}, 7), 1)]
        replies = await self.run_requests(requests + [{'jsonrpc': '2.0', 'id': 99, 'method': 'ping'}])
        self.assertEqual(len(replies), 4)
        self.assertTrue(all(reply.get('error', {}).get('code') == -32602
                            for reply in replies if reply['id'] != 99))

    async def test_invalid_cancellation_id_cannot_kill_following_ping(self):
        replies = await self.run_requests([
            {'jsonrpc': '2.0', 'method': 'notifications/cancelled', 'params': {'requestId': []}},
            {'jsonrpc': '2.0', 'id': 99, 'method': 'ping'}])
        self.assertEqual(replies[-1]['result'], {})

    async def test_ping_remains_responsive_when_eight_tool_slots_are_busy(self):
        async def slow(client):
            await asyncio.sleep(0.1)
            return {'status': 'ok'}
        def configure(server):
            server.registry.tools_map['get_slow'] = {'name': 'get_slow', 'handler': slow,
                'inputSchema': {'type': 'object', 'properties': {}}}
        requests = [{'jsonrpc': '2.0', 'id': index, 'method': 'tools/call', 'params': {'name': 'get_slow'}}
                    for index in range(8)]
        replies = await self.run_requests(requests + [{'jsonrpc': '2.0', 'id': 99, 'method': 'ping'}], configure)
        self.assertEqual(replies[0]['id'], 99)


class ClientHardeningTests(unittest.IsolatedAsyncioTestCase):
    async def test_external_endpoint_accepts_explicit_private_token_file(self):
        with patch.dict('os.environ', {'OMNIQQ_ONEBOT_TOKEN_FILE': 'explicit-remote-token-file'}), \
             patch('napcat_mcp.client.load_onebot_token', return_value='explicit-remote-token') as load:
            client = NapCatClient(http_url='https://example.invalid', auto_heal=False)
            self.assertEqual(client._get_headers()['Authorization'], 'Bearer explicit-remote-token')
            load.assert_called_once()
            await client.close()

    async def test_external_endpoint_requires_explicit_token(self):
        with patch('napcat_mcp.client.load_onebot_token', return_value='local-secret') as load:
            client = NapCatClient(http_url='https://example.invalid', auto_heal=False)
            self.assertNotIn('Authorization', client._get_headers())
            load.assert_not_called()
            await client.close()
        client = NapCatClient(http_url='https://example.invalid', token='explicit-remote-token', auto_heal=False)
        self.assertEqual(client._get_headers()['Authorization'], 'Bearer explicit-remote-token')
        await client.close()

    async def test_already_running_does_not_kill_qq(self):
        client = NapCatClient(token='test', auto_heal=False)
        with patch('napcat_mcp.client.is_port_listening', return_value=True), \
             patch('napcat_mcp.client.kill_qq_processes') as kill:
            result = await client.start_napcat_process()
        self.assertEqual(result['status'], 'already_running')
        kill.assert_not_called()
        await client.close()

    async def test_missing_runtime_does_not_kill_qq(self):
        client = NapCatClient(token='test', auto_heal=False)
        with patch('napcat_mcp.client.is_port_listening', return_value=False), \
             patch('napcat_mcp.client.os.path.exists', return_value=False), \
             patch('napcat_mcp.client.kill_qq_processes') as kill:
            result = await client.start_napcat_process()
        self.assertEqual(result['status'], 'not_installed')
        kill.assert_not_called()
        await client.close()

    async def test_external_endpoint_never_receives_local_recovery_token(self):
        client = NapCatClient(http_url='https://example.invalid', token='test', auto_heal=False)
        with patch('napcat_mcp.client.get_current_account', return_value='123456'), \
             patch('builtins.open', __import__('unittest.mock', fromlist=['mock_open']).mock_open(
                 read_data=json.dumps({'network': {'httpServers': [{'name': 'httpServer', 'token': 'secret'}]}}))), \
             patch.object(client, 'ensure_session', AsyncMock(side_effect=AssertionError('credential leaked'))) as session:
            self.assertFalse(await client._recover_local_token())
            session.assert_not_awaited()
        await client.close()

    async def test_clean_websocket_closures_have_increasing_retry_delay(self):
        client = NapCatClient(token='test', auto_heal=False)
        connections = []
        class EmptyConnection:
            async def __aenter__(self):
                connections.append(1)
                return self
            async def __aexit__(self, *args):
                if len(connections) == 3:
                    client._running = False
            def __aiter__(self):
                return self
            async def __anext__(self):
                raise StopAsyncIteration
        client._running = True
        with patch('napcat_mcp.client.websockets.connect', side_effect=lambda *a, **k: EmptyConnection()), \
             patch('napcat_mcp.client.asyncio.sleep', AsyncMock()) as sleep:
            await client._ws_loop()
        delays = [call.args[0] for call in sleep.await_args_list]
        self.assertEqual(len(delays), 2)
        self.assertGreater(delays[0], 0)
        self.assertGreater(delays[1], delays[0])
        self.assertFalse(client.is_ws_connected)
        await client.close()


class LifecycleHardeningTests(unittest.IsolatedAsyncioTestCase):
    async def test_confirmed_deployments_do_not_overlap(self):
        active = 0
        maximum = 0
        async def deploy(*args):
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            await asyncio.sleep(0.01)
            active -= 1
            return {'status': 'success'}
        with patch('napcat_mcp.deployer._deploy_or_update_napcat', side_effect=deploy), \
             patch('napcat_mcp.deployer._deployment_lock', asyncio.Lock()):
            await asyncio.gather(deploy_or_update_napcat(confirmed=True),
                                 deploy_or_update_napcat(confirmed=True))
        self.assertEqual(maximum, 1)

    async def test_deployment_health_check_does_not_block_event_loop(self):
        entered = threading.Event()
        heartbeat = threading.Event()
        def health():
            entered.set()
            if not heartbeat.wait(timeout=1):
                raise RuntimeError('event loop was blocked by deployment')
            return {'node_version': 'test', 'entry_syntax': 'ok'}
        async def beat():
            while not entered.is_set():
                await asyncio.sleep(0.001)
            heartbeat.set()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root / 'shell_node'
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
                 patch('napcat_mcp.deployer.check_installed_runtime', side_effect=health):
                result, _ = await asyncio.gather(deploy_or_update_napcat(confirmed=True), beat())
            self.assertEqual(result['status'], 'success')
            self.assertTrue(heartbeat.is_set())

    async def test_deferred_switch_keeps_live_account_buffer(self):
        client = NapCatClient(token='test', auto_heal=False)
        client.buffer.select_account('111111')
        with patch('napcat_mcp.tools.env_lifecycle.set_current_account', return_value=True), \
             patch('napcat_mcp.tools.env_lifecycle.get_available_accounts', return_value=[]):
            result = await switch_qq_account(client, '222222', restart_immediately=False)
        self.assertFalse(result['restarted'])
        self.assertEqual(client.buffer.active_account, '111111')
        await client.close()

    async def test_failed_upgrade_preserves_broken_installation_account_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root / 'shell_node'
            (installed / 'napcat' / 'cache').mkdir(parents=True)
            original = installed / 'napcat' / 'cache' / 'account.dat'
            original.write_bytes(b'original-account-data')
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
            self.assertTrue(original.exists(), 'rollback deleted pre-existing account data')
            self.assertEqual(original.read_bytes(), b'original-account-data')
            self.assertFalse((installed / 'node.exe').exists())


if __name__ == '__main__':
    unittest.main()
