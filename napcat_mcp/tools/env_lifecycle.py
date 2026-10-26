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
    export_qrcode_to_desktop,
)


@registry.register()
async def check_napcat_environment(client: NapCatClient) -> dict[str, Any]:
    """
    检查本地 NapCatQQ 运行时安装状态、OneBot 端口 (3000/3001) 监听情况、本地缓存账号列表，并请求 GitHub Release API 对比官方最新版本。
    适用场景：首次连接、排查接口调用失败或判断是否有新版本可升级时优先调用。不适用与替代：若仅需读取当前在线 QQ 的 user_id 与昵称，请改用轻量级的 `get_login_info`（无需请求 GitHub，速度更快）。
    行为与返回：纯只读无副作用操作（包含一次约 5 秒超时的外部 GitHub 版本探测）；返回包含 `installed`、`port_listening`、`cached_accounts`、`latest_release` 及 `needs_update` 诊断结论的字典，失败时在相应字段返回原因。
    """
    if not client.uses_local_runtime():
        probe = await client.call_api('get_version_info', {}, timeout=5.0)
        return {'status': 'ready' if probe.get('status') == 'ok' and probe.get('retcode', 0) == 0 else 'failed',
                'mode': 'external', 'http_url': client.http_url, 'probe': probe}
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
    自动下载、解压并部署或升级本地 Windows NapCatQQ 运行时环境，同时自动写入 OneBot 11 (3000/3001) 端口配置。
    适用场景：当 `check_napcat_environment` 显示未安装（选 `action='deploy'`）或存在新版本需升级（选 `action='update'`）时使用。不适用与替代：若运行时已安装且仅需启动、重启或切换账号，请改用 `switch_qq_account` 或 `call_napcat_api`，切勿重复重装。
    参数约束与两阶段门禁：强制采用两阶段确认锁——首次调用必须传 `confirmed=False` 获取只读预览计划；向用户展示计划并获得明确许可后，再传 `confirmed=True` 真正执行文件覆写。`target_uin` 若指定须为 5~11 位纯数字 QQ 号字符串。
    行为与副作用：`confirmed=True` 时会终止现有本地 NapCat 进程并覆写运行时目录（升级失败或健康检查不通过时自动回滚至旧版本备份）；仅支持本地 Windows 模式，外部远程 OneBot URL 调用将直接返回 `status='failed'`。
    :param action: 执行模式，枚举值 'deploy'（全新部署安装）或 'update'（备份旧版并升级，失败自动回滚），默认 'deploy'
    :param confirmed: 两阶段安全门禁开关；False 时仅返回只读部署预览计划，True 时执行真实下载解压与进程重启
    :param use_local_zip_if_available: 为 True 时优先解压本地已缓存的离线 Release 压缩包以避免重复网络下载，默认 True
    :param target_uin: 部署后自动绑定 OneBot 端口的 5~11 位纯数字 QQ 号字符串；留空则沿用当前默认账号
    """
    if not client.uses_local_runtime():
        return {'status': 'failed', 'error': '外部 OneBot URL 不能部署本地 NapCat'}
    return await _deploy_napcat(
        action=action,
        confirmed=confirmed,
        use_local_zip_if_available=use_local_zip_if_available,
        target_uin=target_uin
    )


@registry.register()
async def list_qq_accounts(client: NapCatClient) -> dict[str, Any]:
    """
    读取本地沙箱中所有已缓存登录凭证的 QQ 账号列表、当前默认激活账号及当前在线账号详情。
    适用场景：在切换账号前查询有哪些历史已登录 QQ 号可供免扫码切换。不适用与替代：若仅需确认当前在线账号的 user_id 和昵称，请改用 `get_login_info`；若需同时检查运行时安装与 GitHub 版本更新，请改用 `check_napcat_environment`。
    行为与返回：纯只读无副作用操作；返回 `service_running`、`online_account`、`default_account` 与 `cached_accounts` 数组。列表中的账号可直接传给 `switch_qq_account` 热切换。
    """
    if not client.uses_local_runtime():
        probe = await client.call_api('get_login_info', {}, timeout=5.0)
        return {'status': 'ok' if probe.get('status') == 'ok' and probe.get('retcode', 0) == 0 else 'failed',
                'mode': 'external', 'online_account': probe.get('data'),
                'default_account': None, 'cached_accounts': [], 'total_cached': 0}
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
    在本地已保存登录凭证的多个 QQ 账号之间免扫码热切换，自动更新默认账号、OneBot 端口配置及按账号隔离的消息缓存池。
    适用场景：目标 QQ 号此前已在本地扫码登录过（可通过 `check_napcat_environment` 的 `cached_accounts` 查看），需快速切换上线时调用。不适用与替代：若目标是一个从未登录过的新 QQ 号或登录凭证已失效，请勿使用本工具，应改用 `login_new_qq_by_qrcode` 扫码登录。
    参数约束与交互：`uin` 必须为 5~11 位纯数字字符串；当 `restart_immediately=True` 时会立即终止旧账号进程并等待最多 `wait_seconds` 秒直至新账号端口就绪，为 `False` 时仅修改配置待下次启动生效。
    行为与返回：幂等配置变更与进程重启操作（仅限本地运行时，外部 URL 返回失败）；返回 `status`、`switched_to`、`online_account` 与 `available_accounts`。
    :param uin: 要切换上线的目标 QQ 号（5~11 位纯数字字符串，须已存在于本地缓存账号列表中）
    :param restart_immediately: 为 True 时立即终止旧进程并以新账号重启上线；为 False 时仅更新默认配置不中断当前进程，默认 True
    :param wait_seconds: 当 restart_immediately=True 时等待新账号 OneBot 端口监听就绪的超时秒数（建议 15~60），默认 25
    """
    if not client.uses_local_runtime():
        return {'status': 'failed', 'error': '外部 OneBot URL 不支持管理本地 QQ 账号'}
    uin_clean = str(uin).strip()
    ok = set_current_account(uin_clean)
    if not ok:
        return {
            "status": "failed",
            "error": f"无效的 QQ 号格式或写入配置失败: {uin}"
        }
    client.buffer.select_account(uin_clean)

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
        "login_required": bool(start_res.get("login_required")),
        "desktop_qrcode_path": start_res.get("desktop_qrcode_path"),
        "online_account": online_info,
        "available_accounts": get_available_accounts(),
        "message": (
            start_res.get("message")
            if start_res.get("login_required")
            else f"账号 {uin_clean} 的服务启动状态：{start_res.get('status')}。"
        )
    }


@registry.register()
async def login_new_qq_by_qrcode(
    client: NapCatClient,
    open_image: bool = True,
    wait_scan_seconds: int = 45
) -> dict[str, Any]:
    """
    启动全新 QQ 账号的二维码扫码登录流程，生成高清二维码图片 (`qrcode.png`) 等待手机 QQ 扫码，成功后自动写入 OneBot 11 端口配置并转为后台常驻运行。
    适用场景：首次绑定新 QQ 号，或已有账号登录态过期需要重新手机扫码授权时调用。不适用与替代：若目标 QQ 号已在本地缓存列表且凭证有效，请勿重新扫码，应改用 `switch_qq_account` 免扫码秒级切换。
    参数约束与交互：`open_image=True` 会在本机 Windows 桌面自动弹出二维码查看器；`wait_scan_seconds` 控制阻塞等待用户手机确认的最大秒数（超时未扫返回 `status='scan_timed_out'`）。
    行为与副作用：会主动停止当前正在运行的本地 NapCat 进程并重置自动登录配置；前置要求本地 NapCat 已部署（未部署请先调用 `deploy_or_update_napcat`），成功时返回 `status='logged_in_and_configured'`、`new_uin` 及 `online_account`。
    :param open_image: 生成二维码后是否立即调用系统默认图片查看器在桌面弹出显示，默认 True
    :param wait_scan_seconds: 阻塞等待用户使用手机 QQ 扫描并确认登录的最大超时秒数（建议 30~120），默认 45
    """
    if not client.uses_local_runtime():
        return {'status': 'failed', 'error': '外部 OneBot URL 不支持本地扫码登录'}
    scan_res = await asyncio.to_thread(
        start_qrcode_login_session,
        open_image=open_image,
        wait_scan_seconds=wait_scan_seconds
    )

    if scan_res.get("status") == "logged_in_and_configured":
        new_uin = scan_res.get("new_uin")
        client.buffer.select_account(new_uin)
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
    读取本地缓存的最新 NapCat 登录二维码图片路径 (`qrcode.png`)，并可选在桌面弹出展示该图片。
    适用场景：当 `login_new_qq_by_qrcode` 已经生成二维码但用户关闭了图片窗口需要重新查看时调用。不适用与替代：本工具不会启动扫码进程或刷新过期二维码；如需发起新的扫码会话，请改用 `login_new_qq_by_qrcode`。
    行为与返回：只读查询本地文件状态（`open_image=True` 时触发本地图片查看器）；文件存在返回 `status='ok'` 与 `qrcode_path`，不存在返回 `status='not_found'`。
    :param open_image: 若本地二维码图片文件存在，是否在 Windows 桌面立即打开图片查看器展示，默认 True
    """
    if not client.uses_local_runtime():
        return {'status': 'not_found', 'error': '外部 OneBot URL 没有本地二维码缓存'}
    exists = os.path.exists(QR_CACHE_IMAGE)
    desktop_qr = export_qrcode_to_desktop(QR_CACHE_IMAGE) if exists else None
    target_qr = desktop_qr or (QR_CACHE_IMAGE if exists else None)
    opened = False
    if exists and open_image and os.name == "nt":
        try:
            os.startfile(target_qr)
            opened = True
        except Exception:
            pass

    return {
        "status": "ok" if exists else "not_found",
        "qrcode_exists": exists,
        "qrcode_path": target_qr,
        "desktop_qrcode_path": desktop_qr,
        "opened_on_screen": opened,
        "message": (
            f"登录二维码已保存到桌面：{target_qr}，请打开桌面上的二维码图片进行扫描登录" + ("（已在屏幕弹出显示）。" if opened else "。")
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
    启动本地 NapCatQQ 后台服务进程并等待 OneBot (3000/3001) 端口就绪，同时挂载后台 WebSocket 事件监听。
    适用场景：当本地服务处于停止状态、需要以默认或指定已缓存账号拉起后台进程时调用（启动前会自动检查并结束冲突的独立 QQ.exe 进程；若检测到需要扫码登录，会自动把登录二维码放到桌面并提示用户打开扫描）。不适用与替代：若服务已在运行且需切换其他已缓存账号，请改用 `switch_qq_account`。
    行为与返回：幂等操作——启动前先结束冲突的独立 QQ.exe 进程；若端口已在监听则返回 `status='already_running'`；新启动成功返回 `status='started'`；若需扫码登录则将二维码导出至桌面并返回 `login_required=True` 及 `desktop_qrcode_path`。
    :param uin: 指定要自动登录的 5~11 位纯数字 QQ 号字符串；留空则使用本地配置中的当前默认账号
    :param wait_seconds: 启动进程后轮询等待 OneBot HTTP 端口监听就绪的最大秒数，默认 25
    """
    res = await client.start_napcat_process(uin=uin, wait_seconds=wait_seconds)
    client.start_background_ws()
    return res


@registry.register()
async def stop_napcat_service(client: NapCatClient) -> dict[str, Any]:
    """
    安全终止本地后台运行的 NapCatQQ 沙箱进程（严格校验进程可执行文件与入口路径，绝不误杀系统其他 Node.js 进程）。
    适用场景：需要彻底下线当前 QQ 机器人、释放本地 3000/3001 端口或维护运行时目录时调用。不适用与替代：若希望重启服务或切换其他已缓存 QQ 号上线，请直接改用 `switch_qq_account`。
    行为与副作用：破坏性但幂等的进程终止操作——调用后当前 QQ 账号立即离线且实时消息监听中断，直至重新调用 `switch_qq_account`、`login_new_qq_by_qrcode` 或任意触发自动自愈的核心工具；返回被终止的 PID 列表 `stopped_processes` 与端口状态。
    """
    if not client.uses_local_runtime():
        return {'status': 'failed', 'error': '外部 OneBot URL 不能停止本地 NapCat'}
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
    强制终止现有本地 NapCatQQ 进程并重新拉起后台服务，支持在重启时指定目标登录 QQ 号。
    适用场景：当 NapCat 服务出现连接僵死、配置变更需重启生效时调用。不适用与替代：若是为了在多个已登录账号间正常切换，请优先使用语义更清晰的 `switch_qq_account`。
    行为与副作用：会短暂中断现有连接并终止旧进程，随后等待最多 `wait_seconds` 秒恢复端口监听与 WebSocket 实时事件订阅；返回 `stopped_old_processes` 及重启结果 `start_result`。
    :param uin: 重启后指定登录的 5~11 位纯数字 QQ 号字符串；留空则沿用当前默认激活账号
    :param wait_seconds: 重启后等待 OneBot 端口监听就绪的最大超时秒数，默认 25
    """
    if not client.uses_local_runtime():
        return {'status': 'failed', 'error': '外部 OneBot URL 不能重启本地 NapCat'}
    target_uin = str(uin).strip() if uin else get_current_account()
    if target_uin:
        if not set_current_account(target_uin):
            return {'status': 'failed', 'error': '账号配置写入失败，未重启 NapCat'}
        client.buffer.select_account(target_uin)
    killed = await asyncio.to_thread(kill_napcat_processes)
    start_res = await client.start_napcat_process(uin=target_uin, wait_seconds=wait_seconds)
    client.start_background_ws()
    return {
        "status": start_res.get("status"),
        "uin": target_uin,
        "stopped_old_processes": killed,
        "start_result": start_res
    }
