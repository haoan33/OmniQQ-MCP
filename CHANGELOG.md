# Changelog

All notable changes to **OmniQQ-MCP** will be documented in this file.

## [1.0.1] - 2026-10-03

### ✨ Added (新增特性)
- **MCP 工具调用审计日志钩子 (`_record_mcp_activity`)**：
  - 在 `NapCatMCPServer._handle_tool_call` 中新增结构化 JSONL 活动审计钩子，每次工具调用自动记录时间戳 (`ts`)、工具名 (`tool`)、调用参数 (`args`) 与执行状态 (`ok` / `error`)；
  - 默认输出至 `outputs/mcp_activity.jsonl`，支持通过环境变量 `OMNIQQ_ACTIVITY_LOG` 自定义日志文件路径，便于外部宿主监控服务实时回显 AI 操作状态。
- **异步协程事件钩子支持 (`Async Event Hook`)**：
  - `MessageBuffer.register_event_hook(callback)` 现已原生支持同步函数与异步协程 (`async def`) 回调函数；
  - `MessageBuffer.push_event` 标准化记录新增 `target_id`、`message` 与完整原始事件 `raw_event` 字段，方便上层伴生监听服务直接复用 `NapCatClient._ws_loop()` 实现单链路事件分发。
- **独立终端账号管理 CLI (`napcat_mcp.account_cli`)**：
  - 新增 `python -m napcat_mcp.account_cli` 命令行交互模块，支持在终端一键查看已缓存账号、切换默认登录 QQ 或发起新账号二维码扫码登录；
  - `napcat_mcp.config` 新增 `kill_napcat_processes()` 标准导出接口。

---

## [1.0.0] - 2026-10-03

### 🎉 Initial Release (首发版本)
- **74 项一级具名 MCP 工具 + 144+ 原生接口万能透传 (`call_napcat_api`)**：全面覆盖消息收发、合并转发、群管控制、群文件上传下载、OCR、好友与资料管理、历史记录查询；
- **二维码扫码登录与多账号秒级热切换**：支持 `login_new_qq_by_qrcode`、`list_qq_accounts`、`switch_qq_account`；
- **环境智能自检与带确认门禁的一键部署 (`check_napcat_environment` / `deploy_or_update_napcat`)**；
- **实时 WebSocket 环形消息缓存池 (`MessageBuffer`)**。
