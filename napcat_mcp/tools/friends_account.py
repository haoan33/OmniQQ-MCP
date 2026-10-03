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
    获取当前登录 QQ 的全部好友列表 (包括 user_id、nickname、remark 等) (OneBot 11: get_friend_list)。
    :param no_cache: 是否强制不使用缓存刷新列表，默认 False
    """
    return await client.call_api("get_friend_list", {"no_cache": bool(no_cache)})


@registry.register()
async def get_friends_with_category(
    client: NapCatClient
) -> dict[str, Any]:
    """
    获取按好友分组归类的好友列表 (NapCat 扩展接口: get_friends_with_category)。
    """
    return await client.call_api("get_friends_with_category", {})


@registry.register()
async def get_stranger_info(
    client: NapCatClient,
    user_id: int,
    no_cache: bool = False
) -> dict[str, Any]:
    """
    获取指定 QQ 用户（好友或陌生人）的公开个人资料 (昵称、性别、年龄、等级、个性签名等) (OneBot 11: get_stranger_info)。
    :param user_id: 目标 QQ 号
    :param no_cache: 是否不使用缓存
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
    删除指定 QQ 好友 (OneBot 11: delete_friend)。
    :param user_id: 要删除的好友 QQ 号
    """
    return await client.call_api("delete_friend", {"user_id": int(user_id)})


@registry.register()
async def set_friend_remark(
    client: NapCatClient,
    user_id: int,
    remark: str
) -> dict[str, Any]:
    """
    设置或修改指定好友的备注名 (NapCat 扩展接口: set_friend_remark)。
    :param user_id: 好友 QQ 号
    :param remark: 新备注名称
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
    审批处理他人发来的加好友请求 (OneBot 11: set_friend_add_request)。
    :param flag: 加好友请求事件上报的 flag 标识
    :param approve: True 同意添加，False 拒绝添加
    :param remark: 同意后的好友备注名 (可选)
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
    修改当前登录 QQ 账号的个人资料 (NapCat 扩展接口: set_qq_profile)。
    :param nickname: 新昵称 (可选)
    :param personal_note: 个人说明 / 个性签名 (可选)
    :param sex: 性别代码 (1男, 2女, 0未知，可选)
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
    修改当前登录 QQ 账号的头像 (NapCat 扩展接口: set_qq_avatar)。
    :param file: 图片本地绝对路径、HTTP URL 或 base64:// 字符串
    """
    return await client.call_api("set_qq_avatar", {"file": str(file)})


@registry.register()
async def set_self_longnick(
    client: NapCatClient,
    long_nick: str
) -> dict[str, Any]:
    """
    设置当前登录 QQ 的个性签名 (NapCat 扩展接口: set_self_longnick)。
    :param long_nick: 个性签名内容
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
    设置当前登录 QQ 的在线状态 (NapCat 扩展接口: set_online_status)。
    常用状态码: status=10(在线), 30(离开), 40(隐身), 50(忙碌), 60(Q我吧), 70(请勿打扰)。
    :param status: 主状态码 (默认 10 在线)
    :param ext_status: 扩展状态码 (默认 0)
    :param battery_status: 电量状态 (默认 0)
    """
    return await client.call_api("set_online_status", {
        "status": int(status),
        "ext_status": int(ext_status),
        "battery_status": int(battery_status)
    })
