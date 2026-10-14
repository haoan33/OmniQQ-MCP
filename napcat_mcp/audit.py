"""Content-free metadata audit records for MCP tool calls."""
import json
import logging
import os
import re
import threading
import time
from pathlib import Path

_audit_lock = threading.Lock()
_logger = logging.getLogger('NapCatMCP.Audit')
_MAX_AUDIT_BYTES = 10_000_000


def _safe_label(value, pattern=r'[A-Za-z0-9_-]{1,80}'):
    return value if isinstance(value, str) and re.fullmatch(pattern, value) else None


def _safe_number(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else (
        value if isinstance(value, str) and value.isascii() and value.isdigit() and len(value) <= 20 else None)


def activity_log_path() -> Path:
    from .config import USER_DATA_DIR
    return Path(os.environ.get('OMNIQQ_ACTIVITY_LOG') or Path(USER_DATA_DIR) / 'logs' / 'mcp_activity.jsonl')


def record_activity(tool, target=None, status=None, result=None, task_id=None, version=None,
                    source='mcp', reason=None):
    """Append metadata only. Message bodies, file contents and credentials stay out of the log."""
    try:
        data = result if isinstance(result, dict) else {}
        payload = data.get('data') if isinstance(data.get('data'), dict) else {}
        message_id = payload.get('message_id') or data.get('message_id')
        path = str(activity_log_path())
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        entry = {
            'ts': round(time.time(), 3), 'source': _safe_label(source), 'task_id': _safe_label(task_id),
            'version': _safe_number(version), 'tool': _safe_label(tool) or '<invalid>',
            'target': _safe_number(target),
            'status': _safe_label(status or data.get('status') or 'unknown'),
            'retcode': _safe_number(data.get('retcode')), 'message_id': _safe_number(message_id),
            'reason': _safe_label(reason),
        }
        with _audit_lock:
            if os.path.exists(path) and os.path.getsize(path) >= _MAX_AUDIT_BYTES:
                Path(f'{path}.3').unlink(missing_ok=True)
                for index in (2, 1):
                    source = f'{path}.{index}'
                    if os.path.exists(source):
                        os.replace(source, f'{path}.{index + 1}')
                os.replace(path, f'{path}.1')
            with open(path, 'a', encoding='utf-8') as stream:
                stream.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception as exc:
        _logger.warning('审计日志写入失败：%s', type(exc).__name__)
