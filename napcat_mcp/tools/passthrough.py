"""
NapCat 144+ 全量接口万能透传与接口清单查询工具
确保 NapCatQQ 官方全部标准与扩展 Action 100% 无死角可被 AI 调用。
"""
from typing import Any, Optional
from . import registry
from ..client import NapCatClient

# 从 NapCat 官方引擎提炼的完整 Action 分类清单 (140+ 接口)
NAPCAT_ALL_ACTIONS = {
    "messaging": [
        "send_private_msg", "send_group_msg", "send_msg", "delete_msg", "get_msg",
        "get_forward_msg", "send_forward_msg", "send_private_forward_msg", "send_group_forward_msg",
        "get_friend_msg_history", "get_group_msg_history",
        "upload_forward_msg", "send_like", "send_poke", "set_msg_emoji_like", "fetch_emoji_like",
        "get_emoji_likes", "mark_msg_as_read", "mark_private_msg_as_read", "mark_group_msg_as_read",
        "set_essence_msg", "delete_essence_msg", "get_essence_msg_list", "send_ark_share",
        "send_group_ark_share", "send_flash_msg", "send_packet", "send_qzone_msg", "delete_qzone_msg"
    ],
    "group_management": [
        "set_group_kick", "set_group_kick_members", "set_group_ban", "set_group_whole_ban",
        "set_group_anonymous_ban", "set_group_anonymous", "set_group_admin", "set_group_card",
        "set_group_name", "set_group_special_title", "set_group_leave", "set_group_portrait",
        "set_group_remark", "set_group_add_request", "set_group_add_option", "set_group_robot_add_option",
        "set_group_search", "set_group_sign", "send_group_sign", "set_group_todo",
        "set_group_member_invite_policy", "set_group_member_permissions",
        "set_group_new_member_history_visibility", "get_group_info", "get_group_info_ex",
        "get_group_detail_info", "get_group_list", "get_group_member_info", "get_group_member_list",
        "get_group_honor_info", "get_group_at_all_remain", "get_group_shut_list",
        "get_group_signed_list", "get_group_system_msg", "get_group_ignore_add_request",
        "get_group_ignored_notifies"
    ],
    "files_and_media": [
        "upload_private_file", "upload_group_file", "upload_file_stream", "delete_group_file",
        "delete_group_folder", "get_group_root_files", "get_group_files_by_folder",
        "get_group_file_url", "get_private_file_url", "get_group_file_system_info",
        "get_file", "get_image", "get_record", "ocr_image", "fetch_ptt_text",
        "download_file", "download_file_stream", "download_file_image_stream",
        "download_file_record_stream", "download_fileset", "get_fileset_id", "get_fileset_info",
        "get_flash_file_list", "get_flash_file_url", "send_online_file", "send_online_folder",
        "get_online_file_msg", "can_send_image", "can_send_record", "clean_cache",
        "clean_stream_temp_file", "get_qun_album_list", "get_group_album_media_list",
        "upload_image_to_qun_album", "del_group_album_media", "set_group_album_media_like"
    ],
    "friends_and_account": [
        "get_login_info", "get_friend_list", "get_friends_with_category",
        "get_unidirectional_friend_list", "delete_friend", "delete_unidirectional_friend",
        "set_friend_remark", "set_friend_add_request", "get_doubt_friends_add_request",
        "set_doubt_friends_add_request", "get_stranger_info", "get_profile_like",
        "set_qq_profile", "set_qq_avatar", "set_self_longnick", "set_online_status",
        "set_diy_online_status", "set_input_status", "fetch_custom_face",
        "fetch_custom_face_detail", "delete_custom_face", "set_custom_face_desc",
        "get_collection_list", "get_recent_contact"
    ],
    "ai_and_system": [
        "get_status", "get_version_info", "get_online_clients", "set_restart",
        "get_cookies", "get_csrf_token", "get_credentials", "get_clientkey",
        "get_rkey", "get_rkey_server", "get_robot_uin_range", "get_share_link",
        "get_mini_app_ark", "get_ai_characters", "get_ai_record", "send_group_ai_record",
        "get_guild_list", "get_guild_service_profile"
    ]
}


_LOCAL_MCP_PASSTHROUGH_TOOLS = {
    "start_napcat_service",
    "stop_napcat_service",
    "restart_napcat_service",
    "list_qq_accounts",
    "get_login_qrcode_image",
    "get_recent_notices_and_requests",
    "clear_recent_messages_buffer",
}

_ALL_KNOWN_ONEBOT_ACTIONS = {
    act for acts in NAPCAT_ALL_ACTIONS.values() for act in acts
}


@registry.register()
async def call_napcat_api(
    client: NapCatClient,
    action: str,
    params: Optional[dict] = None,
    timeout: float = 30.0
) -> dict[str, Any]:
    """
    调用 NapCatQQ 任意 OneBot 11 标准或扩展底层 Action（覆盖全部 144+ 项功能）的通用兜底透传工具。
    适用场景：仅当核心专用工具未覆盖所需功能时使用（例如查询历史记录 `get_friend_msg_history`/`get_group_msg_history`、群管禁言踢人 `set_group_ban`/`set_group_kick`、文件下载与 OCR `download_file`/`ocr_image`、好友与资料管理 `get_friend_list`/`set_qq_profile`、群相册或打卡等）。不适用与替代：严禁使用本工具替代已暴露的核心专用工具（发送私聊/群聊请用 `send_private_msg`/`send_group_msg`，撤回请用 `delete_msg`，上传文件请用 `upload_private_file`/`upload_group_file`）；不确定 `action` 精确名称时，请先调用 `list_supported_napcat_actions` 检索。
    参数约束与交互：`action` 必须为合法的 OneBot 11 / NapCat 端点名（不含前导斜杠 `/`）；`params` 为传给该端点的 JSON 键值字典，上传或下载大文件时建议将 `timeout` 调大至 120.0。
    行为、权限与副作用：操作性质完全取决于所调用的 `action`——`get_*`/`fetch_*` 为只读查询，而 `delete_*`/`set_group_kick`/`set_group_leave` 属于不可逆破坏性操作且要求当前账号已在线并具备相应群主/管理员权限；返回标准 OneBot 响应字典 `{"status": "ok"|"failed", "retcode": int, "data": ...}`，未知 action 或参数错误时返回非 0 `retcode` 并提示调用 `list_supported_napcat_actions`。
    :param action: 目标 OneBot 11 或 NapCat 扩展接口精确名称（可通过 `list_supported_napcat_actions` 查阅，如 'get_group_msg_history', 'set_group_ban', 'ocr_image'）
    :param params: 传递给该接口的请求参数字典（字段依具体 action 而定，无参数接口传空字典 {} 或省略）
    :param timeout: HTTP 请求最大等待超时秒数（常规接口默认 30.0，文件传输类接口建议 120.0）
    """
    action_clean = str(action or "").strip().lstrip("/")
    if action_clean in _LOCAL_MCP_PASSTHROUGH_TOOLS and action_clean in registry.tools_map:
        handler = registry.tools_map[action_clean]["handler"]
        return await handler(client=client, **(params or {}))

    res = await client.call_api(action=action_clean, params=params or {}, timeout=timeout)
    if isinstance(res, dict) and (res.get("status") == "failed" or res.get("retcode", 0) not in (0, None)):
        hint = "可先调用 list_supported_napcat_actions 查询接口名。"
        msg_text = f"{res.get('message', '')} {res.get('wording', '')} {res.get('error', '')}"
        is_unknown_action = (
            action_clean not in _ALL_KNOWN_ONEBOT_ACTIONS
            or "不支持" in msg_text
            or "not found" in msg_text.lower()
            or "unknown" in msg_text.lower()
            or res.get("retcode") in (404, 1404)
        )
        if is_unknown_action:
            res = dict(res)
            res.setdefault("advice", f"未知或不支持的接口 '{action_clean}'，{hint}")
            for field in ("message", "wording", "error"):
                if isinstance(res.get(field), str) and "list_supported_napcat_actions" not in res[field]:
                    res[field] = f"{res[field]}（{hint}）"
        else:
            res = dict(res)
            res.setdefault("advice", hint)
    return res


@registry.register()
async def list_supported_napcat_actions(
    client: NapCatClient,
    category: str = "all"
) -> dict[str, Any]:
    """
    查询 NapCatQQ 引擎支持的全部 144+ 个底层 OneBot 11 与扩展 Action 名称分类目录。
    适用场景：在准备调用 `call_napcat_api` 但不确定目标功能的精确 `action` 英文名称时，先调用本工具按分类查阅。不适用与替代：若所需操作已有直接对应的核心具名工具（如 `send_private_msg`、`send_group_msg`、`get_group_list` 等），则无需查阅本目录；本工具仅返回接口名称清单，真正执行接口调用请使用 `call_napcat_api`。
    参数约束与交互：`category` 可按功能域筛选子集（如群管选 `'group_management'`，媒体选 `'files_and_media'`，系统与 AI 声聊选 `'ai_and_system'`），若传入未识别的分类名则自动回退返回 `'all'` 全量字典。
    行为与返回：纯本地静态目录只读查询（无网络请求、无需登录在线、零副作用）；当 `category='all'` 时返回 `total_count` 与按分类组织的 `categories` 字典，指定单一分类时返回 `count` 与 `actions` 字符串数组。
    :param category: 接口分类筛选枚举: 'all'（全部 5 大分类）、'messaging'（消息与互动）、'group_management'（群组管理与查询）、'files_and_media'（文件、相册与语音OCR）、'friends_and_account'（好友与个人资料）、'ai_and_system'（系统状态、凭证与AI声聊），默认 'all'
    """
    if category != "all" and category in NAPCAT_ALL_ACTIONS:
        return {
            "category": category,
            "count": len(NAPCAT_ALL_ACTIONS[category]),
            "actions": NAPCAT_ALL_ACTIONS[category]
        }
    total = sum(len(v) for v in NAPCAT_ALL_ACTIONS.values())
    return {
        "category": "all",
        "total_count": total,
        "categories": NAPCAT_ALL_ACTIONS
    }
