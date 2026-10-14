"""
OmniQQ-MCP 终端账号管理与扫码登录交互 CLI (napcat_mcp/account_cli.py)
供命令行直接调用进行多账号切换与二维码扫码登录。
"""
import socket
import subprocess
import sys
import time

from .config import (
    SHELL_NODE_DIR,
    NODE_EXE,
    INDEX_JS,
    get_current_account,
    set_current_account,
    get_available_accounts,
    kill_napcat_processes,
)


def restart_napcat_with_account(uin: str) -> bool:
    """切换账号后重启 NapCat 沙箱以新账号上线"""
    kill_napcat_processes()
    if not set_current_account(uin):
        print('[ERROR] 账号配置保存失败，未启动新账号')
        return False
    print(f"[*] 正在以账号 {uin} 重新启动 NapCat 沙箱...")
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 7  # SW_SHOWMINNOACTIVE
    subprocess.Popen(
        [NODE_EXE, INDEX_JS, "-q", uin],
        cwd=SHELL_NODE_DIR,
        startupinfo=startupinfo,
        creationflags=0x00000010,  # CREATE_NEW_CONSOLE
    )
    for _ in range(30):
        time.sleep(1)
        try:
            s = socket.create_connection(("127.0.0.1", 3001), timeout=1)
            s.close()
            print(f"[OK] NapCat 沙箱已就绪 (账号: {uin}, 端口: 3001)")
            return True
        except (ConnectionRefusedError, OSError):
            pass
    print("[WARN] 等待 NapCat 端口超时，请检查沙箱是否正常启动")
    return False


def scan_new_account():
    """Reuse the same bounded login flow as the MCP tool."""
    from .config import start_qrcode_login_session
    result = start_qrcode_login_session(open_image=True, wait_scan_seconds=120)
    print(result.get("message") or result.get("error") or result["status"])
    if result.get("status") == "logged_in_and_configured":
        restart_napcat_with_account(result["new_uin"])


def interactive_menu():
    current = get_current_account()
    avail = get_available_accounts()

    print("==================================================================")
    print("                     OmniQQ-MCP QQ 账号管理")
    print("==================================================================")
    print(f" 当前默认登录账号: [ {current if current else '未设置'} ]\n")
    print(" 已缓存的历史账号:")
    if not avail:
        print("  (暂无历史账号)")
    else:
        for idx, acc in enumerate(avail, 1):
            mark = " (当前默认)" if acc == current else ""
            print(f"  [{idx}] QQ: {acc}{mark}")

    print("\n 可选操作:")
    print("  [0] 扫码登录新账号 / 绑定新 QQ")
    print("  [回车] 保持当前账号退出")
    print("------------------------------------------------------------------")

    choice = input("请输入选项编号: ").strip()
    if choice == "0":
        scan_new_account()
    elif choice.isdigit() and 1 <= int(choice) <= len(avail):
        selected = avail[int(choice) - 1]
        if selected == current:
            print("[INFO] 所选账号与当前默认账号相同，无需切换。")
        else:
            restart_napcat_with_account(selected)
    else:
        print("[INFO] 保持当前设置，未做更改。")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--scan":
        scan_new_account()
    elif len(sys.argv) > 1 and sys.argv[1] == "--get":
        print(get_current_account())
    elif len(sys.argv) > 2 and sys.argv[1] == "--set":
        set_current_account(sys.argv[2])
    else:
        interactive_menu()
