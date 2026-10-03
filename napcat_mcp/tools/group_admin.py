"""
群组管理与治理控制工具集 (踢人、禁言、管理员、群名片、头衔、加群审批、群待办等)
"""
from typing import Any, Optional
from . import registry
from ..client import NapCatClient


@registry.register()
async def set_group_kick(
    client: NapCatClient,
    group_id: int,
    user_id: int,
    reject_add_request: bool = False
) -> dict[str, Any]:
    """
    将指定成员移出群聊 / 群踢人 (OneBot 11: set_group_kick)。需具备管理员或群主权限。
    :param group_id: 群号
    :param user_id: 被移出的成员 QQ 号
    :param reject_add_request: 是否拒绝此人今后的加群申请，默认 False
    """
    return await client.call_api("set_group_kick", {
        "group_id": int(group_id),
        "user_id": int(user_id),
        "reject_add_request": bool(reject_add_request)
    })


@registry.register()
async def set_group_ban(
    client: NapCatClient,
    group_id: int,
    user_id: int,
    duration: int = 1800
) -> dict[str, Any]:
    """
    群聊单人禁言或解禁 (OneBot 11: set_group_ban)。
    :param group_id: 群号
    :param user_id: 目标成员 QQ 号
    :param duration: 禁言时长(秒)，设为 0 表示解除禁言，默认 1800 (30分钟)
    """
    return await client.call_api("set_group_ban", {
        "group_id": int(group_id),
        "user_id": int(user_id),
        "duration": int(duration)
    })


@registry.register()
async def set_group_whole_ban(
    client: NapCatClient,
    group_id: int,
    enable: bool = True
) -> dict[str, Any]:
    """
    开启或关闭群全员禁言 (OneBot 11: set_group_whole_ban)。
    :param group_id: 群号
    :param enable: True 开启全员禁言，False 关闭全员禁言
    """
    return await client.call_api("set_group_whole_ban", {
        "group_id": int(group_id),
        "enable": bool(enable)
    })


@registry.register()
async def set_group_admin(
    client: NapCatClient,
    group_id: int,
    user_id: int,
    enable: bool = True
) -> dict[str, Any]:
    """
    设置或取消群管理员 (OneBot 11: set_group_admin)。需群主权限。
    :param group_id: 群号
    :param user_id: 目标成员 QQ 号
    :param enable: True 设为管理员，False 取消管理员
    """
    return await client.call_api("set_group_admin", {
        "group_id": int(group_id),
        "user_id": int(user_id),
        "enable": bool(enable)
    })


@registry.register()
async def set_group_card(
    client: NapCatClient,
    group_id: int,
    user_id: int,
    card: str = ""
) -> dict[str, Any]:
    """
    修改群成员的群名片 / 群昵称 (OneBot 11: set_group_card)。
    :param group_id: 群号
    :param user_id: 目标成员 QQ 号
    :param card: 新群名片内容 (传空字符串表示清空群名片)
    """
    return await client.call_api("set_group_card", {
        "group_id": int(group_id),
        "user_id": int(user_id),
        "card": str(card)
    })


@registry.register()
async def set_group_name(
    client: NapCatClient,
    group_id: int,
    group_name: str
) -> dict[str, Any]:
    """
    修改 QQ 群名称 (OneBot 11: set_group_name)。
    :param group_id: 群号
    :param group_name: 新群名称
    """
    return await client.call_api("set_group_name", {
        "group_id": int(group_id),
        "group_name": str(group_name)
    })


@registry.register()
async def set_group_special_title(
    client: NapCatClient,
    group_id: int,
    user_id: int,
    special_title: str = "",
    duration: int = -1
) -> dict[str, Any]:
    """
    设置群成员专属头衔 (OneBot 11: set_group_special_title)。需群主权限。
    :param group_id: 群号
    :param user_id: 目标成员 QQ 号
    :param special_title: 专属头衔名称 (空字符串表示取消头衔)
    :param duration: 有效期秒数，默认 -1 表示永久
    """
    return await client.call_api("set_group_special_title", {
        "group_id": int(group_id),
        "user_id": int(user_id),
        "special_title": str(special_title),
        "duration": int(duration)
    })


@registry.register()
async def set_group_leave(
    client: NapCatClient,
    group_id: int,
    is_dismiss: bool = False
) -> dict[str, Any]:
    """
    退出群聊或解散群聊 (OneBot 11: set_group_leave)。
    :param group_id: 群号
    :param is_dismiss: 是否解散群 (仅当自己是群主时有效)，默认 False
    """
    return await client.call_api("set_group_leave", {
        "group_id": int(group_id),
        "is_dismiss": bool(is_dismiss)
    })


@registry.register()
async def set_group_add_request(
    client: NapCatClient,
    flag: str,
    sub_type: str = "add",
    approve: bool = True,
    reason: str = ""
) -> dict[str, Any]:
    """
    审批处理加群请求或邀请入群请求 (OneBot 11: set_group_add_request)。
    :param flag: 加群请求事件上报的 flag 标识
    :param sub_type: 请求类型，'add' (他人申请入群) 或 'invite' (被邀请入群)
    :param approve: True 同意，False 拒绝
    :param reason: 拒绝时的理由 (仅在 approve=False 时生效)
    """
    return await client.call_api("set_group_add_request", {
        "flag": str(flag),
        "sub_type": str(sub_type),
        "approve": bool(approve),
        "reason": str(reason)
    })


@registry.register()
async def set_group_todo(
    client: NapCatClient,
    group_id: int,
    message_id: int
) -> dict[str, Any]:
    """
    将群内的某条消息设置为“群待办”提醒全员 (NapCat 扩展接口: set_group_todo)。
    :param group_id: 群号
    :param message_id: 要设为群待办的消息 ID
    """
    return await client.call_api("set_group_todo", {
        "group_id": int(group_id),
        "message_id": int(message_id)
    })


@registry.register()
async def set_group_portrait(
    client: NapCatClient,
    group_id: int,
    file: str
) -> dict[str, Any]:
    """
    修改 QQ 群头像 (OneBot 11: set_group_portrait)。
    :param group_id: 群号
    :param file: 图片本地绝对路径、网络 URL 或 base64:// 字符串
    """
    return await client.call_api("set_group_portrait", {
        "group_id": int(group_id),
        "file": str(file)
    })


@registry.register()
async def get_group_at_all_remain(
    client: NapCatClient,
    group_id: int
) -> dict[str, Any]:
    """
    查询指定群聊今日剩余的 @全体成员 次数 (OneBot 11: get_group_at_all_remain)。
    :param group_id: 群号
    """
    return await client.call_api("get_group_at_all_remain", {"group_id": int(group_id)})


@registry.register()
async def get_group_shut_list(
    client: NapCatClient,
    group_id: int
) -> dict[str, Any]:
    """
    获取指定群聊当前处于被禁言状态的成员列表 (NapCat 扩展接口: get_group_shut_list)。
    :param group_id: 群号
    """
    return await client.call_api("get_group_shut_list", {"group_id": int(group_id)})


@registry.register()
async def get_group_system_msg(
    client: NapCatClient
) -> dict[str, Any]:
    """
    获取群系统消息列表 (包括待审批的入群申请、被邀请进群通知等) (OneBot 11: get_group_system_msg)。
    """
    return await client.call_api("get_group_system_msg", {})
