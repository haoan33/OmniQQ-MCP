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
    message: str | list[dict[str, Any]],
    auto_escape: bool = False
) -> dict[str, Any]:
    """
    向指定 QQ 好友或私聊用户发送单条即时私聊消息 (OneBot 11: send_private_msg)。
    适用场景：向个人 QQ 账号发送文本、CQ 码或富媒体消息段。不适用与替代：若目标是 QQ 群聊，请改用 `send_group_msg`；若需发送本地文件附件，请改用 `upload_private_file`。
    参数约束与交互：`message` 支持含 CQ 码的字符串或 OneBot 标准消息段数组（如 `[{"type":"face","data":{"id":"14"}}]`）；仅当希望将 `[CQ:...]` 原样作为纯文本输出时才将 `auto_escape` 设为 `True`。
    行为与返回：非幂等外部发送操作（调用即真实发出消息）；前置要求当前账号已在线且与目标存在好友或临时会话关系，成功返回 `status='ok'` 及 `data.message_id`（可用于后续 `delete_msg` 撤回），被风控或非好友时返回非 0 `retcode`。
    :param user_id: 接收方个人 QQ 号（5~11 位正整数）
    :param message: 消息正文；可传普通字符串、内嵌 CQ 码字符串或 OneBot 11 消息段对象数组
    :param auto_escape: 为 True 时忽略文本中的 CQ 码语法并按纯文本字面量发送；为 False 时解析 CQ 码，默认 False
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
    message: str | list[dict[str, Any]],
    auto_escape: bool = False
) -> dict[str, Any]:
    """
    向指定 QQ 群发送单条群聊消息 (OneBot 11: send_group_msg)。
    适用场景：在已加入的 QQ 群内发布通知、@成员或发送富媒体消息。不适用与替代：若目标是个人好友私聊，请改用 `send_private_msg`；若需向群内上传文档或压缩包附件，请改用 `upload_group_file`。
    参数约束与交互：如需产生真实的 @全体成员 或 @指定成员 提醒，必须在 `message` 中使用 CQ 码 `[CQ:at,qq=all]` / `[CQ:at,qq=123456]`（且保持 `auto_escape=False`）或传入 `at` 类型消息段，手写纯文本“@全体成员”不会触发群提醒。
    行为与返回：非幂等群广播操作；前置要求当前 QQ 已加入目标群且未被禁言（@全体成员需群主或管理员权限且受每日次数限制），成功返回 `status='ok'` 及 `data.message_id`，无权限或被禁言时返回非 0 `retcode`。
    :param group_id: 目标 QQ 群号（正整数，可通过 `get_group_list` 查询已加入的群号）
    :param message: 群消息内容；支持普通文本、含 `[CQ:at,qq=all]` 的 CQ 码字符串或 OneBot 11 消息段数组
    :param auto_escape: 为 True 时不解析 CQ 码而按纯文本字面量发送；需要触发 @提醒或表情时必须保持 False，默认 False
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
    message: str | list[dict[str, Any]],
    auto_escape: bool = False
) -> dict[str, Any]:
    """
    按 `message_type` 动态路由发送私聊或群聊消息的底层聚合接口 (OneBot 11: send_msg)。
    适用场景：仅在调用方以变量形式动态持有会话类型 (`private`/`group`) 时使用。不适用与替代：明确知道发送目标是个人或群聊时，请优先使用语义更明确的 `send_private_msg` 或 `send_group_msg`。
    参数约束与行为：`message_type='private'` 时 `target_id` 解释为好友 QQ 号，为 `'group'` 时解释为群号；非幂等发送操作，成功返回 `data.message_id`。
    :param message_type: 会话类型枚举，'private'（私聊）或 'group'（群聊）
    :param target_id: 目标 ID；私聊时填对方 QQ 号，群聊时填目标群号
    :param message: 要发送的文本、CQ 码字符串或 OneBot 消息段数组
    :param auto_escape: 为 True 时按纯文本发送而不解析 CQ 码，默认 False
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
    从私聊或群聊会话中永久撤回指定消息 (OneBot 11: delete_msg)。
    适用场景：发错消息需紧急撤回，或作为群主/群管理员撤回群成员的违规发言。不适用与替代：若仅需将群精华消息移出精华列表或删除群共享文件，请通过 `call_napcat_api` 调用 `delete_essence_msg` 或 `delete_group_file`。
    参数约束：传入的 `message_id` 必须来自 `send_private_msg`、`send_group_msg` 的返回值或 `get_recent_messages` 消息记录中的有效整数 ID。
    行为与权限限制：不可逆的破坏性操作（撤回后消息无法恢复）；撤回自身消息受 QQ 平台 2 分钟时效限制，撤回他人群消息要求当前账号在该群具备管理员或群主权限，超时或权限不足将返回非 0 `retcode`。
    :param message_id: 目标消息的唯一整数 ID（由发送接口返回或从近期消息列表中获取）
    """
    return await client.call_api("delete_msg", {"message_id": int(message_id)})


@registry.register()
async def get_msg(
    client: NapCatClient,
    message_id: int
) -> dict[str, Any]:
    """
    根据 `message_id` 查询单条历史消息的完整详情，包含发送者信息、时间戳与原始消息段数组 (OneBot 11: get_msg)。
    适用场景：已知单条消息 ID 需检视其完整富媒体消息段或引用上下文时调用。不适用与替代：若需获取最新收到的多条实时消息列表，请改用 `get_recent_messages`；若需展开合并转发卡片，请改用 `get_forward_msg`。
    行为与返回：纯只读无副作用查询；成功返回 `data`（含 `sender`, `time`, `message`, `raw_message`），若消息 ID 不存在或已过期则返回非 0 `retcode`。
    :param message_id: 要查询的目标消息整数 ID
    """
    return await client.call_api("get_msg", {"message_id": int(message_id)})


@registry.register()
async def get_forward_msg(
    client: NapCatClient,
    message_id: str
) -> dict[str, Any]:
    """
    解析并获取合并转发消息卡片 (`[聊天记录]`) 内部的全部子消息节点列表 (OneBot 11: get_forward_msg)。
    适用场景：当收到 `forward` 类型的合并转发消息、需要读取其中包含的多条原始聊天内容时调用。不适用与替代：查询普通单条消息详情请改用 `get_msg`；向他人发送合并转发请改用 `send_private_forward_msg` 或 `send_group_forward_msg`。
    行为与返回：只读操作；返回 `data.messages` 节点数组，若转发 резидент ID 无效或过期则返回错误。
    :param message_id: 合并转发消息段中的转发资源 ID（字符串或整数转换的字符串）
    """
    return await client.call_api("get_forward_msg", {"message_id": str(message_id), "id": str(message_id)})


@registry.register()
async def send_private_forward_msg(
    client: NapCatClient,
    user_id: int,
    messages: list
) -> dict[str, Any]:
    """
    将多条消息打包为一张合并转发聊天记录卡片发送给指定好友 (NapCat OneBot 11: send_private_forward_msg)。
    适用场景：向个人好友汇总转发多条历史聊天记录或长篇多段内容。不适用与替代：发送单条普通私聊消息请改用 `send_private_msg`；向 QQ 群发送合并转发请改用 `send_group_forward_msg`。
    参数约束与行为：`messages` 须为包含 `type='node'` 的节点字典列表；非幂等发送操作，成功返回 `data.message_id`。
    :param user_id: 接收方好友的 QQ 号（正整数）
    :param messages: 合并转发节点数组，每项格式如 `{"type":"node","data":{"name":"昵称","uin":"QQ号","content":"内容"}}`
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
    将多条消息打包为一张合并转发聊天记录卡片发送至指定 QQ 群 (NapCat OneBot 11: send_group_forward_msg)。
    适用场景：向群聊批量转发多条消息记录以避免刷屏。不适用与替代：发送单条群通知请改用 `send_group_msg`；向个人好友发送合并转发请改用 `send_private_forward_msg`。
    参数约束与行为：`messages` 须为非空的 `node` 节点数组；非幂等群发操作，需当前账号在该群未被禁言，成功返回 `data.message_id`。
    :param group_id: 目标 QQ 群号（正整数）
    :param messages: 合并转发节点数组，每项格式如 `{"type":"node","data":{"name":"昵称","uin":"QQ号","content":"内容"}}`
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
    对指定 QQ 用户的个人资料卡执行名片点赞 (OneBot 11: send_like)。
    适用场景：响应用户“赞我/资料卡点赞”的社交互动指令。不适用与替代：若需对聊天窗口中的某条具体消息贴表情回应，请改用 `set_msg_emoji_like`；若需发送窗口抖动提醒，请改用 `send_poke`。
    参数约束与行为：`times` 有效范围为 1~10（普通用户每日对同一好友上限 10 次）；受 QQ 每日点赞配额限制，超出今日上限时返回非 0 `retcode`。
    :param user_id: 目标用户的 QQ 号（正整数）
    :param times: 连续点赞次数，取值范围 1~10，默认 10
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
    向指定 QQ 用户发送“戳一戳”轻量级互动提醒，支持私聊戳一戳或群内戳指定成员 (NapCat 扩展接口: send_poke)。
    适用场景：在不发送文字消息的情况下触发系统级的“戳了戳你”提示。不适用与替代：如需发送带正文的消息或 @提醒，请改用 `send_private_msg` 或 `send_group_msg`。
    参数交互与行为：传 `group_id` 时在对应群聊内戳 `user_id`，省略 `group_id` 时发起私聊戳一戳；非幂等操作，频繁调用可能触发客户端冷却限制。
    :param user_id: 被戳的目标用户 QQ 号（正整数）
    :param group_id: 群聊群号；传入时为群内戳一戳，留空时为好友私聊戳一戳
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
    对指定的群聊或私聊消息添加或移除贴表情回应 (NapCat 扩展接口: set_msg_emoji_like)。
    适用场景：用表情符号（如点赞👍）对某条消息作轻量级反馈。不适用与替代：若需给用户个人主页资料卡点赞，请改用 `send_like`。
    参数约束与行为：`set_like=True` 为贴上表情，`False` 为取消已贴表情；该操作具有幂等性，重复设置同一状态不会产生额外副作用。
    :param message_id: 目标消息的整数 ID
    :param emoji_id: QQ 表情或 Unicode 表情的数字编码（如 128077 代表👍，76 代表赞）
    :param set_like: 为 True 时添加表情回应，为 False 时移除已添加的同款表情回应，默认 True
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
    清除指定单条消息、好友私聊会话或群聊会话的未读红点状态 (NapCat 扩展接口: mark_msg_as_read)。
    适用场景：处理完实时消息后同步清除 QQ 客户端上的未读计数。不适用与替代：本工具不会清空本地 MCP 内存缓存池；如需清空内存消息缓冲，请改用 `clear_recent_messages_buffer`。
    参数交互与行为：至少应提供 `message_id`、`user_id` 或 `group_id` 之一（仅传 `group_id` 清除整群未读，仅传 `user_id` 清除该私聊未读）；幂等操作，无破坏性副作用。
    :param message_id: 要标记已读的具体消息 ID（可选）
    :param user_id: 要将整个私聊会话标记为已读的好友 QQ 号（可选）
    :param group_id: 要将整个群聊会话标记为已读的目标群号（可选）
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
    将指定的群聊消息添加到群精华消息列表 (NapCat 扩展接口: set_essence_msg)。
    适用场景：将群内重要通知或优质发言固定到群精华区。不适用与替代：若需取消精华状态请改用 `delete_essence_msg`；若需设为强制弹窗的群待办请改用 `set_group_todo`。
    行为与权限：幂等修改操作；前置要求当前账号在该群拥有管理员或群主权限，普通群成员调用将返回权限错误。
    :param message_id: 要设为群精华的群聊消息整数 ID
    """
    return await client.call_api("set_essence_msg", {"message_id": int(message_id)})


@registry.register()
async def delete_essence_msg(
    client: NapCatClient,
    message_id: int
) -> dict[str, Any]:
    """
    将指定消息从 QQ 群精华消息列表中移除，保留原群聊消息不被撤回 (NapCat 扩展接口: delete_essence_msg)。
    适用场景：清理过期的群精华条目。不适用与替代：若需从群聊记录中彻底撤回该消息，请改用 `delete_msg`；若需新增群精华，请改用 `set_essence_msg`。
    行为与权限：前置要求当前账号具备该群管理员或群主权限，且目标消息当前已处于精华列表中（可通过 `get_essence_msg_list` 查询）。
    :param message_id: 要移出群精华列表的目标消息整数 ID
    """
    return await client.call_api("delete_essence_msg", {"message_id": int(message_id)})


@registry.register()
async def get_essence_msg_list(
    client: NapCatClient,
    group_id: int
) -> dict[str, Any]:
    """
    获取指定 QQ 群当前的全部精华消息列表 (NapCat 扩展接口: get_essence_msg_list)。
    适用场景：查阅群内沉淀的精华通知或获取 `message_id` 以便调用 `delete_essence_msg` 管理精华。不适用与替代：查询常规群聊历史消息请改用 `get_group_msg_history`。
    行为与返回：纯只读无副作用查询；返回包含发送者、设精人、设精时间及消息 ID 的数组。
    :param group_id: 目标 QQ 群号（正整数）
    """
    return await client.call_api("get_essence_msg_list", {"group_id": int(group_id)})
