"""
NapCat MCP Server 标准启动入口 (stdio 模式)
支持直接被 Antigravity / Claude Desktop / Cursor / Windsurf 等 MCP 宿主拉起。
"""
import os
import sys
import asyncio
import logging
import argparse

# 确保项目根目录在 sys.path 中
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 强制将 Windows 下的 stdin / stdout 设为 UTF-8，确保 JSON-RPC 中文无乱码
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 日志严禁输出到 stdout (stdout 专用于 MCP JSON-RPC 通信)，全部定向到 stderr 与日志文件
LOG_FILE = os.path.join(CURRENT_DIR, "napcat_mcp.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(LOG_FILE, encoding="utf-8")
    ]
)

from napcat_mcp.server import NapCatMCPServer, export_antigravity_schemas  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="NapCatQQ Model Context Protocol (MCP) Server")
    parser.add_argument(
        "--export-schemas",
        type=str,
        default="",
        help="导出工具 JSON Schema 到指定目录后退出"
    )
    args = parser.parse_args()

    if args.export_schemas:
        count = export_antigravity_schemas(args.export_schemas)
        sys.stderr.write(f"[OK] 成功导出 {count} 个 MCP 工具 Schema 到: {args.export_schemas}\n")
        return

    server = NapCatMCPServer()
    try:
        asyncio.run(server.run_stdio())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
