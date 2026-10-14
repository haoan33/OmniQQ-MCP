# OmniQQ-MCP v1.1.0 compatibility and reliability

## Compatibility

| Component | Supported range or behavior |
| --- | --- |
| Python | 3.10 or newer; Windows CI checks 3.10, 3.11 and 3.12. |
| websockets | `>=14,<17`; uses `additional_headers`. |
| MCP stdio | JSON-RPC 2.0, protocol version `2024-11-05`; newer requests negotiate to this implemented version. |
| OneBot | OneBot 11 HTTP and WebSocket; authenticated remote endpoints can be configured with environment variables. |
| Local runtime | Windows NapCat Node Shell; deployment, QR login and process management require Windows. |

Automated tests use mocks and temporary local endpoints. They do not establish real QQ login, live message delivery, or compatibility with every MCP client and NapCat release. Actual Action support depends on the installed runtime; the static Action catalog is not a live capability probe.

## Request and event behavior

Stdio permits eight active requests and up to 64 pending requests. Read-only requests can be cancelled using `notifications/cancelled`. Writes and lifecycle operations finish and return their actual result; cancellation cannot undo a remote side effect.

Recent messages, notices and requests are held in memory per account `self_id`. Switching accounts selects the corresponding cache. Events without `self_id` are ignored once an account is selected. Caches do not persist across process restarts.

Event hooks execute in order through a queue of at most 200 records. Synchronous hooks run in a worker thread. Backpressure pauses reads when the queue is full; hooks are not durable across process crashes.

## User data and authentication

New installations use `%LOCALAPPDATA%\OmniQQ-MCP` on Windows, or `~/.local/share/OmniQQ-MCP` otherwise. Existing checkout runtimes continue to use `napcat_runtime`. A legacy `current_account.txt` is read until the next account selection writes user data.

Override locations with `OMNIQQ_RUNTIME_DIR`, `OMNIQQ_CURRENT_ACCOUNT_FILE`, `OMNIQQ_ONEBOT_TOKEN_FILE`, `OMNIQQ_LOG_FILE` and `OMNIQQ_ACTIVITY_LOG`. Token files and managed account configuration use restrictive Windows ACLs. HTTP and WebSocket use the same Token. On an HTTP 403, a candidate from managed runtime configuration is adopted only after a successful read-only login-info probe.

Set `NAPCAT_HTTP_URL` and `NAPCAT_WS_URL` together for a remote OneBot deployment, and keep the private Token file consistent with server authentication. Remote endpoints do not trigger local runtime deployment or process management.

Audit records omit chat text, file contents, full arguments and credentials, but retain numeric targets and message identifiers for diagnostics. Keep logs private. Application logs rotate at 5 MB with three backups; activity audits rotate at 10 MB with three backups.

## Upgrade and rollback

Deployment extracts into staging and checks for `node.exe` and `index.js`. It backs up an existing runtime before copying, writes managed OneBot configuration and validates `node.exe --version` and `node.exe --check index.js`. Copy, configuration or validation failures return `failed` and restore the backup. Successful responses expose the backup directory when available.

These checks do not prove QQ login. After upgrading, start the runtime and check `get_login_info`. Updating a running instance stops it and does not automatically restart it. Restart MCP host processes after installing this release.
