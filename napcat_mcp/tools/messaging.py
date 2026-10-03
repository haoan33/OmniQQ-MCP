"""
消息收发、撤回、合并转发、互动与群精华控制工具集 (依据 NapCat OneBot 11 官方规范)
"""
from typing import Any, Optional
from . import registry
from ..client import NapCatClient


@registry.register()
async def send_private_msg(
    client: NapCatClient,
    user_id: int,
    message: str,
    auto_escape: bool = False
) -> dict[str, Any]:
    """
    向指定好友或用户发送私聊消息 (OneBot 11: send_private_msg)。
    支持纯文本、CQ 码 (如 [CQ:image,file=xxx] / [CQ:face,id=14])。
    :param user_id: 对方 QQ 号
    :param message: 要发送的消息内容 (文本或 CQ 码字符串)
    :param auto_escape: 是否作为纯文本发送 (不解析 CQ 码)，默认 False
    """
    return await client.call_api("send_private_msg", {
        "user_id": int(user_id),
        "message": message,
        "auto_escape": bool(auto_escape)
    })


@registry.register()
async def send_group_msg(
    client: NapCatClient,
    group_id: int,
    message: str,
    auto_escape: bool = False
) -> dict[str, Any]:
    """
    向指定 QQ 群发送群聊消息 (OneBot 11: send_group_msg)。
    支持纯文本、@全体成员 ([CQ:at,qq=all] 或直接 @全体成员)、@指定成员 ([CQ:at,qq=123456]) 及图片/表情等 CQ 码。
    :param group_id: 目标 QQ 群号
    :param message: 要发送的群消息内容
    :param auto_escape: 是否作为纯文本发送 (不解析 CQ 码)，默认 False
    """
    return await client.call_api("send_group_msg", {
        "group_id": int(group_id),
        "message": message,
        "auto_escape": bool(auto_escape)
    })


@registry.register()
async def send_msg(
    client: NapCatClient,
    message_type: str,
    target_id: int,
    message: str,
    auto_escape: bool = False
) -> dict[str, Any]:
    """
    通用消息发送接口 (OneBot 11: send_msg)，可根据 message_type 发送私聊或群聊消息。
    :param message_type: 消息类型，'private' (私聊) 或 'group' (群聊)
    :param target_id: 当 message_type='private' 时为对方 QQ 号；为 'group' 时为目标群号
    :param message: 要发送的消息文本或 CQ 码
    :param auto_escape: 是否不解析 CQ 码，默认 False
    """
    params: dict[str, Any] = {
        "message_type": message_type,
        "message": message,
        "auto_escape": bool(auto_escape)
    }
    if message_type == "group":
        params["group_id"] = int(target_id)
    else:
        params["user_id"] = int(target_id)
    return await client.call_api("send_msg", params)


@registry.register()
async def delete_msg(
    client: NapCatClient,
    message_id: int
) -> dict[str, Any]:
    """
    撤回指定消息 (OneBot 11: delete_msg)。可撤回自己发出的消息，或作为群管理员撤回群成员消息。
    :param message_id: 目标消息 ID
    """
    return await client.call_api("delete_msg", {"message_id": int(message_id)})


@registry.register()
async def get_msg(
    client: NapCatClient,
    message_id: int
) -> dict[str, Any]:
    """
    根据 message_id 获取单条消息的详细信息，包括发送者、发送时间、原始消息段等 (OneBot 11: get_msg)。
    :param message_id: 目标消息 ID
    """
    return await client.call_api("get_msg", {"message_id": int(message_id)})


@registry.register()
async def get_forward_msg(
    client: NapCatClient,
    message_id: str
) -> dict[str, Any]:
    """
    获取合并转发消息的具体内容节点列表 (OneBot 11: get_forward_msg)。
    :param message_id: 合并转发 ID (id / message_id)
    """
    return await client.call_api("get_forward_msg", {"message_id": str(message_id), "id": str(message_id)})


@registry.register()
async def send_private_forward_msg(
    client: NapCatClient,
    user_id: int,
    messages: list
) -> dict[str, Any]:
    """
    向指定好友发送合并转发消息 (NapCat OneBot 11: send_private_forward_msg)。
    节点格式示例: [{"type": "node", "data": {"name": "发送者昵称", "uin": "10001", "content": "消息内容"}}]
    :param user_id: 接收方好友 QQ 号
    :param messages: 合并转发消息节点数组 (list of node dicts)
    """
    return await client.call_api("send_private_forward_msg", {
        "user_id": int(user_id),
        "messages": messages
    })


@registry.register()
async def send_group_forward_msg(
    client: NapCatClient,
    group_id: int,
    messages: list
) -> dict[str, Any]:
    """
    向指定群聊发送合并转发消息 (NapCat OneBot 11: send_group_forward_msg)。
    节点格式示例: [{"type": "node", "data": {"name": "发送者昵称", "uin": "10001", "content": "消息内容"}}]
    :param group_id: 目标 QQ 群号
    :param messages: 合并转发消息节点数组 (list of node dicts)
    """
    return await client.call_api("send_group_forward_msg", {
        "group_id": int(group_id),
        "messages": messages
    })


@registry.register()
async def send_like(
    client: NapCatClient,
    user_id: int,
    times: int = 10
) -> dict[str, Any]:
    """
    向指定好友资料卡点赞 (OneBot 11: send_like)。
    :param user_id: 对方 QQ 号
    :param times: 点赞次数 (1~10，默认 10)
    """
    return await client.call_api("send_like", {
        "user_id": int(user_id),
        "times": int(times)
    })


@registry.register()
async def send_poke(
    client: NapCatClient,
    user_id: int,
    group_id: Optional[int] = None
) -> dict[str, Any]:
    """
    发送“戳一戳”互动提醒 (NapCat 扩展接口: send_poke)。
    若提供 group_id 则在群内戳指定成员；若不提供则发送私聊戳一戳。
    :param user_id: 要戳的目标 QQ 号
    :param group_id: 所在群号 (可选，不填则为私聊戳一戳)
    """
    params: dict[str, Any] = {"user_id": int(user_id)}
    if group_id is not None:
        params["group_id"] = int(group_id)
    return await client.call_api("send_poke", params)


@registry.register()
async def set_msg_emoji_like(
    client: NapCatClient,
    message_id: int,
    emoji_id: int,
    set_like: bool = True
) -> dict[str, Any]:
    """
    对指定消息添加或取消表情回应 / 贴表情 (NapCat 扩展接口: set_msg_emoji_like)。
    :param message_id: 目标消息 ID
    :param emoji_id: 表情 ID (如 128077 表示👍，或 QQ 表情 ID)
    :param set_like: True 为添加贴表情，False 为取消
    """
    return await client.call_api("set_msg_emoji_like", {
        "message_id": int(message_id),
        "emoji_id": str(emoji_id),
        "set": bool(set_like)
    })


@registry.register()
async def mark_msg_as_read(
    client: NapCatClient,
    message_id: Optional[int] = None,
    user_id: Optional[int] = None,
    group_id: Optional[int] = None
) -> dict[str, Any]:
    """
    将指定消息、私聊会话或群聊会话标记为已读 (NapCat 扩展接口: mark_msg_as_read / mark_private_msg_as_read / mark_group_msg_as_read)。
    :param message_id: 消息 ID (可选)
    :param user_id: 好友 QQ 号，标记该私聊已读 (可选)
    :param group_id: 群号，标记该群聊已读 (可选)
    """
    if group_id is not None and message_id is None:
        return await client.call_api("mark_group_msg_as_read", {"group_id": int(group_id)})
    if user_id is not None and message_id is None:
        return await client.call_api("mark_private_msg_as_read", {"user_id": int(user_id)})
    params: dict[str, Any] = {}
    if message_id is not None:
        params["message_id"] = int(message_id)
    if user_id is not None:
        params["user_id"] = int(user_id)
    if group_id is not None:
        params["group_id"] = int(group_id)
    return await client.call_api("mark_msg_as_read", params)


@registry.register()
async def set_essence_msg(
    client: NapCatClient,
    message_id: int
) -> dict[str, Any]:
    """
    将指定群消息设为群精华消息 (NapCat 扩展接口: set_essence_msg)。
    :param message_id: 要设为精华的消息 ID
    """
    return await client.call_api("set_essence_msg", {"message_id": int(message_id)})


@registry.register()
async def delete_essence_msg(
    client: NapCatClient,
    message_id: int
) -> dict[str, Any]:
    """
    移出指定的群精华消息 (NapCat 扩展接口: delete_essence_msg)。
    :param message_id: 要移出精华的消息 ID
    """
    return await client.call_api("delete_essence_msg", {"message_id": int(message_id)})


@registry.register()
async def get_essence_msg_list(
    client: NapCatClient,
    group_id: int
) -> dict[str, Any]:
    """
    获取指定 QQ 群的精华消息列表 (NapCat 扩展接口: get_essence_msg_list)。
    :param group_id: 目标群号
    """
    return await client.call_api("get_essence_msg_list", {"group_id": int(group_id)})
