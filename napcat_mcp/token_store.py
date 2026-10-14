"""Local OneBot credential shared by NapCat, the service, and OmniQQ-MCP.

The token is kept outside the project and is never placed in Agent prompts or
the project's YAML configuration. This is a best-effort boundary: an Agent
running arbitrary commands as the same Windows user can still read it.
"""
import getpass
import os
import secrets
import subprocess
import tempfile
from pathlib import Path


def token_path() -> Path:
    explicit = os.environ.get('OMNIQQ_ONEBOT_TOKEN_FILE')
    if explicit:
        return Path(explicit).expanduser()
    base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
    return Path(base) / 'OmniQQ-MCP' / 'onebot-token'


def load_onebot_token() -> str:
    path = token_path()
    if not path.exists():
        return ''
    value = path.read_text(encoding='ascii').strip()
    if not value:
        raise RuntimeError('OneBot Token 文件为空')
    return value


def restrict_credential_acl(path: Path) -> None:
    if os.name != 'nt':
        path.chmod(0o600)
        return
    user = getpass.getuser()
    flags = subprocess.CREATE_NO_WINDOW
    result = subprocess.run(
        ['icacls', str(path), '/inheritance:r', '/grant:r', f'{user}:F', 'SYSTEM:F'],
        capture_output=True, text=True, creationflags=flags,
    )
    if result.returncode:
        raise RuntimeError(f'无法限制 OneBot Token 文件权限：{result.stderr.strip()}')


def ensure_onebot_token() -> str:
    """Create a random token once; never overwrite an existing credential."""
    path = token_path()
    if path.exists():
        restrict_credential_acl(path.parent)
        restrict_credential_acl(path)
        return load_onebot_token()
    path.parent.mkdir(parents=True, exist_ok=True)
    restrict_credential_acl(path.parent)
    value = secrets.token_urlsafe(48)
    try:
        with path.open('x', encoding='ascii') as stream:
            stream.write(value + '\n')
        restrict_credential_acl(path)
    except FileExistsError:
        return load_onebot_token()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return value


def save_verified_onebot_token(value: str) -> None:
    """Persist a token only after a caller has verified it against the running NapCat."""
    if not isinstance(value, str) or len(value) < 24 or not value.isascii() or any(c in value for c in '\r\n'):
        raise ValueError('无效的 OneBot Token')
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    restrict_credential_acl(path.parent)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='ascii') as stream:
            stream.write(value + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        restrict_credential_acl(Path(temporary))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
