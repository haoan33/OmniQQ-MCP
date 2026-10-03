"""
OmniQQ-MCP 终端账号管理与扫码登录交互 CLI (napcat_mcp/account_cli.py)
供 launcher.py 或命令行直接调用进行多账号切换与二维码扫码登录。
"""
import json
import os
import socket
import subprocess
import sys
import time

from .config import (
    SHELL_NODE_DIR,
    NAPCAT_CONFIG_DIR,
    NODE_EXE,
    INDEX_JS,
    QR_CACHE_IMAGE,
    get_current_account,
    set_current_account,
    get_available_accounts,
    ensure_onebot_config,
    kill_napcat_processes,
)


def restart_napcat_with_account(uin: str) -> bool:
    """切换账号后重启 NapCat 沙箱以新账号上线"""
    kill_napcat_processes()
    set_current_account(uin)
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
    """启动交互式扫码登录流程"""
    kill_napcat_processes()

    webui_path = os.path.join(NAPCAT_CONFIG_DIR, "webui.json")
    if os.path.exists(webui_path):
        try:
            with open(webui_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["autoLoginAccount"] = ""
            with open(webui_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print("[OK] 已清除自动登录账号，将弹出二维码")
        except Exception as e:
            print(f"[WARN] 清除 autoLoginAccount 失败: {e}")

    print("==================================================================")
    print("                     OmniQQ-MCP 扫码登录新账号")
    print("==================================================================")
    print("[*] 正在启动独立协议沙箱...")

    proc = subprocess.Popen(
        [NODE_EXE, INDEX_JS],
        cwd=SHELL_NODE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    qr_opened = False
    logged_in_uin = None

    while True:
        line = proc.stdout.readline() if proc.stdout else ""
        if not line and proc.poll() is not None:
            break
        if line:
            print(line, end="")
            if "二维码已保存到" in line and not qr_opened and os.path.exists(QR_CACHE_IMAGE):
                try:
                    os.startfile(QR_CACHE_IMAGE)
                    qr_opened = True
                    print("\n[HINT] 已自动打开二维码图片！请使用手机 QQ 扫码授权登录。\n")
                except Exception:
                    pass
            if "Worker进程已登录成功" in line or "已通知主进程登录成功" in line:
                print("\n[SUCCESS] 手机扫码授权成功！")
            if "快速登录" in line and any(ch.isdigit() for ch in line):
                for p in line.split():
                    if p.isdigit() and len(p) >= 5:
                        logged_in_uin = p
            if "OneBot11 适配器初始化完成" in line or "HTTP服务" in line:
                break

    accounts = get_available_accounts()
    current = get_current_account()
    new_accounts = [a for a in accounts if a != current]
    target_uin = new_accounts[-1] if new_accounts else (logged_in_uin or (accounts[-1] if accounts else None))

    try:
        proc.kill()
        proc.wait(timeout=5)
    except Exception:
        pass

    if target_uin:
        set_current_account(target_uin)
        print(f"\n[SUCCESS] 新账号 [ {target_uin} ] 登录并配置完毕！已设为默认账号。")
        restart_napcat_with_account(target_uin)
    else:
        print("\n[INFO] 未捕获到新账号，保持原有配置。")


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
