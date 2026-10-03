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


@registry.register()
async def call_napcat_api(
    client: NapCatClient,
    action: str,
    params: Optional[dict] = None,
    timeout: float = 30.0
) -> dict[str, Any]:
    """
    万能底层接口透传工具：直接调用 NapCatQQ 支持的任意 OneBot 11 标准或扩展 Action (覆盖全部 144+ 项功能)。
    当高层具名工具未涵盖某个特定冷门接口 (如群相册、群签到、语音转文字 fetch_ptt_text、AI声聊 send_group_ai_record、清理缓存 clean_cache 等) 时，使用此工具直接调用。
    :param action: NapCat 接口名称 (例如 'send_group_sign', 'fetch_ptt_text', 'get_cookies' 等)
    :param params: 传递给该接口的 JSON 参数字典 (例如 {"group_id": 123456})
    :param timeout: 请求超时秒数，默认 30.0
    """
    return await client.call_api(action=action, params=params or {}, timeout=timeout)


@registry.register()
async def list_supported_napcat_actions(
    client: NapCatClient,
    category: str = "all"
) -> dict[str, Any]:
    """
    列出 NapCatQQ 官方引擎支持的全部 140+ 个底层 Action 名称目录，方便在使用 call_napcat_api 前查阅精确的接口名。
    :param category: 分类过滤: 'all' | 'messaging' | 'group_management' | 'files_and_media' | 'friends_and_account' | 'ai_and_system'
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
