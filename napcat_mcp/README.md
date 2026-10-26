# OmniQQ-MCP: Full-Featured QQ Bot Control & OneBot 11 Model Context Protocol (MCP) Server

[![MCP Compatible](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-blue)](https://modelcontextprotocol.io)
[![NapCatQQ](https://img.shields.io/badge/NapCatQQ-OneBot%2011-00BFFF)](https://github.com/NapNeko/NapCatQQ)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

**OmniQQ-MCP (`omniqq-mcp`)** 是基于 [NapNeko/NapCatQQ](https://github.com/NapNeko/NapCatQQ) 与 **OneBot 11 协议**的 QQ 控制与事件读取 MCP Server。本版本提供 74 项具名工具与 OneBot Action 透传，新增账号隔离缓存、并发请求、只读取消和可靠性修复。

通过本工具，你可以让 **Claude Desktop、Google Antigravity、Cursor、Windsurf、Cline、OpenAI Agents** 等任意支持 MCP 的 AI 智能体直接获得**操控 QQ 的双手与实时感知的眼睛**——涵盖私聊/群聊收发、合并转发、群管禁言踢人、群文件上传下载、图片 OCR、好友与资料管理、**二维码扫码登录、多 QQ 账号热切换**，以及 **一键环境自检与自动部署更新**。

---

## 🔍 核心检索关键词 (Keywords / Topics)

`omniqq` `omniqq-mcp` `mcp` `model-context-protocol` `mcp-server` `qq-bot` `napcat` `napcatqq` `onebot` `onebot11` `ntqq` `ai-agent` `qq-mcp` `claude-desktop` `cursor-mcp` `antigravity` `chatbot` `python-mcp`

---

## ✨ 功能特色与核心亮点 (Key Features)

### 1. 🦾 全量 144+ 项 NapCat 接口 100% 覆盖（14 个核心正交工具 + 74 项具名工具 + 万能透传）
- **默认暴露 14 个精选正交核心工具 (OMNIQQ_TOOL_PROFILE=core)**：严格遵循 MCP 最佳实践区间（3~15 个工具），避免撑爆 LLM 上下文窗口，每个工具均附带完整 MCP nnotations、outputSchema、前置权限说明与替代工具路由指引；
- **74 个具名工具全量兼容 (OMNIQQ_TOOL_PROFILE=full)**：全部 74 个细分具名工具始终支持通过 	ools/call 直接按名调用，或通过设置环境变量 OMNIQQ_TOOL_PROFILE=full 在 	ools/list 中全量列出；
- **万能底层接口透传 (`call_napcat_api`)**：支持直接调用 NapCat 官方引擎全部 **144+ 个标准与扩展 Action**（如群相册、群打卡、语音转文字 `fetch_ptt_text`、AI 声聊 `send_group_ai_record` 等），并内置 `list_supported_napcat_actions` 供 AI 自主查阅全部接口目录。

### 2. 📱 原生支持二维码扫码登录与多 QQ 账号切换
- **新账号扫码登录 (`login_new_qq_by_qrcode`)**：无需手动折腾配置文件，AI 一键拉起扫码沙箱、在屏幕自动弹出高清二维码图片 (`qrcode.png`)，用户手机扫码后**自动生成 OneBot 11 (3000/3001) 端口配置并转为后台常驻服务**；
- **多账号免扫码热切换 (`list_qq_accounts` / `switch_qq_account`)**：自动识别本地已缓存的所有历史登录 QQ 号，支持在多个 QQ 账号之间重启切换上线（耗时取决于登录状态）；
- **精准进程控制 (`start_napcat_service` / `stop_napcat_service` / `restart_napcat_service`)**：精准管理 `napcat_runtime` 下的沙箱进程，按可执行文件与入口路径匹配托管进程。

### 3. 🛠️ 环境智能自检、版本对比与一键安全自动部署 (`Self-Deploying & Auto-Healing`)
- **环境诊断 (`check_napcat_environment`)**：自动检测本地 NapCat 运行时完整性、3000/3001 端口状态，并实时连接 GitHub Release API 对比官方最新版本；
- **带安全确认锁的一键部署与升级 (`deploy_or_update_napcat`)**：内建 `confirmed=False` 强制确认门禁，在向用户展示部署路径与版本信息并获得明确授权后，自动下载/解压官方 Release 包并完成初始化；
- **混合自愈启动 (`Auto-Heal`)**：调用任意 QQ 工具时，若检测到后台 NapCat 未启动，自动以最小化无焦点窗口静默拉起服务并完成握手。

### 4. ⚡ 实时 WebSocket 消息环形缓存 + 机制与策略彻底分离
- **实时收信感知 (`get_recent_messages` / `get_recent_notices_and_requests`)**：后台自动维护 WebSocket 长连接与环形消息队列（默认缓存最近 200 条消息与群通知/好友申请），自动净化 CQ 码与富媒体段，支持按群号、QQ 号、关键词秒级检索；
- **机制与策略分离 (`Event Hook` 扩展总线)**：MCP Server 保持 100% 纯净通用，不写死任何特定业务白名单；同时在 `MessageBuffer.register_event_hook(callback)` 预留事件回调钩子，并支持多路 WebSocket 并行监听，方便开发者后期按需挂载自定义筛选与 Agent 唤醒脚本。

---

## 🧰 74 项工具全景矩阵 (Tools Overview)

| 模块分类 | 工具数量 | 代表性工具列表 |
| :--- | :---: | :--- |
| **1. 环境运维、登录与多账号** | 9 | `check_napcat_environment`, `deploy_or_update_napcat`, `list_qq_accounts`, `switch_qq_account`, `login_new_qq_by_qrcode`, `get_login_qrcode_image`, `start_napcat_service`, `stop_napcat_service`, `restart_napcat_service` |
| **2. 消息收发与社交互动** | 15 | `send_private_msg`, `send_group_msg`, `send_msg`, `delete_msg`, `get_msg`, `get_forward_msg`, `send_private_forward_msg`, `send_group_forward_msg`, `send_like`, `send_poke`, `set_msg_emoji_like`, `mark_msg_as_read`, `set_essence_msg`, `delete_essence_msg`, `get_essence_msg_list` |
| **3. 群组管理与治理控制** | 14 | `set_group_kick`, `set_group_ban`, `set_group_whole_ban`, `set_group_admin`, `set_group_card`, `set_group_name`, `set_group_special_title`, `set_group_leave`, `set_group_add_request`, `set_group_todo`, `set_group_portrait`, `get_group_at_all_remain`, `get_group_shut_list`, `get_group_system_msg` |
| **4. 文件与富媒体操作** | 11 | `upload_private_file`, `upload_group_file`, `delete_group_file`, `delete_group_folder`, `get_group_root_files`, `get_group_files_by_folder`, `get_group_file_url`, `get_private_file_url`, `get_group_file_system_info`, `ocr_image`, `download_file` |
| **5. 好友关系与账号设置** | 10 | `get_friend_list`, `get_friends_with_category`, `get_stranger_info`, `delete_friend`, `set_friend_remark`, `set_friend_add_request`, `set_qq_profile`, `set_qq_avatar`, `set_self_longnick`, `set_online_status` |
| **6. 信息与历史记录查询** | 10 | `get_login_info`, `get_group_list`, `get_group_info`, `get_group_member_info`, `get_group_member_list`, `get_group_honor_info`, `get_friend_msg_history`, `get_group_msg_history`, `get_recent_contact`, `get_napcat_status` |
| **7. 实时消息与通知感知** | 3 | `get_recent_messages`, `get_recent_notices_and_requests`, `clear_recent_messages_buffer` |
| **8. 144+ 接口万能透传** | 2 | `call_napcat_api`, `list_supported_napcat_actions` |

---

## 🚀 快速开始 (Quick Start)

### 1. 安装依赖

本服务采用原生异步 JSON-RPC 2.0 实现，依赖极度精简：

```bash
python -m pip install -r requirements.txt
```

依赖范围见 `requirements.txt`，WebSocket 使用 `websockets>=14,<17`。可在本目录构建 wheel 或执行 `pip install .`，入口为 `omniqq-mcp`。

本地 NapCat 托管、扫码、进程管理与自动部署仅支持 Windows；连接外部 OneBot URL 时不检查或启动本地端口。Python、WebSocket、MCP 和 NapCat 的版本矩阵，以及升级备份和回滚方式，见 [可靠性审查](docs/RELIABILITY_REVIEW.md)。

### 2. 在 MCP 客户端中挂载 (`mcp_config.json`)

在 **Antigravity (`~/.gemini/config/mcp_config.json`)**、**Claude Desktop** 或 **Cursor** 中添加：

```json
{
  "mcpServers": {
    "omniqq-mcp": {
      "command": "python",
      "args": [
        "-u",
        "/path/to/napcat_mcp/run_mcp.py"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

### 3. 首次使用自然语言交互示例

挂载完成后，直接对你的 AI 助手说：
- *“检查一下我的 NapCat 环境状态，如果没部署帮我自动部署一下”*
- *“帮我启动二维码扫码登录一个新 QQ 账号”*
- *“查看我已缓存的 QQ 账号，并切换到另一个账号上线”*
- *“看看我最近收到了哪些 QQ 消息，给群 12345678 发一条通知”*

---

## v1.1.0 更新（2026-10-14）

- **账号隔离缓存**：消息、通知和申请按 `self_id` 保存在内存中，切换账号不会混用收件记录。
- **并发与取消**：stdio 同时处理请求，慢请求不阻塞查询；只读请求支持 `notifications/cancelled`，写操作继续完成并报告实际结果。
- **有界事件钩子**：事件按序投递，慢同步钩子在线程中执行，队列背压保护 WebSocket 读取。
- **OneBot 鉴权**：HTTP 与 WebSocket 复用用户数据目录中的随机 Token；403 恢复先用只读探测验证候选凭据。
- **可靠性修复**：外部端点不启动本地运行时；账号配置写入失败可见；进程清理匹配目标可执行文件和入口；升级失败回滚备份。
- **结构化消息与校验**：保留原始消息段，补齐历史查询 Action；校验必填项和参数类型，畸形 JSON-RPC 不终止服务。
- **元数据审计**：日志不保留消息正文、文件内容、完整调用参数或凭据，支持轮转和可配置路径。

更新全部 MCP 宿主使用的源码或安装包后，重启 MCP 进程以加载新版本。新安装的运行时、日志、账号选择和 Token 默认位于 `%LOCALAPPDATA%\OmniQQ-MCP`；已有 `napcat_runtime` 会继续使用。

### v1.2.1 (2026-10-26)
- **启动前自动清理冲突 `QQ.exe` 进程**：每次启动 NapCat 服务前自动检测并结束独立 `QQ.exe` 进程，避免同账号互踢与数据库锁冲突。
- **需登录时自动导出二维码至桌面**：检测到需要扫码登录时，自动将 `qrcode.png` 复制到桌面（`qq_login_qrcode.png`）并提示用户打开扫描。
- **纯本地工具入核与未知接口引导**：将 6 个无 OneBot HTTP 等价接口的纯本地工具纳入 `core` 模式（共 20 个工具），并为 `call_napcat_api` 未知接口报错补充 `list_supported_napcat_actions` 指引。

### v1.2.0 (2026-10-25)
- **核心工具精简与全量兼容 (`OMNIQQ_TOOL_PROFILE`)**：默认 `tools/list` 暴露 19 个核心与本地工具（14 个高频核心工具 + 5 个无 OneBot 等价接口的纯本地工具），`tools/call` 仍支持直接调用全部 74 项具名工具，设置 `OMNIQQ_TOOL_PROFILE=full` 可全量列出。
- **标准注解与返回结构**：为全部工具补齐 MCP `annotations` 与 `outputSchema`，剥离主描述中重复的 `:param` 行并补全使用场景、权限要求与副作用说明。

完整历史见 [CHANGELOG.md](./CHANGELOG.md)，兼容性和回滚说明见 [可靠性说明](docs/RELIABILITY_REVIEW.md)。

## 安装与连接

源码根目录运行 `python -m pip install .`，或安装 Release 附件中的 wheel。安装后可直接使用 `omniqq-mcp` 命令作为 MCP stdio 入口。

连接已有 OneBot 服务时，设置 `NAPCAT_HTTP_URL` 和 `NAPCAT_WS_URL`；鉴权 Token 从私有文件读取，`OMNIQQ_ONEBOT_TOKEN_FILE` 可覆盖默认位置。请保持 Token 文件与 OneBot 服务端鉴权配置一致。

不要上传 Token、账号选择文件、NapCat 登录凭据、二维码、日志或运行时目录。审计仍包含运行时的目标账号和消息 ID，请保存在本地私有目录。

## 后续计划

继续完善 MCP 客户端兼容性、依赖版本验证、Action 目录与实际 NapCat 版本的对应关系。通用工具与事件钩子的路线图见 [docs/ROADMAP.md](docs/ROADMAP.md)。

---

## 📄 开源协议 (License)

本项目基于 [MIT License](./LICENSE) 开源。


