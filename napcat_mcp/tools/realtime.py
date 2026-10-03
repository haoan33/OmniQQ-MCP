"""
实时消息与事件感知工具集 (从后台 WebSocket 环形缓存获取实时收到的消息、通知和申请)
"""
from typing import Any, Optional
from . import registry
from ..client import NapCatClient


@registry.register()
async def get_recent_messages(
    client: NapCatClient,
    count: int = 20,
    chat_type: str = "all",
    target_id: Optional[int] = None,
    keyword: Optional[str] = None,
    include_self_sent: bool = False
) -> dict[str, Any]:
    """
    获取 MCP 服务后台通过 WebSocket 实时监听并缓存的近期 QQ 消息列表。
    支持按私聊/群聊、目标 QQ 号或群号、关键词过滤。
    :param count: 返回的最大消息条数，默认 20
    :param chat_type: 消息类型过滤: 'all' (全部), 'private' (仅私聊), 'group' (仅群聊)
    :param target_id: 按特定群号 (group_id) 或特定用户 QQ 号 (user_id) 过滤 (可选)
    :param keyword: 按消息文本或发送者昵称关键词过滤 (可选)
    :param include_self_sent: 是否包含自己发出的消息，默认 False
    """
    messages = client.buffer.get_recent_messages(
        count=count,
        chat_type=chat_type,
        target_id=target_id,
        keyword=keyword,
        include_self_sent=include_self_sent
    )
    return {
        "status": "ok",
        "ws_connected": client.is_ws_connected,
        "count": len(messages),
        "messages": messages
    }


@registry.register()
async def get_recent_notices_and_requests(
    client: NapCatClient,
    count: int = 20
) -> dict[str, Any]:
    """
    获取后台实时捕获的近期群通知事件 (如群文件上传、撤回、禁言、成员增减) 以及加好友/加群验证请求。
    返回的 flag 字段可直接传入 set_friend_add_request 或 set_group_add_request 进行审批。
    :param count: 最大返回条数，默认 20
    """
    data = client.buffer.get_recent_notices_and_requests(count=count)
    return {
        "status": "ok",
        "ws_connected": client.is_ws_connected,
        "notices": data["notices"],
        "requests": data["requests"]
    }


@registry.register()
async def clear_recent_messages_buffer(
    client: NapCatClient
) -> dict[str, Any]:
    """
    清空本地内存中的近期实时消息缓存池。
    """
    cleared = client.buffer.clear()
    return {
        "status": "ok",
        "cleared_count": cleared
    }
