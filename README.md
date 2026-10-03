# OmniQQ-MCP: Full-Featured QQ Bot Control & OneBot 11 Model Context Protocol (MCP) Server

[![MCP Compatible](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-blue)](https://modelcontextprotocol.io)
[![NapCatQQ](https://img.shields.io/badge/NapCatQQ-OneBot%2011-00BFFF)](https://github.com/NapNeko/NapCatQQ)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

**OmniQQ-MCP (`omniqq-mcp`)** 是一个基于 [NapNeko/NapCatQQ](https://github.com/NapNeko/NapCatQQ) 与 **OneBot 11 协议**打造的**全功能、自运维、零业务耦合的通用 QQ 控制与感知 MCP (Model Context Protocol) Server**。

通过本工具，你可以让 **Claude Desktop、Google Antigravity、Cursor、Windsurf、Cline、OpenAI Agents** 等任意支持 MCP 的 AI 智能体直接获得**操控 QQ 的双手与实时感知的眼睛**——涵盖私聊/群聊收发、合并转发、群管禁言踢人、群文件上传下载、图片 OCR、好友与资料管理、**二维码扫码登录、多 QQ 账号热切换**，以及 **一键环境自检与自动部署更新**。

---

## 🔍 核心检索关键词 (Keywords / Topics)

`omniqq` `omniqq-mcp` `mcp` `model-context-protocol` `mcp-server` `qq-bot` `napcat` `napcatqq` `onebot` `onebot11` `ntqq` `ai-agent` `qq-mcp` `claude-desktop` `cursor-mcp` `antigravity` `chatbot` `python-mcp`

---

## ✨ 功能特色与核心亮点 (Key Features)

### 1. 🦾 全量 144+ 项 NapCat 接口 100% 覆盖（74 个一级具名工具 + 万能透传）
- **74 个开箱即用的第一公民具名工具 (First-Class Tools)**：提供完备的 JSON Schema 类型校验与清晰参数说明，覆盖 99% 的高频操作；
- **万能底层接口透传 (`call_napcat_api`)**：支持直接调用 NapCat 官方引擎全部 **144+ 个标准与扩展 Action**（如群相册、群打卡、语音转文字 `fetch_ptt_text`、AI 声聊 `send_group_ai_record` 等），并内置 `list_supported_napcat_actions` 供 AI 自主查阅全部接口目录。

### 2. 📱 原生支持二维码扫码登录与多 QQ 账号秒级热切换
- **新账号扫码登录 (`login_new_qq_by_qrcode`)**：无需手动折腾配置文件，AI 一键拉起扫码沙箱、在屏幕自动弹出高清二维码图片 (`qrcode.png`)，用户手机扫码后**自动生成 OneBot 11 (3000/3001) 端口配置并转为后台常驻服务**；
- **多账号免扫码热切换 (`list_qq_accounts` / `switch_qq_account`)**：自动识别本地已缓存的所有历史登录 QQ 号，支持在多个 QQ 账号之间秒级热重启切换上线；
- **精准进程控制 (`start_napcat_service` / `stop_napcat_service` / `restart_napcat_service`)**：精准管理 `napcat_runtime` 下的沙箱进程，绝不误杀系统其他 Node.js 服务。

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
pip install aiohttp websockets psutil
```

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
- *“查看我已缓存的 QQ 账号，并切换到小号上线”*
- *“看看我最近收到了哪些 QQ 消息，给群 12345678 发一条通知”*

---

## 🗺️ 后续迭代路线图 (Roadmap)

NapCat-MCP 秉持 **“机制与策略彻底解耦”** 的架构设计理念：底层 MCP Server 保持纯净稳定的控制工具库，上层通过独立的事件流机制实现智能化消息应答。下一步迭代规划如下：

### 1. 阶段一：实时消息智能监听与多维筛选引擎 (v1.1)
- **多维规则过滤器 (Filter Pipeline)**：
  - 支持指定私聊/群聊白名单与黑名单，避免无差别响应；
  - 精准识别 `@当前机器人`、`@全体成员` 以及自定义关键词/正则规则触发；
  - 自动捕获群文件上传、好友申请、入群请求等通知事件。
- **连发防抖与多模态消息聚合器 (Debounce Window)**：
  - 设定 10~30 秒防抖保护窗口，自动将同一用户的连续多条短文本、表情包、图片与文件附件聚合为一个完整的结构化上下文，彻底杜绝碎片化 Token 浪费。

### 2. 阶段二：Agent 自动调度与闭环应答 (v1.2)
- **双向 Agent 驱动调度器 (Agent Dispatcher)**：
  - 支持通过 Antigravity CLI、标准 Webhook 或 OpenAI/Anthropic 兼容接口自动唤醒 AI 智能体；
  - AI 接收结构化上下文进行推理决策，随后直接调用本 MCP Server 的 `send_private_msg` / `send_group_msg` 原生工具完成闭环自动回复。
- **人机协同安全门禁 (Human-in-the-Loop)**：
  - 针对大群等敏感场景，支持“AI 拟定回复草案 -> 推送管理员手机审批 -> 确认后代发”，兼具全自动与高安全。

> 详见完整技术方案：[docs/ROADMAP.md](./docs/ROADMAP.md)

---

## 📝 版本更新日志 (Changelog)

### `v1.0.1` (2026-10-03)
- **新增 MCP 工具调用审计日志钩子 (`_record_mcp_activity`)**：每次工具执行自动向 `outputs/mcp_activity.jsonl`（或环境变量 `OMNIQQ_ACTIVITY_LOG` 指定路径）追加结构化 JSONL 审计日志，支持外部监控台实时回显 AI 发送/上传动作；
- **升级异步事件回调总线 (`MessageBuffer.register_event_hook`)**：原生兼容同步函数与 `async def` 异步协程回调，标准化事件结构新增 `target_id` 与 `raw_event`，支持上层监听服务直接复用 `NapCatClient._ws_loop()`；
- **新增终端多账号管理 CLI (`napcat_mcp.account_cli`)**：支持通过命令行交互管理多 QQ 账号与扫码登录。

> 完整历史记录请参阅 [CHANGELOG.md](./CHANGELOG.md)。

---

## 📄 开源协议 (License)

本项目基于 [MIT License](./LICENSE) 开源。


