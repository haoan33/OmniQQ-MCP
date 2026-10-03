"""
NapCat 环境自检、版本比对与自动化部署/更新管理器
支持检测本地沙箱、远程查询 GitHub Release 最新版本，并在用户明确授权 (confirmed=True) 后执行一键部署或升级。
"""
import os
import json
import zipfile
import logging
from typing import Any, Optional
import aiohttp

from .config import (
    RUNTIME_DIR,
    SHELL_NODE_DIR,
    NODE_EXE,
    INDEX_JS,
    LOCAL_RELEASE_ZIP,
    DEFAULT_HTTP_PORT,
    DEFAULT_WS_PORT,
    is_port_listening,
    get_current_account,
    get_available_accounts,
    ensure_onebot_config,
)

logger = logging.getLogger("NapCatMCP.Deployer")

GITHUB_RELEASE_API = "https://api.github.com/repos/NapNeko/NapCatQQ/releases/latest"


def get_local_napcat_version() -> dict[str, str]:
    """读取本地安装的 NapCat 与 NTQQ Shell 版本信息"""
    shell_version = "unknown"
    napcat_version = "unknown"

    shell_pkg = os.path.join(SHELL_NODE_DIR, "package.json")
    if os.path.exists(shell_pkg):
        try:
            with open(shell_pkg, "r", encoding="utf-8") as f:
                data = json.load(f)
                shell_version = data.get("version", "unknown")
        except Exception:
            pass

    napcat_pkg = os.path.join(SHELL_NODE_DIR, "napcat", "package.json")
    if os.path.exists(napcat_pkg):
        try:
            with open(napcat_pkg, "r", encoding="utf-8") as f:
                data = json.load(f)
                napcat_version = data.get("version", "unknown")
        except Exception:
            pass

    return {
        "ntqq_shell_version": shell_version,
        "napcat_package_version": napcat_version
    }


async def fetch_github_latest_release() -> dict[str, Any]:
    """查询 NapNeko/NapCatQQ 官方 GitHub 最新 Release 信息"""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "OmniQQ-MCP-Server/1.0"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(GITHUB_RELEASE_API, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tag_name = data.get("tag_name", "")
                    published_at = data.get("published_at", "")
                    html_url = data.get("html_url", "https://github.com/NapNeko/NapCatQQ/releases")

                    # 查找适用于 Windows Node Shell 的资产包
                    assets = data.get("assets", [])
                    win_asset = None
                    for asset in assets:
                        name = asset.get("name", "")
                        if "Shell.Windows.Node" in name or ("Windows" in name and name.endswith(".zip")):
                            win_asset = {
                                "name": name,
                                "size_mb": round(asset.get("size", 0) / (1024 * 1024), 2),
                                "download_url": asset.get("browser_download_url", "")
                            }
                            break

                    return {
                        "reachable": True,
                        "latest_tag": tag_name,
                        "published_at": published_at,
                        "release_url": html_url,
                        "recommended_asset": win_asset
                    }
                return {
                    "reachable": False,
                    "error": f"GitHub API 返回状态码 {resp.status}",
                    "release_url": "https://github.com/NapNeko/NapCatQQ/releases"
                }
    except Exception as e:
        return {
            "reachable": False,
            "error": f"无法连接 GitHub Release API: {e}",
            "release_url": "https://github.com/NapNeko/NapCatQQ/releases"
        }


async def check_napcat_environment(live_version_info: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    全方位诊断当前 NapCat 环境：
    1. 本地沙箱文件完整性 (node.exe, index.js)
    2. 离线安装包是否存在 (NapCat.Shell.Windows.Node.zip)
    3. 端口监听状态 (HTTP 3000 / WS 3001)
    4. 已配置 QQ 账号列表
    5. 本地版本 vs GitHub 官方最新发布版本
    """
    node_exists = os.path.exists(NODE_EXE)
    index_exists = os.path.exists(INDEX_JS)
    runtime_installed = node_exists and index_exists
    local_zip_exists = os.path.exists(LOCAL_RELEASE_ZIP)

    http_open = is_port_listening(DEFAULT_HTTP_PORT)
    ws_open = is_port_listening(DEFAULT_WS_PORT)
    service_running = http_open and ws_open

    local_ver = get_local_napcat_version()
    if live_version_info and isinstance(live_version_info, dict):
        local_ver["running_app_name"] = live_version_info.get("app_name", "NapCat.Onebot")
        local_ver["running_app_version"] = live_version_info.get("app_version", "unknown")
        local_ver["protocol_version"] = live_version_info.get("protocol_version", "v11")

    github_info = await fetch_github_latest_release()

    # 状态与建议判定
    if not runtime_installed:
        status = "not_installed"
        advice = (
            "未检测到完整的 NapCat 本地运行环境 (napcat_runtime/shell_node)。"
            "请询问用户是否允许调用 `deploy_or_update_napcat(action='deploy', confirmed=True)` 自动解压/下载部署。"
        )
    elif not service_running:
        status = "installed_not_running"
        advice = (
            "NapCat 运行时已安装，但服务尚未启动（端口 3000/3001 未监听）。"
            "可调用 `start_napcat_service()` 自动拉起后台服务，或调用任意控制工具触发自动自愈启动。"
        )
    else:
        status = "ready"
        advice = "NapCat 运行时已就绪且 OneBot 11 服务正在正常运行。"

    return {
        "status": status,
        "advice": advice,
        "runtime": {
            "installed": runtime_installed,
            "runtime_dir": SHELL_NODE_DIR,
            "node_exe_exists": node_exists,
            "index_js_exists": index_exists,
            "local_offline_zip_exists": local_zip_exists,
            "local_offline_zip_path": LOCAL_RELEASE_ZIP if local_zip_exists else None,
        },
        "service": {
            "running": service_running,
            "http_port": DEFAULT_HTTP_PORT,
            "http_listening": http_open,
            "ws_port": DEFAULT_WS_PORT,
            "ws_listening": ws_open,
        },
        "accounts": {
            "current_account": get_current_account(),
            "available_accounts": get_available_accounts(),
        },
        "version": {
            "local": local_ver,
            "github_latest": github_info,
        }
    }


async def deploy_or_update_napcat(
    action: str = "deploy",
    confirmed: bool = False,
    use_local_zip_if_available: bool = True,
    target_uin: Optional[str] = None
) -> dict[str, Any]:
    """
    自动部署或更新 NapCat 运行时环境。
    安全门禁：当 confirmed=False 时，仅生成部署预览计划，绝不执行文件写入或下载，必须征得用户同意后传入 confirmed=True。
    """
    github_info = await fetch_github_latest_release()
    local_zip_exists = os.path.exists(LOCAL_RELEASE_ZIP)
    uin = target_uin or get_current_account()

    asset = github_info.get("recommended_asset") or {}
    download_url = asset.get("download_url", "")

    # 1. 安全确认锁拦截
    if not confirmed:
        source_desc = (
            f"本地离线包 ({LOCAL_RELEASE_ZIP})"
            if (use_local_zip_if_available and local_zip_exists)
            else (download_url or "GitHub 官方 Release 最新包")
        )
        return {
            "status": "confirmation_required",
            "requires_user_permission": True,
            "planned_action": action,
            "target_directory": SHELL_NODE_DIR,
            "package_source": source_desc,
            "github_latest_tag": github_info.get("latest_tag", "unknown"),
            "account_to_configure": uin or "(部署后首次启动扫码登录)",
            "message_for_ai": (
                "⚠️ 安全拦截：自动部署或更新将修改本地 napcat_runtime 目录。"
                "请先向用户展示上述【部署目标路径、安装包来源、版本号】，"
                "在获得用户明确许可后，再次调用本工具并设置 `confirmed=True` 执行。"
            )
        }

    # 2. 用户已确认，执行部署或更新
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    os.makedirs(SHELL_NODE_DIR, exist_ok=True)

    zip_to_extract = None

    if use_local_zip_if_available and local_zip_exists and action == "deploy":
        zip_to_extract = LOCAL_RELEASE_ZIP
    elif download_url:
        # 从 GitHub 下载最新包
        downloaded_zip = os.path.join(RUNTIME_DIR, f"NapCat_{github_info.get('latest_tag', 'latest')}.zip")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                    if resp.status != 200:
                        if local_zip_exists:
                            zip_to_extract = LOCAL_RELEASE_ZIP
                        else:
                            return {
                                "status": "failed",
                                "error": f"下载官方发布包失败 (HTTP {resp.status})，且本地无离线包。",
                                "download_url": download_url
                            }
                    else:
                        with open(downloaded_zip, "wb") as f:
                            async for chunk in resp.content.iter_chunked(1024 * 64):
                                f.write(chunk)
                        zip_to_extract = downloaded_zip
        except Exception as e:
            if local_zip_exists:
                zip_to_extract = LOCAL_RELEASE_ZIP
            else:
                return {
                    "status": "failed",
                    "error": f"网络下载异常: {e}",
                    "download_url": download_url
                }
    elif local_zip_exists:
        zip_to_extract = LOCAL_RELEASE_ZIP
    else:
        return {
            "status": "failed",
            "error": "既无法从 GitHub 获取下载链接，本地也不存在 NapCat.Shell.Windows.Node.zip 离线包。",
            "manual_url": "https://github.com/NapNeko/NapCatQQ/releases"
        }

    # 3. 解压归档文件
    try:
        with zipfile.ZipFile(zip_to_extract, "r") as zf:
            zf.extractall(SHELL_NODE_DIR)
    except Exception as e:
        return {
            "status": "failed",
            "error": f"解压安装包 ({zip_to_extract}) 到 {SHELL_NODE_DIR} 失败: {e}"
        }

    # 4. 初始化 OneBot 11 配置文件
    config_ok = False
    if uin:
        config_ok = ensure_onebot_config(uin)

    return {
        "status": "success",
        "action": action,
        "extracted_from": zip_to_extract,
        "target_directory": SHELL_NODE_DIR,
        "node_ready": os.path.exists(NODE_EXE),
        "index_ready": os.path.exists(INDEX_JS),
        "onebot_configured_for_uin": uin if config_ok else None,
        "message": "NapCat 运行时已成功部署/更新！现在可以调用 `start_napcat_service` 启动服务。"
    }
