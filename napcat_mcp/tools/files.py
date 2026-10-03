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
    向指定好友发送本地文件附件 (NapCat OneBot 11: upload_private_file)。
    :param user_id: 接收方好友 QQ 号
    :param file_path: 本地文件的绝对路径 (如 'D:/Desktop/report.xlsx')
    :param file_name: 对方看到的显示文件名 (如 'report.xlsx')
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
    向指定 QQ 群上传群文件 (NapCat OneBot 11: upload_group_file)。
    :param group_id: 目标 QQ 群号
    :param file_path: 本地文件的绝对路径
    :param file_name: 群文件中显示的文件名
    :param folder: 目标群文件夹 ID (可选，不填则上传至群文件根目录)
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
    删除指定的 QQ 群文件 (NapCat OneBot 11: delete_group_file)。
    :param group_id: 群号
    :param file_id: 群文件 ID
    :param busid: 文件类型 busid，默认 102
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
    删除指定的 QQ 群文件夹 (NapCat OneBot 11: delete_group_folder)。
    :param group_id: 群号
    :param folder_id: 群文件夹 ID
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
    获取 QQ 群文件根目录下的所有文件与文件夹列表 (NapCat OneBot 11: get_group_root_files)。
    :param group_id: 群号
    """
    return await client.call_api("get_group_root_files", {"group_id": int(group_id)})


@registry.register()
async def get_group_files_by_folder(
    client: NapCatClient,
    group_id: int,
    folder_id: str
) -> dict[str, Any]:
    """
    获取 QQ 群指定文件夹内的文件与子文件夹列表 (NapCat OneBot 11: get_group_files_by_folder)。
    :param group_id: 群号
    :param folder_id: 文件夹 ID
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
    获取指定群文件的直接 HTTP 下载链接 (NapCat OneBot 11: get_group_file_url)。
    :param group_id: 群号
    :param file_id: 群文件 ID
    :param busid: 文件 busid (可选，默认 102)
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
    获取私聊文件的直接下载链接或本地缓存路径 (NapCat 扩展接口: get_private_file_url)。
    :param file_id: 私聊文件 file_id
    """
    return await client.call_api("get_private_file_url", {"file_id": str(file_id)})


@registry.register()
async def get_group_file_system_info(
    client: NapCatClient,
    group_id: int
) -> dict[str, Any]:
    """
    获取 QQ 群文件系统的空间使用情况 (总空间、已用空间、文件数上限等) (NapCat OneBot 11: get_group_file_system_info)。
    :param group_id: 群号
    """
    return await client.call_api("get_group_file_system_info", {"group_id": int(group_id)})


@registry.register()
async def ocr_image(
    client: NapCatClient,
    image: str
) -> dict[str, Any]:
    """
    调用 QQ 内置 OCR 引擎识别图片中的文字 (NapCat OneBot 11: ocr_image)。
    :param image: 图片文件 ID、本地绝对路径或 HTTP URL
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
    通过 NapCat 下载网络文件到本地缓存目录并返回本地绝对路径 (OneBot 11: download_file)。
    :param url: 文件下载 URL
    :param thread_count: 下载线程数，默认 3
    :param headers: 自定义请求头列表 (如 ["User-Agent=xxx"])
    """
    params: dict[str, Any] = {
        "url": str(url),
        "thread_count": int(thread_count)
    }
    if headers:
        params["headers"] = headers
    return await client.call_api("download_file", params, timeout=120.0)
