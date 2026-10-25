"""
好友关系与个人账号设置工具集 (好友列表、分组、备注、好友申请审批、头像、个性签名、在线状态)
"""
from typing import Any, Optional
from . import registry
from ..client import NapCatClient


@registry.register()
async def get_friend_list(
    client: NapCatClient,
    no_cache: bool = False
) -> dict[str, Any]:
    """
    获取当前登录 QQ 账号的全部扁平好友列表，包含每个好友的 `user_id`、`nickname` 与 `remark`（备注名）(OneBot 11: get_friend_list)。
    适用场景：按姓名/备注名查找好友 QQ 号或遍历好友名单。不适用与替代：若需获取带好友分组目录树结构的列表，请改用 `get_friends_with_category`；若需查询非好友陌生人的公开资料，请改用 `get_stranger_info`。
    行为与返回：纯只读无副作用查询；成功在 `data` 中返回好友信息字典数组。
    :param no_cache: 为 True 时绕过本地缓存强制从服务器拉取最新好友列表，默认 False
    """
    return await client.call_api("get_friend_list", {"no_cache": bool(no_cache)})


@registry.register()
async def get_friends_with_category(
    client: NapCatClient
) -> dict[str, Any]:
    """
    获取按 QQ 好友分组归类组织的层级式好友列表 (NapCat 扩展接口: get_friends_with_category)。
    适用场景：需要了解某个好友所属分组名称或按分组筛选好友时调用。不适用与替代：若仅需扁平的全部好友数组以快速检索 `user_id`，请改用结构更简单的 `get_friend_list`。
    行为与返回：纯只读无副作用操作；返回包含各分组 ID、分组名称及组内好友列表的数组。
    """
    return await client.call_api("get_friends_with_category", {})


@registry.register()
async def get_stranger_info(
    client: NapCatClient,
    user_id: int,
    no_cache: bool = False
) -> dict[str, Any]:
    """
    查询任意指定 QQ 用户（支持好友或非好友陌生人）的公开个人资料，包含昵称、性别、年龄、QQ 等级与个性签名 (OneBot 11: get_stranger_info)。
    适用场景：根据未知 QQ 号核实对方公开资料。不适用与替代：若目标在特定 QQ 群内且需查看其群名片或群管理员身份，请改用 `get_group_member_info`；若查询当前机器人自己的登录信息，请改用 `get_login_info`。
    行为与返回：纯只读无副作用查询；返回用户资料字典，账号不存在时返回非 0 `retcode`。
    :param user_id: 要查询的目标用户 QQ 号（正整数）
    :param no_cache: 是否绕过缓存强制拉取最新公开资料，默认 False
    """
    return await client.call_api("get_stranger_info", {
        "user_id": int(user_id),
        "no_cache": bool(no_cache)
    })


@registry.register()
async def delete_friend(
    client: NapCatClient,
    user_id: int
) -> dict[str, Any]:
    """
    从当前登录 QQ 的好友列表中永久删除指定好友 (OneBot 11: delete_friend)。
    适用场景：用户明确授权解除与某人的 QQ 好友关系时调用。不适用与替代：若仅需将某人移出群聊请改用 `set_group_kick`；若仅需修改好友备注请改用 `set_friend_remark`。
    行为与副作用：不可逆的破坏性操作——删除后双方好友关系立即解除，无法继续向对方发送需要好友关系的私聊或文件，除非重新发起加好友申请并获对方通过；目标非好友时返回非 0 `retcode`。
    :param user_id: 要解除好友关系的目标好友 QQ 号（正整数，须当前已为好友）
    """
    return await client.call_api("delete_friend", {"user_id": int(user_id)})


@registry.register()
async def set_friend_remark(
    client: NapCatClient,
    user_id: int,
    remark: str
) -> dict[str, Any]:
    """
    设置或修改当前账号对指定 QQ 好友的专属备注名 (NapCat 扩展接口: set_friend_remark)。
    适用场景：为好友添加姓名备注以便后续识别。不适用与替代：若需修改群成员在群内的群名片，请改用 `set_group_card`；若需修改机器人自己的个人昵称，请改用 `set_qq_profile`。
    行为与权限：幂等覆盖操作（仅自己可见）；前置要求目标 `user_id` 已经是当前账号的好友。
    :param user_id: 目标好友的 QQ 号（正整数）
    :param remark: 新的好友备注名称字符串（传空字符串可清空备注）
    """
    return await client.call_api("set_friend_remark", {
        "user_id": int(user_id),
        "remark": str(remark)
    })


@registry.register()
async def set_friend_add_request(
    client: NapCatClient,
    flag: str,
    approve: bool = True,
    remark: str = ""
) -> dict[str, Any]:
    """
    审批处理他人发来的添加好友验证请求 (OneBot 11: set_friend_add_request)。
    适用场景：从 `get_recent_notices_and_requests` 获取加好友事件 `flag` 后执行同意或拒绝。不适用与替代：若需审批加群或入群邀请请求，请改用 `set_group_add_request`。
    参数约束与行为：`flag` 必须来自真实的加好友请求事件；`remark` 仅在 `approve=True` 同意添加时作为新好友的初始备注名生效。
    :param flag: 加好友请求事件上报的唯一标识 flag 字符串
    :param approve: 为 True 时同意添加为好友，为 False 时拒绝请求，默认 True
    :param remark: 当 approve=True 时为新好友自动设置的备注名（可选）
    """
    return await client.call_api("set_friend_add_request", {
        "flag": str(flag),
        "approve": bool(approve),
        "remark": str(remark)
    })


@registry.register()
async def set_qq_profile(
    client: NapCatClient,
    nickname: Optional[str] = None,
    personal_note: Optional[str] = None,
    sex: Optional[int] = None
) -> dict[str, Any]:
    """
    修改当前登录 QQ 账号自身的个人资料，支持更新昵称、个人说明及性别 (NapCat 扩展接口: set_qq_profile)。
    适用场景：更新机器人账号自身的公开资料卡信息。不适用与替代：若仅需更新个性签名可使用 `set_self_longnick`；若需更换个人头像请改用 `set_qq_avatar`。
    参数约束与行为：未传入的可选字段将保持原值或按协议端默认处理；幂等设置操作，要求当前账号已在线。
    :param nickname: 新的个人 QQ 昵称（可选）
    :param personal_note: 新的个人说明或简介文本（可选）
    :param sex: 性别编码枚举：1（男）、2（女）、0（未知/保密）（可选）
    """
    params: dict[str, Any] = {}
    if nickname is not None:
        params["nickname"] = str(nickname)
    if personal_note is not None:
        params["personal_note"] = str(personal_note)
    if sex is not None:
        params["sex"] = int(sex)
    return await client.call_api("set_qq_profile", params)


@registry.register()
async def set_qq_avatar(
    client: NapCatClient,
    file: str
) -> dict[str, Any]:
    """
    更换当前登录 QQ 账号自身的个人头像图片 (NapCat 扩展接口: set_qq_avatar)。
    适用场景：更新当前登录账号的个人头像。不适用与替代：若需修改某个 QQ 群的群聊头像，请改用 `set_group_portrait`。
    参数约束与行为：`file` 支持本机已存在的图片绝对路径、HTTP/HTTPS 图片链接或 `base64://` 字符串；幂等覆盖操作，立即对所有好友与群聊生效。
    :param file: 新个人头像图片源，支持本地文件绝对路径、HTTP URL 或 base64:// 编码字符串
    """
    return await client.call_api("set_qq_avatar", {"file": str(file)})


@registry.register()
async def set_self_longnick(
    client: NapCatClient,
    long_nick: str
) -> dict[str, Any]:
    """
    设置或覆盖当前登录 QQ 账号的个性签名文本 (NapCat 扩展接口: set_self_longnick)。
    适用场景：单独更新当前账号展示在资料卡与列表中的个性签名。不适用与替代：若需同时修改个人昵称或性别，请改用 `set_qq_profile`；若需修改在线状态（如忙碌/隐身），请改用 `set_online_status`。
    行为与返回：幂等覆盖操作，新签名会直接替换原有签名；要求当前账号已登录在线。
    :param long_nick: 要设置的个性签名文本内容（传空字符串可清空签名）
    """
    return await client.call_api("set_self_longnick", {"longNick": str(long_nick)})


@registry.register()
async def set_online_status(
    client: NapCatClient,
    status: int = 10,
    ext_status: int = 0,
    battery_status: int = 0
) -> dict[str, Any]:
    """
    设置当前登录 QQ 账号的客户端在线状态及扩展状态图标 (NapCat 扩展接口: set_online_status)。
    适用场景：切换在线、离开、隐身、忙碌或请勿打扰等状态。不适用与替代：本工具仅改变状态显示图标，不会启动或停止后台服务进程；如需切换登录的 QQ 号或启停服务，请改用 `switch_qq_account` 或 `stop_napcat_service`。
    参数约束与行为：常用主状态码 `status` 为 `10`(在线)、`30`(离开)、`40`(隐身)、`50`(忙碌)、`60`(Q我吧)、`70`(请勿打扰)；幂等操作，要求账号已在线。
    :param status: 主在线状态码枚举：10(在线), 30(离开), 40(隐身), 50(忙碌), 60(Q我吧), 70(请勿打扰)，默认 10
    :param ext_status: 扩展自定义状态码（整数，0 表示无扩展状态），默认 0
    :param battery_status: 展示电量百分比状态（0~100 整数，默认 0）
    """
    return await client.call_api("set_online_status", {
        "status": int(status),
        "ext_status": int(ext_status),
        "battery_status": int(battery_status)
    })
