"""Audit metadata remains useful without retaining chat bodies or credentials."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from napcat_mcp.server import NapCatMCPServer


class ActivityAuditTests(unittest.TestCase):
    def test_mcp_audit_contains_delivery_metadata_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'activity.jsonl'
            with patch.dict(os.environ, {'OMNIQQ_ACTIVITY_LOG': str(path)}):
                NapCatMCPServer._record_mcp_activity(
                    'send_private_msg', {'user_id': 123, 'message': 'private message',
                                         'task_id': 'task-1', 'version': 2, 'token': 'never-log'},
                    {'status': 'ok', 'retcode': 0, 'data': {'message_id': 456,
                                                           'message': 'private response'}}, False)
            raw = path.read_text(encoding='utf-8')
            entry = json.loads(raw)
            self.assertEqual((entry['task_id'], entry['version'], entry['tool'], entry['target'],
                              entry['status'], entry['message_id']),
                             ('task-1', 2, 'send_private_msg', 123, 'ok', 456))
            for secret in ('private message', 'private response', 'never-log'):
                self.assertNotIn(secret, raw)


if __name__ == '__main__':
    unittest.main()
