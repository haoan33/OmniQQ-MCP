# Changelog

## [1.2.0] - 2026-10-25

### Added
- Standard MCP Tool `annotations` (`title`, `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) and `outputSchema` across all registered tools.
- Dual tool-profile support (`OMNIQQ_TOOL_PROFILE=core` vs `full`): default `tools/list` exposes 19 orthogonal core & local tools (14 high-frequency core tools + 5 pure local runtime/buffer tools without OneBot HTTP equivalents), while `tools/call` and `OMNIQQ_TOOL_PROFILE=full` retain full access to all 74 named tools.

### Changed
- Stripped duplicate `:param` lines from tool primary `description` strings so parameter definitions live cleanly in `inputSchema` while descriptions focus on parameter constraints, interactions, and usage boundaries.
- Expanded all 8 tool modules with explicit when-to-use / when-not-to-use guidance, sibling tool disambiguation, permission prerequisites, and side-effect / reversibility disclosures.

## [1.1.0] - 2026-10-14

### Added
- Account-isolated in-memory message, notice and request caches, selected by QQ `self_id`.
- Concurrent MCP stdio dispatch (eight active requests, 64 pending requests) and cancellation of read-only requests; writes finish and report their actual outcome.
- Ordered event hooks with a bounded 200-record queue and worker-thread handling of synchronous callbacks.
- Shared HTTP/WebSocket OneBot Token stored outside the project, restrictive credential ACLs on Windows, and read-only verification before recovering a 403 with a candidate Token.
- Input/schema validation, structured message segment support, and a declared MCP protocol version of `2024-11-05`.
- Windows CI covering Python 3.10–3.12, regression tests, lint, focused type checks, dependency audit and package smoke tests.

### Fixed
- External OneBot endpoints bypass local lifecycle checks; local deployment and process tools remain Windows-only.
- Failed account/configuration writes are reported, and process cleanup checks the exact Node executable and NapCat entry.
- Runtime upgrades stage and validate files, retain backups and restore the previous runtime on copy, configuration or health-check failure.
- Invalid JSON and malformed JSON-RPC requests return errors without terminating stdio handling.
- The passthrough Action catalog now includes both named history tools. Actual Action support still depends on the installed NapCat version.

### Changed
- New installations keep runtime, account selection, Token and logs in user data; existing checkout runtimes remain supported.
- Activity audits record metadata and outcomes only, omitting message bodies, full arguments, file contents and credentials. Audit and application logs rotate.
- Dependencies declare `websockets>=14,<17`. Restart MCP host processes after upgrading.

## [1.0.1] - 2026-10-03

- Added tool activity audit hooks, synchronous/asynchronous event callbacks and the account-management CLI.

## [1.0.0] - 2026-10-03

- Initial release: 74 named tools, OneBot Action passthrough, QR login, account switching, runtime deployment and WebSocket event buffering.
