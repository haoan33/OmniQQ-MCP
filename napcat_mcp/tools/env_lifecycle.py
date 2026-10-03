"""
环境诊断、自动部署更新、多账号管理、扫码登录与服务启停控制工具集
"""
import os
import asyncio
from typing import Any, Optional
from . import registry
from ..client import NapCatClient
from ..deployer import (
    check_napcat_environment as _check_env,
    deploy_or_update_napcat as _deploy_napcat,
)
from ..config import (
    DEFAULT_HTTP_PORT,
    QR_CACHE_IMAGE,
    is_port_listening,
    set_current_account,
    get_available_accounts,
    get_current_account,
    kill_napcat_processes,
    start_qrcode_login_session,
)


@registry.register()
async def check_napcat_environment(client: NapCatClient) -> dict[str, Any]:
    """
    检查本地 NapCatQQ 运行环境、服务端口状态、已保存账号列表，并与 GitHub 官方最新 Release 版本进行对比。
    当不确定 NapCat 是否已部署、是否正在运行或是否有新版本可更新时，优先调用此工具。
    """
    live_ver = None
    if is_port_listening(DEFAULT_HTTP_PORT):
        res = await client.call_api("get_version_info", {}, timeout=5.0)
        if res.get("status") == "ok":
            live_ver = res.get("data")
    return await _check_env(live_version_info=live_ver)


@registry.register()
async def deploy_or_update_napcat(
    client: NapCatClient,
    action: str = "deploy",
    confirmed: bool = False,
    use_local_zip_if_available: bool = True,
    target_uin: Optional[str] = None
) -> dict[str, Any]:
    """
    一键自动部署或更新 NapCat 运行时环境 (支持从 GitHub 官方 Release 下载或使用本地离线包解压并自动配置 OneBot 端口)。
    ⚠️ 安全规范：首次调用必须保持 confirmed=False 以获取部署预览计划；向用户展示计划并获得明确授权后，再传入 confirmed=True 执行。
    :param action: 执行动作类型，'deploy' (部署安装) 或 'update' (更新升级)
    :param confirmed: 是否已获得用户明确许可 (False 时仅返回预览，True 时真正执行解压/下载)
    :param use_local_zip_if_available: 部署时若本地存在离线包是否优先使用
    :param target_uin: 要自动配置 OneBot 11 端口的 QQ 号 (留空则使用当前默认账号)
    """
    return await _deploy_napcat(
        action=action,
        confirmed=confirmed,
        use_local_zip_if_available=use_local_zip_if_available,
        target_uin=target_uin
    )


@registry.register()
async def list_qq_accounts(client: NapCatClient) -> dict[str, Any]:
    """
    查看本地沙箱中所有已保存登录凭证的 QQ 账号列表、当前默认激活账号以及当前正在线运行的账号信息。
    列表中的账号均可直接通过 switch_qq_account 免扫码快速切换上线。
    """
    current_default = get_current_account()
    available = get_available_accounts()
    online_account = None

    if is_port_listening(DEFAULT_HTTP_PORT):
        res = await client.call_api("get_login_info", {}, timeout=5.0)
        if res.get("status") == "ok":
            online_account = res.get("data")

    return {
        "status": "ok",
        "service_running": is_port_listening(DEFAULT_HTTP_PORT),
        "online_account": online_account,
        "default_account": current_default,
        "cached_accounts": available,
        "total_cached": len(available)
    }


@registry.register()
async def switch_qq_account(
    client: NapCatClient,
    uin: str,
    restart_immediately: bool = True,
    wait_seconds: int = 25
) -> dict[str, Any]:
    """
    切换当前使用的 QQ 账号（支持在多个已登录过的 QQ 号之间热切换）。
    会自动更新默认配置与 OneBot 11 端口配置；当 restart_immediately=True 时，会自动停止旧账号进程并以新账号重启上线。
    :param uin: 要切换的目标 QQ 号
    :param restart_immediately: 是否立即重启 NapCat 服务使新账号即刻上线，默认 True
    :param wait_seconds: 重启时等待端口就绪的最大秒数，默认 25
    """
    uin_clean = str(uin).strip()
    ok = set_current_account(uin_clean)
    if not ok:
        return {
            "status": "failed",
            "error": f"无效的 QQ 号格式或写入配置失败: {uin}"
        }

    if not restart_immediately:
        return {
            "status": "ok",
            "switched_to": uin_clean,
            "restarted": False,
            "available_accounts": get_available_accounts(),
            "message": f"已将默认配置切换为 {uin_clean}（尚未重启后台服务，下次启动生效）。"
        }

    # 停止旧进程并以新账号启动
    killed = await asyncio.to_thread(kill_napcat_processes)
    start_res = await client.start_napcat_process(uin=uin_clean, wait_seconds=wait_seconds)
    client.start_background_ws()

    online_info = None
    if is_port_listening(DEFAULT_HTTP_PORT):
        login_res = await client.call_api("get_login_info", {}, timeout=5.0)
        if login_res.get("status") == "ok":
            online_info = login_res.get("data")

    return {
        "status": "ok" if start_res.get("status") in ("started", "already_running") else start_res.get("status"),
        "switched_to": uin_clean,
        "stopped_old_processes": killed,
        "start_result": start_res,
        "online_account": online_info,
        "available_accounts": get_available_accounts(),
        "message": f"已成功切换至 QQ 账号 {uin_clean} 并重新拉起服务！"
    }


@registry.register()
async def login_new_qq_by_qrcode(
    client: NapCatClient,
    open_image: bool = True,
    wait_scan_seconds: int = 45
) -> dict[str, Any]:
    """
    启动新 QQ 账号扫码登录流程（绑定新 QQ 号或当旧账号凭证过期需要重新扫码时使用）。
    执行流程：
    1. 自动停止当前后台 NapCat 进程并清空自动登录配置；
    2. 启动扫码沙箱生成高清二维码图片 (`qrcode.png`)，并在屏幕上自动弹出该二维码供用户用手机 QQ 扫码；
    3. 等待用户扫码成功后，自动为新 QQ 号生成 OneBot 11 (3000/3001) 端口配置，并自动转为后台常驻模式上线。
    :param open_image: 是否自动在电脑屏幕上用图片查看器弹出二维码图片，默认 True
    :param wait_scan_seconds: 等待用户手机扫码的最大秒数，默认 45 秒
    """
    scan_res = await asyncio.to_thread(
        start_qrcode_login_session,
        open_image=open_image,
        wait_scan_seconds=wait_scan_seconds
    )

    if scan_res.get("status") == "logged_in_and_configured":
        new_uin = scan_res.get("new_uin")
        start_res = await client.start_napcat_process(uin=new_uin, wait_seconds=25)
        client.start_background_ws()
        scan_res["service_start_result"] = start_res
        if is_port_listening(DEFAULT_HTTP_PORT):
            info = await client.call_api("get_login_info", {}, timeout=5.0)
            if info.get("status") == "ok":
                scan_res["online_account"] = info.get("data")

    return scan_res


@registry.register()
async def get_login_qrcode_image(
    client: NapCatClient,
    open_image: bool = True
) -> dict[str, Any]:
    """
    查看本地最新的 NapCat 登录二维码图片路径 (`qrcode.png`)，并可选在电脑屏幕上直接打开展示该二维码。
    :param open_image: 若二维码文件存在，是否立即在屏幕上打开图片查看器，默认 True
    """
    exists = os.path.exists(QR_CACHE_IMAGE)
    opened = False
    if exists and open_image and os.name == "nt":
        try:
            os.startfile(QR_CACHE_IMAGE)
            opened = True
        except Exception:
            pass

    return {
        "status": "ok" if exists else "not_found",
        "qrcode_exists": exists,
        "qrcode_path": QR_CACHE_IMAGE if exists else None,
        "opened_on_screen": opened,
        "message": (
            f"二维码文件位于 {QR_CACHE_IMAGE}" + ("，已在屏幕弹出显示。" if opened else "。")
            if exists
            else "当前没有缓存的二维码图片，请调用 `login_new_qq_by_qrcode` 生成新二维码。"
        )
    }


@registry.register()
async def start_napcat_service(
    client: NapCatClient,
    uin: Optional[str] = None,
    wait_seconds: int = 25
) -> dict[str, Any]:
    """
    启动本地 NapCat 后台服务进程并等待端口 (3000/3001) 就绪。
    若服务已在运行则直接返回就绪状态。
    :param uin: 指定要登录启动的 QQ 号 (留空则使用默认激活账号)
    :param wait_seconds: 等待端口监听的最大秒数
    """
    res = await client.start_napcat_process(uin=uin, wait_seconds=wait_seconds)
    client.start_background_ws()
    return res


@registry.register()
async def stop_napcat_service(client: NapCatClient) -> dict[str, Any]:
    """
    安全停止当前后台运行的 NapCat 沙箱进程 (仅精准终止 napcat_runtime 下的进程，不影响系统其他 Node 服务)。
    """
    killed = await asyncio.to_thread(kill_napcat_processes)
    return {
        "status": "ok",
        "stopped_processes": killed,
        "port_listening": is_port_listening(DEFAULT_HTTP_PORT),
        "message": "NapCat 后台服务已停止。"
    }


@registry.register()
async def restart_napcat_service(
    client: NapCatClient,
    uin: Optional[str] = None,
    wait_seconds: int = 25
) -> dict[str, Any]:
    """
    强制重启本地 NapCat 后台服务进程（可指定要登录的 QQ 号）。
    :param uin: 指定重启登录的 QQ 号 (可选，留空则使用当前默认账号)
    :param wait_seconds: 等待端口监听就绪的秒数，默认 25
    """
    target_uin = str(uin).strip() if uin else get_current_account()
    if target_uin:
        set_current_account(target_uin)
    killed = await asyncio.to_thread(kill_napcat_processes)
    start_res = await client.start_napcat_process(uin=target_uin, wait_seconds=wait_seconds)
    client.start_background_ws()
    return {
        "status": start_res.get("status"),
        "uin": target_uin,
        "stopped_old_processes": killed,
        "start_result": start_res
    }
