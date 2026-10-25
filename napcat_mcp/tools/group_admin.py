"""
群组管理与治理控制工具集 (踢人、禁言、管理员、群名片、头衔、加群审批、群待办等)
"""
from typing import Any
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
    将指定群成员强制移出 QQ 群聊（群踢人）(OneBot 11: set_group_kick)。
    适用场景：清理违规群成员。不适用与替代：若仅需临时限制发言而非踢出群聊，请改用 `set_group_ban`；若机器人自身要退群，请改用 `set_group_leave`。
    行为与权限：不可逆的破坏性群管操作（`reject_add_request=True` 时还将永久拉黑其后续入群申请）；前置要求当前账号在该群具备群主或管理员权限（且管理员不能踢出其他管理员或群主），权限不足返回非 0 `retcode`。
    :param group_id: 目标 QQ 群号（正整数）
    :param user_id: 要移出群聊的成员 QQ 号（正整数）
    :param reject_add_request: 为 True 时同时屏蔽该成员今后的再次加群申请，默认 False
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
    对指定 QQ 群内的单个成员执行定期禁言或解除禁言 (OneBot 11: set_group_ban)。
    适用场景：对单个群成员禁言或通过传 `duration=0` 解禁。不适用与替代：若需开启或关闭全群全员禁言，请改用 `set_group_whole_ban`；若需将成员移出群聊，请改用 `set_group_kick`。
    参数约束与行为：`duration` 设为 `0` 表示立即解除禁言，正整数表示禁言秒数（最大通常不超过 30 天即 2592000 秒）；幂等操作，要求当前账号为该群管理员或群主。
    :param group_id: 目标 QQ 群号（正整数）
    :param user_id: 目标群成员的 QQ 号（正整数）
    :param duration: 禁言持续秒数；传 0 表示解除禁言，默认 1800（30 分钟）
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
    开启或关闭指定 QQ 群的全员禁言模式 (OneBot 11: set_group_whole_ban)。
    适用场景：发布重要公告期间开启全群禁言或恢复群聊发言。不适用与替代：若仅需针对特定违规成员禁言，请改用 `set_group_ban`。
    行为与权限：幂等状态变更（开启后仅群主与管理员可发言）；前置要求当前账号具备该群管理员或群主权限。
    :param group_id: 目标 QQ 群号（正整数）
    :param enable: 为 True 时开启全员禁言，为 False 时解除全员禁言，默认 True
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
    任命或罢免指定 QQ 群的群管理员 (OneBot 11: set_group_admin)。
    适用场景：群主调整群管理员名单。不适用与替代：若仅需授予成员展示性的群专属头衔（无管理权限），请改用 `set_group_special_title`。
    行为与权限：幂等权限变更操作；前置严格要求当前登录账号必须是该群的**群主 (owner)**，普通管理员调用将返回权限错误。
    :param group_id: 目标 QQ 群号（正整数）
    :param user_id: 目标群成员的 QQ 号（正整数）
    :param enable: 为 True 时设为管理员，为 False 时取消其管理员身份，默认 True
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
    修改指定群成员在群内的群名片（群昵称）(OneBot 11: set_group_card)。
    适用场景：修改自己的群名片，或作为管理员统一规范群成员名片格式。不适用与替代：若需修改整个 QQ 群的名称请改用 `set_group_name`；若需修改好友私聊备注名请改用 `set_friend_remark`。
    参数约束与行为：`card` 传空字符串 `""` 时清空群名片并恢复显示其个人 QQ 昵称；修改他人名片需具备群管理员或群主权限。
    :param group_id: 目标 QQ 群号（正整数）
    :param user_id: 目标群成员的 QQ 号（正整数）
    :param card: 新的群名片文本；传空字符串 "" 表示清除自定义群名片
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
    修改指定 QQ 群的群聊名称 (OneBot 11: set_group_name)。
    适用场景：更新群聊标题。不适用与替代：若需修改群内某个成员的群名片，请改用 `set_group_card`。
    行为与权限：幂等覆盖操作；前置要求当前账号具备该群管理员或群主权限。
    :param group_id: 目标 QQ 群号（正整数）
    :param group_name: 新的群名称非空字符串
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
    为指定群成员授予或清除群聊专属头衔徽章 (OneBot 11: set_group_special_title)。
    适用场景：群主为成员颁发荣誉头衔。不适用与替代：若需修改群名片请改用 `set_group_card`；若需授予实际群管权限请改用 `set_group_admin`。
    参数约束与权限：`special_title` 传空字符串表示收回头衔，`duration=-1` 表示永久有效；前置严格要求当前账号为该群**群主 (owner)**。
    :param group_id: 目标 QQ 群号（正整数）
    :param user_id: 目标群成员的 QQ 号（正整数）
    :param special_title: 专属头衔文本（传空字符串 "" 表示取消头衔）
    :param duration: 头衔有效期秒数，默认 -1 表示永久有效
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
    使当前登录的 QQ 账号主动退出指定群聊，或作为群主解散该群 (OneBot 11: set_group_leave)。
    适用场景：清理不再需要驻留的群聊。不适用与替代：若需将群内某位其他成员踢出群聊，请改用 `set_group_kick`，切勿误调本工具导致机器人自身退群。
    行为与副作用：不可逆的高危破坏性操作——一旦退群或解散（`is_dismiss=True` 仅当自身为群主时生效），将立即失去该群访问权限与群成员关系。
    :param group_id: 要退出或解散的目标 QQ 群号（正整数）
    :param is_dismiss: 为 True 时解散整个群聊（仅群主有效），为 False 时仅自己退出群聊，默认 False
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
    审批处理他人申请入群或邀请当前账号入群的验证请求 (OneBot 11: set_group_add_request)。
    适用场景：从 `get_recent_notices_and_requests` 或 `get_group_system_msg` 获取入群请求 `flag` 后执行同意或拒绝。不适用与替代：若需审批个人加好友请求，请改用 `set_friend_add_request`。
    参数约束与行为：`flag` 与 `sub_type` (`'add'` 或 `'invite'`) 必须与原始请求事件严格一致；`reason` 仅在 `approve=False` 拒绝时作为拒绝理由发给申请人。
    :param flag: 入群请求事件上报的唯一请求标识 flag 字符串
    :param sub_type: 请求子类型枚举，'add'（他人申请加群，需管理员权限）或 'invite'（被邀请进群），默认 'add'
    :param approve: 为 True 时同意请求，为 False 时拒绝请求，默认 True
    :param reason: 当 approve=False 拒绝入群时附带的拒绝理由文本（可选）
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
    将群内的某条已有消息设置为全群顶置强提醒的“群待办”事项 (NapCat 扩展接口: set_group_todo)。
    适用场景：发送重要群通知后，将其 `message_id` 设为群待办以强化全员触达。不适用与替代：若仅需将消息收录进群精华区而不弹待办，请改用 `set_essence_msg`。
    行为与权限：会向全群成员触发客户端待办横幅提醒；前置要求当前账号具备该群管理员或群主权限。
    :param group_id: 目标 QQ 群号（正整数）
    :param message_id: 要设为群待办的群内消息整数 ID
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
    修改指定 QQ 群的群聊头像图片 (OneBot 11: set_group_portrait)。
    适用场景：更换所管理群聊的群图标。不适用与替代：若需更换当前登录 QQ 个人账号的头像，请改用 `set_qq_avatar`。
    参数约束与权限：`file` 支持本地图片绝对路径、HTTP/HTTPS URL 或 `base64://` 字符串；前置要求当前账号具备该群管理员或群主权限。
    :param group_id: 目标 QQ 群号（正整数）
    :param file: 新群头像图片源，支持本机绝对路径、HTTP URL 或 base64:// 编码字符串
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
    查询指定 QQ 群内当前账号今日剩余的 `@全体成员` 可用配额次数 (OneBot 11: get_group_at_all_remain)。
    适用场景：在调用 `send_group_msg` 发送 `@全体成员` 通知前，预检是否具有权限及剩余次数。不适用与替代：查询群人数或基础资料请改用 `get_group_info`。
    行为与返回：纯只读无副作用查询；返回 `can_at_all`（布尔值）、群内今日剩余总次数及个人今日剩余次数。
    :param group_id: 目标 QQ 群号（正整数）
    """
    return await client.call_api("get_group_at_all_remain", {"group_id": int(group_id)})


@registry.register()
async def get_group_shut_list(
    client: NapCatClient,
    group_id: int
) -> dict[str, Any]:
    """
    查询指定 QQ 群内当前正处于被禁言状态的成员列表及到期时间 (NapCat 扩展接口: get_group_shut_list)。
    适用场景：核查群内有哪些成员被禁言以便调用 `set_group_ban(duration=0)` 解禁。不适用与替代：若需获取全群所有正常成员名单，请改用 `get_group_member_list`。
    行为与返回：纯只读无副作用查询；返回被禁言成员的 `uin`、昵称与解禁时间戳列表。
    :param group_id: 目标 QQ 群号（正整数）
    """
    return await client.call_api("get_group_shut_list", {"group_id": int(group_id)})


@registry.register()
async def get_group_system_msg(
    client: NapCatClient
) -> dict[str, Any]:
    """
    从 QQ 服务器拉取群系统通知消息列表，包含待审批的加群申请 (`join_requests`) 与被邀请进群通知 (`invited_requests`) (OneBot 11: get_group_system_msg)。
    适用场景：查询历史积压的入群申请并获取 `flag` 传给 `set_group_add_request` 审批。不适用与替代：若需同时查看实时群文件上传、撤回通知及加好友请求，请配合使用 `get_recent_notices_and_requests`。
    行为与返回：纯只读无副作用查询；成功返回包含 `invited_requests` 与 `join_requests` 数组的 `data` 字典。
    """
    return await client.call_api("get_group_system_msg", {})
