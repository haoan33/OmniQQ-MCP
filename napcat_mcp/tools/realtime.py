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
    读取 MCP 服务后台通过 WebSocket 实时监听并保存在本地环形内存缓存池（上限 200 条，按登录账号隔离）中的近期 QQ 消息列表。
    适用场景：快速轮询或按条件检索服务运行期间实时收到的最新私聊与群聊消息。不适用与替代：若需查询 MCP 启动之前的历史聊天记录或向更早页码翻页，请通过 `call_napcat_api` 调用 `get_friend_msg_history` 或 `get_group_msg_history`；若需查看加群/加好友审批请求或群撤回通知，请调用 `get_recent_notices_and_requests`。
    参数约束与交互：当指定 `target_id` 时，若 `chat_type='group'` 则按群号过滤，若 `chat_type='private'` 则按发送者 QQ 号过滤，若 `chat_type='all'` 则同时匹配群号或 QQ 号；`keyword` 对净化后的消息文本 `clean_text` 与发送者昵称做大小写不敏感子串匹配。
    行为与返回：纯内存只读操作（零外部网络延迟，不修改缓存状态）；返回 `ws_connected`、`count` 及 `messages` 数组（每项含 `message_id`, `chat_type`, `user_id`, `group_id`, `sender_name`, `clean_text`, `time`）。
    :param count: 返回的最大最新消息条数（范围 1~200，默认 20）
    :param chat_type: 会话范围过滤枚举: 'all'（全部消息）、'private'（仅私聊）、'group'（仅群聊），默认 'all'
    :param target_id: 限定特定群号（group_id）或特定好友 QQ 号（user_id）的正整数 ID；留空不过滤
    :param keyword: 按消息正文或发送者昵称/群名片包含的子串关键词过滤；留空不过滤
    :param include_self_sent: 为 True 时包含当前登录账号自己发出的消息，为 False 时仅返回他人发来的消息，默认 False
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
    从本地 WebSocket 环形缓存池中读取近期实时捕获的群通知事件（群文件上传、消息撤回、禁言、成员变动）及加好友/加群验证请求。
    适用场景：监听群动态或获取验证请求的 `flag` 标识以便通过 `call_napcat_api` 调用 `set_friend_add_request` / `set_group_add_request` 审批。不适用与替代：若需读取普通私聊或群聊文字/富媒体消息，请改用 `get_recent_messages`。
    行为与返回：纯本地内存只读操作；返回 `ws_connected`、`notices` 数组与 `requests` 数组。
    :param count: 通知与请求各自返回的最大条数（范围 1~200，默认 20）
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
    清空当前登录账号在本地 MCP 内存环形缓冲区中暂存的所有实时消息、群通知与请求事件记录。
    适用场景：在完成一批消息处理或测试重置时，主动清空本地内存缓冲以避免重复读取旧事件。不适用与替代：本工具仅清空本地内存缓存，不会撤回 QQ 聊天消息（撤回请用 `delete_msg`）也不会清除 QQ 客户端未读红点（标记已读请通过 `call_napcat_api` 调用 `mark_msg_as_read`）。
    行为与副作用：本地破坏性且不可逆的内存清空操作（不影响 QQ 服务器端历史记录，后续可通过 `call_napcat_api` 调用 `get_friend_msg_history` / `get_group_msg_history` 重新从服务器拉取）；返回被清除的记录总数 `cleared_count`。
    """
    cleared = client.buffer.clear()
    return {
        "status": "ok",
        "cleared_count": cleared
    }
