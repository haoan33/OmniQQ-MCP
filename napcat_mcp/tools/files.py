"""
文件与富媒体控制工具集 (私聊文件、群文件上传/删除/浏览/获取下载链接、图片OCR、文件下载)
"""
from typing import Any, Optional
from . import registry
from ..client import NapCatClient


@registry.register()
async def upload_private_file(
    client: NapCatClient,
    user_id: int,
    file_path: str,
    file_name: str
) -> dict[str, Any]:
    """
    将本机磁盘上的文件作为私聊附件发送给指定 QQ 好友 (NapCat OneBot 11: upload_private_file)。
    适用场景：向个人 QQ 好友交付文档、表格、PDF 或压缩包等本地文件。不适用与替代：若需将文件上传至 QQ 群共享空间，请改用 `upload_group_file`；若仅需发送纯文本或图片消息段，请改用 `send_private_msg`。
    参数约束与交互：`file_path` 必须为当前机器上已存在且可读的本地绝对路径（如 `D:/Desktop/report.xlsx`）；`file_name` 应包含正确的文件扩展名以便接收方客户端识别打开。
    行为与返回：非幂等外部文件传输操作（默认超时 120 秒以支持大文件上传）；前置要求当前账号已在线且目标为好友，成功返回 `status='ok'`，若本地文件不存在、超出大小限制或非好友则返回非 0 `retcode`。
    :param user_id: 接收方好友的 QQ 号（5~11 位正整数）
    :param file_path: 待发送本地文件的完整绝对路径（文件必须真实存在且可读）
    :param file_name: 对方在私聊窗口中看到的显示文件名（须含扩展名，如 'report.xlsx'）
    """
    return await client.call_api(
        "upload_private_file",
        {
            "user_id": int(user_id),
            "file": str(file_path),
            "name": str(file_name)
        },
        timeout=120.0
    )


@registry.register()
async def upload_group_file(
    client: NapCatClient,
    group_id: int,
    file_path: str,
    file_name: str,
    folder: Optional[str] = None
) -> dict[str, Any]:
    """
    将本机磁盘上的文件上传至指定 QQ 群的群文件共享空间 (NapCat OneBot 11: upload_group_file)。
    适用场景：向 QQ 群发布共享资料、汇总表或通知附件。不适用与替代：若需将文件单独私发给某个好友，请改用 `upload_private_file`；若仅需在群内发送文字通知，请改用 `send_group_msg`。
    参数约束与交互：`file_path` 必须为本机已存在的绝对路径；省略 `folder` 时默认上传至群文件根目录，若指定 `folder` 则须传入通过 `call_napcat_api(action='get_group_root_files')` 查询到的有效群文件夹 ID。
    行为与返回：非幂等群文件创建操作（默认超时 120 秒，同名文件通常会在群文件列表中产生新条目）；前置要求当前账号已加入目标群且群文件空间未满、具备上传权限，成功返回 `status='ok'`。
    :param group_id: 目标 QQ 群号（正整数，须为已加入的群聊）
    :param file_path: 待上传本地文件的完整绝对路径（文件必须真实存在且可读）
    :param file_name: 在群文件列表中展示的文件名称（须含扩展名）
    :param folder: 目标群文件夹 ID（可选；留空则上传至群文件根目录）
    """
    params: dict[str, Any] = {
        "group_id": int(group_id),
        "file": str(file_path),
        "name": str(file_name)
    }
    if folder:
        params["folder"] = str(folder)
    return await client.call_api("upload_group_file", params, timeout=120.0)


@registry.register()
async def delete_group_file(
    client: NapCatClient,
    group_id: int,
    file_id: str,
    busid: int = 102
) -> dict[str, Any]:
    """
    从指定 QQ 群的群文件空间中永久删除单个群文件 (NapCat OneBot 11: delete_group_file)。
    适用场景：清理过期或误传的群文件。不适用与替代：若需删除整个群文件夹，请改用 `delete_group_folder`；若需撤回群聊窗口中的普通消息，请改用 `delete_msg`。
    参数约束与行为：`file_id` 与 `busid` 可从 `get_group_root_files`、`get_group_files_by_folder` 或群上传事件中获取；此操作为不可逆的破坏性删除，要求当前账号为文件上传者本人或具备该群管理员/群主权限。
    :param group_id: 目标 QQ 群号（正整数）
    :param file_id: 要删除的群文件唯一标识 ID（字符串）
    :param busid: 群文件类型总线 ID（整数，从文件列表或事件中获取，默认 102）
    """
    return await client.call_api("delete_group_file", {
        "group_id": int(group_id),
        "file_id": str(file_id),
        "busid": int(busid)
    })


@registry.register()
async def delete_group_folder(
    client: NapCatClient,
    group_id: int,
    folder_id: str
) -> dict[str, Any]:
    """
    从指定 QQ 群的群文件空间中永久删除指定的群文件夹 (NapCat OneBot 11: delete_group_folder)。
    适用场景：删除不再需要的群文件目录。不适用与替代：若仅需删除单个群文件而保留文件夹，请改用 `delete_group_file`。
    参数约束与行为：`folder_id` 可通过 `get_group_root_files` 获取；此操作为不可逆的破坏性操作（会一并移除目录结构），前置要求当前账号具备该群管理员或群主权限。
    :param group_id: 目标 QQ 群号（正整数）
    :param folder_id: 要删除的群文件夹 ID（字符串）
    """
    return await client.call_api("delete_group_folder", {
        "group_id": int(group_id),
        "folder_id": str(folder_id)
    })


@registry.register()
async def get_group_root_files(
    client: NapCatClient,
    group_id: int
) -> dict[str, Any]:
    """
    获取指定 QQ 群文件根目录下的全部文件列表与一级文件夹列表 (NapCat OneBot 11: get_group_root_files)。
    适用场景：浏览群文件根目录以查找 `file_id`、`busid` 或 `folder_id`。不适用与替代：若需查看某个子文件夹内部的文件，请先用本工具拿到 `folder_id` 后改用 `get_group_files_by_folder`；若已知 `file_id` 需获取下载链接，请改用 `get_group_file_url`。
    行为与返回：纯只读无副作用查询；成功返回 `data.files` 与 `data.folders` 数组。
    :param group_id: 目标 QQ 群号（正整数）
    """
    return await client.call_api("get_group_root_files", {"group_id": int(group_id)})


@registry.register()
async def get_group_files_by_folder(
    client: NapCatClient,
    group_id: int,
    folder_id: str
) -> dict[str, Any]:
    """
    获取指定 QQ 群特定子文件夹内的全部文件与下级文件夹列表 (NapCat OneBot 11: get_group_files_by_folder)。
    适用场景：已知群文件夹 `folder_id`，需检索该目录内的文件。不适用与替代：若需浏览群文件根目录，请改用 `get_group_root_files`。
    行为与返回：纯只读查询；返回 `data.files` 与 `data.folders`，文件夹不存在时返回非 0 `retcode`。
    :param group_id: 目标 QQ 群号（正整数）
    :param folder_id: 目标群文件夹 ID（可从 `get_group_root_files` 返回的 `folders` 列表中获取）
    """
    return await client.call_api("get_group_files_by_folder", {
        "group_id": int(group_id),
        "folder_id": str(folder_id)
    })


@registry.register()
async def get_group_file_url(
    client: NapCatClient,
    group_id: int,
    file_id: str,
    busid: int = 102
) -> dict[str, Any]:
    """
    根据群号与 `file_id` 解析指定 QQ 群文件的直接 HTTP 下载链接 (NapCat OneBot 11: get_group_file_url)。
    适用场景：收到群文件通知或从群文件列表中找到目标文件后，获取其下载 URL 以便随后调用 `download_file` 保存到本地。不适用与替代：若目标文件来自好友私聊而非群聊，请改用 `get_private_file_url`。
    行为与返回：纯只读查询；成功在 `data.url` 中返回临时有效的 HTTP 下载地址。
    :param group_id: 文件所属的 QQ 群号（正整数）
    :param file_id: 群文件的唯一标识 ID（字符串）
    :param busid: 群文件 busid 类型标识（整数，默认 102）
    """
    return await client.call_api("get_group_file_url", {
        "group_id": int(group_id),
        "file_id": str(file_id),
        "busid": int(busid)
    })


@registry.register()
async def get_private_file_url(
    client: NapCatClient,
    file_id: str
) -> dict[str, Any]:
    """
    根据私聊文件 `file_id` 获取直接 HTTP 下载链接或本地缓存路径 (NapCat 扩展接口: get_private_file_url)。
    适用场景：处理好友私聊发来的文件附件时，解析其下载 URL 以便传给 `download_file` 下载。不适用与替代：若文件来自 QQ 群共享或群聊，请改用 `get_group_file_url`。
    行为与返回：纯只读查询；成功返回 `data.url`。
    :param file_id: 私聊文件消息段或事件中提供的 `file_id` 字符串
    """
    return await client.call_api("get_private_file_url", {"file_id": str(file_id)})


@registry.register()
async def get_group_file_system_info(
    client: NapCatClient,
    group_id: int
) -> dict[str, Any]:
    """
    查询指定 QQ 群文件系统的容量配额与使用统计，包括总空间、已用空间及文件数量上限 (NapCat OneBot 11: get_group_file_system_info)。
    适用场景：在上传大型群文件前检查群空间余量。不适用与替代：若需列出具体有哪些群文件，请改用 `get_group_root_files`。
    行为与返回：纯只读无副作用操作；返回 `file_count`、`limit_count`、`used_space` 与 `total_space`（字节）。
    :param group_id: 目标 QQ 群号（正整数）
    """
    return await client.call_api("get_group_file_system_info", {"group_id": int(group_id)})


@registry.register()
async def ocr_image(
    client: NapCatClient,
    image: str
) -> dict[str, Any]:
    """
    调用 QQ 客户端内置 OCR 引擎识别图片中的文字内容及坐标位置 (NapCat OneBot 11: ocr_image)。
    适用场景：需要对收到的聊天图片、截图或本地图片提取文本内容时调用。不适用与替代：若仅需将网络文件下载到本地磁盘而不做文字识别，请改用 `download_file`。
    参数约束与行为：`image` 支持图片文件 ID、本地绝对路径或 HTTP URL；纯只读无副作用操作，成功返回包含识别文本段落列表 `texts` 的 `data` 对象。
    :param image: 待识别的图片标识，支持消息段中的图片 file ID、本机绝对路径或 HTTP/HTTPS 图片链接
    """
    return await client.call_api("ocr_image", {"image": str(image)})


@registry.register()
async def download_file(
    client: NapCatClient,
    url: str,
    thread_count: int = 3,
    headers: Optional[list] = None
) -> dict[str, Any]:
    """
    通过 NapCat 内置下载器将指定 HTTP/HTTPS URL 的文件下载到本地缓存目录并返回本地绝对路径 (OneBot 11: download_file)。
    适用场景：配合 `get_group_file_url` 或 `get_private_file_url` 获取下载链接后，将远程附件拉取到本地以便读取或处理。不适用与替代：若需把本地文件发送给好友或上传到群，请改用 `upload_private_file` 或 `upload_group_file`。
    参数约束与行为：`headers` 若传入须为 `"Key=Value"` 格式的字符串数组；会在本地缓存目录写入文件（默认超时 120 秒），成功在 `data.file` 中返回下载后的本地绝对路径。
    :param url: 要下载的文件完整 HTTP 或 HTTPS URL（可由 `get_group_file_url` / `get_private_file_url` 获得）
    :param thread_count: 并发下载线程数（正整数，默认 3）
    :param headers: 自定义 HTTP 请求头字符串数组，每项格式为 'HeaderName=Value'（可选）
    """
    params: dict[str, Any] = {
        "url": str(url),
        "thread_count": int(thread_count)
    }
    if headers:
        params["headers"] = headers
    return await client.call_api("download_file", params, timeout=120.0)
