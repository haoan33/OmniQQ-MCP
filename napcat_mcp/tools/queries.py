"""
信息查询工具集 (登录信息、群列表、群详情、群成员、历史聊天记录、最近会话、Bot状态)
"""
from typing import Any, Optional
from . import registry
from ..client import NapCatClient


@registry.register()
async def get_login_info(
    client: NapCatClient
) -> dict[str, Any]:
    """
    获取当前登录的 QQ 账号信息 (返回 user_id 与 nickname) (OneBot 11: get_login_info)。
    """
    return await client.call_api("get_login_info", {})


@registry.register()
async def get_group_list(
    client: NapCatClient,
    no_cache: bool = True
) -> dict[str, Any]:
    """
    获取当前账号已加入的所有 QQ 群列表 (包含 group_id, group_name, member_count, max_member_count 等) (OneBot 11: get_group_list)。
    :param no_cache: 是否强制刷新最新群列表而不使用缓存，默认 True
    """
    return await client.call_api("get_group_list", {"no_cache": bool(no_cache)})


@registry.register()
async def get_group_info(
    client: NapCatClient,
    group_id: int,
    no_cache: bool = False
) -> dict[str, Any]:
    """
    获取指定 QQ 群的详细信息 (群名称、人数、群主、群备注等) (OneBot 11: get_group_info)。
    :param group_id: 目标群号
    :param no_cache: 是否不使用缓存
    """
    return await client.call_api("get_group_info", {
        "group_id": int(group_id),
        "no_cache": bool(no_cache)
    })


@registry.register()
async def get_group_member_info(
    client: NapCatClient,
    group_id: int,
    user_id: int,
    no_cache: bool = False
) -> dict[str, Any]:
    """
    获取指定群成员的详细资料 (群名片 card、昵称 nickname、群角色 role[owner/admin/member]、入群时间、最后发言时间、头衔等) (OneBot 11: get_group_member_info)。
    :param group_id: 群号
    :param user_id: 群成员 QQ 号
    :param no_cache: 是否强制刷新缓存
    """
    return await client.call_api("get_group_member_info", {
        "group_id": int(group_id),
        "user_id": int(user_id),
        "no_cache": bool(no_cache)
    })


@registry.register()
async def get_group_member_list(
    client: NapCatClient,
    group_id: int,
    no_cache: bool = False
) -> dict[str, Any]:
    """
    获取指定 QQ 群的全部成员名单列表 (OneBot 11: get_group_member_list)。
    :param group_id: 群号
    :param no_cache: 是否强制刷新缓存
    """
    return await client.call_api("get_group_member_list", {
        "group_id": int(group_id),
        "no_cache": bool(no_cache)
    })


@registry.register()
async def get_group_honor_info(
    client: NapCatClient,
    group_id: int,
    honor_type: str = "all"
) -> dict[str, Any]:
    """
    获取指定 QQ 群的群荣誉信息 (龙王、群聊之火、快乐源泉等) (OneBot 11: get_group_honor_info)。
    :param group_id: 群号
    :param honor_type: 荣誉类型: 'talkative'(龙王), 'performer'(群聊之火), 'legend'(群聊炽焰), 'strong_newbie'(冒尖小春笋), 'emotion'(快乐源泉), 或 'all'(全部)
    """
    return await client.call_api("get_group_honor_info", {
        "group_id": int(group_id),
        "type": str(honor_type)
    })


@registry.register()
async def get_friend_msg_history(
    client: NapCatClient,
    user_id: int,
    count: int = 20,
    message_seq: Optional[int] = None,
    reverse_order: bool = False
) -> dict[str, Any]:
    """
    从 NapCat 获取与指定好友的历史私聊消息记录 (NapCat OneBot 11: get_friend_msg_history)。
    :param user_id: 好友 QQ 号
    :param count: 获取的消息条数，默认 20
    :param message_seq: 历史游标，填上一页最早记录的 message_id；NapCat 的参数名沿用 message_seq，但不要填返回记录的 message_seq。不填则取最新记录。
    :param reverse_order: 向更旧的记录翻页时设为 True；默认 False 保持原工具行为。
    """
    params: dict[str, Any] = {
        "user_id": int(user_id),
        "count": int(count),
        "reverse_order": bool(reverse_order)
    }
    if message_seq is not None:
        params["message_seq"] = str(message_seq)
    return await client.call_api("get_friend_msg_history", params)


@registry.register()
async def get_group_msg_history(
    client: NapCatClient,
    group_id: int,
    count: int = 20,
    message_seq: Optional[int] = None,
    reverse_order: bool = False
) -> dict[str, Any]:
    """
    从 NapCat 获取指定群聊的历史聊天记录 (NapCat OneBot 11: get_group_msg_history)。
    :param group_id: 群号
    :param count: 获取的消息条数，默认 20
    :param message_seq: 历史游标，填上一页最早记录的 message_id；NapCat 的参数名沿用 message_seq，但不要填返回记录的 message_seq。不填则取最新记录。
    :param reverse_order: 向更旧的记录翻页时设为 True；默认 False 保持原工具行为。
    """
    params: dict[str, Any] = {
        "group_id": int(group_id),
        "count": int(count),
        "reverse_order": bool(reverse_order)
    }
    if message_seq is not None:
        params["message_seq"] = str(message_seq)
    return await client.call_api("get_group_msg_history", params)


@registry.register()
async def get_recent_contact(
    client: NapCatClient,
    count: int = 20
) -> dict[str, Any]:
    """
    获取当前 QQ 最近联系列表 / 最近会话列表 (包含最近联系的好友和群聊及最新消息摘要) (NapCat 扩展接口: get_recent_contact)。
    :param count: 返回的最近会话数量，默认 20
    """
    return await client.call_api("get_recent_contact", {"count": int(count)})


@registry.register()
async def get_napcat_status(
    client: NapCatClient
) -> dict[str, Any]:
    """
    获取 NapCat OneBot 11 协议端运行状态与版本信息 (组合调用 get_status 与 get_version_info)。
    """
    status_res = await client.call_api("get_status", {})
    ver_res = await client.call_api("get_version_info", {})
    return {
        "status": status_res.get("status", "failed"),
        "online_status": status_res.get("data"),
        "version_info": ver_res.get("data"),
        "ws_listener_connected": client.is_ws_connected
    }
