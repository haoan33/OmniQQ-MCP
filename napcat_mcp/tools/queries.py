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
    获取当前在线 QQ 账号的基础身份信息，返回 `user_id`（QQ 号）与 `nickname`（昵称）(OneBot 11: get_login_info)。
    适用场景：快速确认当前是哪个 QQ 号在线，或验证 OneBot 接口连通性。不适用与替代：若需检查本地所有已缓存的历史账号列表或运行时安装与 GitHub 最新版本对比，请改用 `check_napcat_environment`。
    行为与返回：纯只读无副作用操作；成功返回 `status='ok'` 及 `data: {"user_id": int, "nickname": str}`，若当前未登录或服务未启动则返回 `status='failed'` 及非 0 `retcode`。
    """
    return await client.call_api("get_login_info", {})


@registry.register()
async def get_group_list(
    client: NapCatClient,
    no_cache: bool = True
) -> dict[str, Any]:
    """
    获取当前登录 QQ 账号已加入的全部 QQ 群列表，包含每群的 `group_id`、`group_name`、`member_count` 与 `max_member_count` (OneBot 11: get_group_list)。
    适用场景：在发送群消息或上传群文件前，根据群名称查找对应的 `group_id` 或遍历已加入的群聊。不适用与替代：若已知具体 `group_id` 仅需查询该单群的详细资料或需查询好友列表，请通过 `call_napcat_api` 调用 `get_group_info` 或 `get_friend_list`。
    参数约束与行为：`no_cache=True`（默认）会强制向 QQ 服务器拉取最新群列表以确保新加入的群立即可见；纯只读无副作用操作，成功在 `data` 中返回群信息字典数组。
    :param no_cache: 为 True 时绕过本地缓存强制从服务器刷新最新群列表，为 False 时优先使用缓存，默认 True
    """
    return await client.call_api("get_group_list", {"no_cache": bool(no_cache)})


@registry.register()
async def get_group_info(
    client: NapCatClient,
    group_id: int,
    no_cache: bool = False
) -> dict[str, Any]:
    """
    查询指定单个 QQ 群的详细资料，包括群名称、群人数、最大容量等 (OneBot 11: get_group_info)。
    适用场景：已知 `group_id` 需要核实该群名称或人数。不适用与替代：若不知道 `group_id` 需遍历所有已加入的群，请改用 `get_group_list`；若需获取群内所有成员名单，请改用 `get_group_member_list`。
    行为与返回：纯只读无副作用查询；成功返回 `data` 字典，群号不存在时返回非 0 `retcode`。
    :param group_id: 目标 QQ 群号（正整数）
    :param no_cache: 是否绕过缓存强制向服务器刷新群资料，默认 False
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
    获取指定 QQ 群内单个成员的详细资料，包括群名片 `card`、昵称 `nickname`、权限角色 `role` (`owner`/`admin`/`member`)、入群时间与专属头衔 (OneBot 11: get_group_member_info)。
    适用场景：核查某个群成员的身份、群名片或管理员权限。不适用与替代：若需拉取全群所有成员列表，请改用 `get_group_member_list`；若目标用户不在群内需查询其公开资料，请改用 `get_stranger_info`。
    行为与返回：纯只读查询；若该用户不在指定群内则返回非 0 `retcode`。
    :param group_id: 目标 QQ 群号（正整数）
    :param user_id: 要查询的群成员 QQ 号（正整数）
    :param no_cache: 是否强制刷新缓存以获取最新名片与权限状态，默认 False
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
    获取指定 QQ 群的全部群成员名单及各自的基础资料列表 (OneBot 11: get_group_member_list)。
    适用场景：统计群成员名单、按姓名/群名片在群内检索成员 QQ 号。不适用与替代：若已知成员 `user_id` 仅查单人详情，请改用开销更小的 `get_group_member_info`。
    行为与返回：纯只读查询（大群可能返回数百至数千条记录）；成功在 `data` 中返回成员字典数组。
    :param group_id: 目标 QQ 群号（正整数）
    :param no_cache: 是否绕过缓存强制重新拉取全群成员列表，默认 False
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
    查询指定 QQ 群的群荣誉榜单（龙王、群聊之火、快乐源泉等）(OneBot 11: get_group_honor_info)。
    适用场景：查看群内活跃度排行或龙王得主。不适用与替代：查询普通群基础资料请改用 `get_group_info`。
    参数约束与行为：`honor_type` 支持 `'all'` 或单项枚举；纯只读无副作用操作。
    :param group_id: 目标 QQ 群号（正整数）
    :param honor_type: 荣誉类型枚举: 'all'(全部), 'talkative'(龙王), 'performer'(群聊之火), 'legend'(群聊炽焰), 'strong_newbie'(冒尖小春笋), 'emotion'(快乐源泉)，默认 'all'
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
    向 NapCat 协议端分页拉取与指定好友的私聊历史聊天记录 (NapCat OneBot 11: get_friend_msg_history)。
    适用场景：需要回溯 MCP 启动之前的历史私聊记录或核对过往双方对话。不适用与替代：若仅需读取近期收到的实时新消息（含群聊与私聊），请优先使用零网络开销的 `get_recent_messages`；若查询群聊历史，请改用 `get_group_msg_history`。
    参数约束与交互：向上翻页时，`message_seq` 游标必须填入上一页最早一条记录的 `message_id`（切勿填入返回记录中的 `message_seq` 字段），并配合 `reverse_order=True`。
    行为与返回：纯只读无副作用查询；成功返回 `data.messages` 历史消息数组。
    :param user_id: 目标好友的 QQ 号（正整数）
    :param count: 单次拉取的消息条数（建议 1~100，默认 20）
    :param message_seq: 分页起始游标；必须填上一页最早记录的 `message_id` 整数值，留空则从最新一条消息开始拉取
    :param reverse_order: 向更旧的历史消息翻页时设为 True，默认 False
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
    向 NapCat 协议端分页拉取指定 QQ 群的历史群聊消息记录 (NapCat OneBot 11: get_group_msg_history)。
    适用场景：回溯群内历史聊天记录或查找服务启动前的群通知。不适用与替代：若仅需获取后台实时监听到的最新消息，请改用 `get_recent_messages`；若查询个人私聊历史，请改用 `get_friend_msg_history`。
    参数约束与交互：翻页游标 `message_seq` 必须填入上一页最早记录的 `message_id`（不要填返回对象的 `message_seq`），向旧消息翻页时设 `reverse_order=True`。
    行为与返回：纯只读无副作用操作；成功在 `data.messages` 中返回群消息数组。
    :param group_id: 目标 QQ 群号（正整数）
    :param count: 单次拉取的消息条数（建议 1~100，默认 20）
    :param message_seq: 分页起始游标；必须填上一页最早记录的 `message_id` 整数值，留空则获取最新记录
    :param reverse_order: 向更旧的历史记录翻页时设为 True，默认 False
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
    获取当前 QQ 账号的最近联系会话列表（包含近期产生过交互的好友与群聊及最新消息摘要）(NapCat 扩展接口: get_recent_contact)。
    适用场景：查看最近活跃的聊天会话列表。不适用与替代：若需读取实时收到的完整消息正文与附件信息，请改用 `get_recent_messages`。
    行为与返回：纯只读查询；返回按最后活跃时间排序的最近会话数组。
    :param count: 返回的最近会话最大数量，默认 20
    """
    return await client.call_api("get_recent_contact", {"count": int(count)})


@registry.register()
async def get_napcat_status(
    client: NapCatClient
) -> dict[str, Any]:
    """
    获取 NapCat OneBot 11 协议端的在线状态、版本信息及后台 WebSocket 监听器连接状态 (组合调用 get_status 与 get_version_info)。
    适用场景：轻量级探测协议端在线状态与版本号。不适用与替代：若需全面检查本地运行时安装目录、缓存账号列表及 GitHub 最新版本更新对比，请改用 `check_napcat_environment`；若仅需获取当前登录 QQ 号与昵称，请改用 `get_login_info`。
    行为与返回：纯只读无副作用操作；返回 `online_status`、`version_info` 与 `ws_listener_connected`。
    """
    status_res = await client.call_api("get_status", {})
    ver_res = await client.call_api("get_version_info", {})
    return {
        "status": status_res.get("status", "failed"),
        "online_status": status_res.get("data"),
        "version_info": ver_res.get("data"),
        "ws_listener_connected": client.is_ws_connected
    }
