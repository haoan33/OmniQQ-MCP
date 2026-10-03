"""
NapCat MCP Server 实时消息滚动缓冲区与事件回调接口
负责接收 WebSocket 消息流，净化 CQ 码与消息段，并为未来外部筛选脚本预留 Event Hook。
"""
import time
import datetime
import logging
from collections import deque
from typing import Any, Callable, Optional

logger = logging.getLogger("NapCatMCP.MessageBuffer")


class MessageBuffer:
    """实时消息环形缓冲区 + 可扩展事件钩子总线"""

    def __init__(self, maxlen: int = 200):
        self.maxlen = maxlen
        self._messages: deque[dict[str, Any]] = deque(maxlen=maxlen)
        self._notices: deque[dict[str, Any]] = deque(maxlen=100)
        self._requests: deque[dict[str, Any]] = deque(maxlen=100)
        self._event_hooks: list[Callable[[dict[str, Any]], Any]] = []

    def register_event_hook(self, callback: Callable[[dict[str, Any]], Any]):
        """
        注册自定义事件回调钩子 (预留给外部消息筛选器或主动唤醒脚本使用)
        当收到任何 OneBot 11 事件时，会自动触发已注册的 callback(event)。
        """
        if callback not in self._event_hooks:
            self._event_hooks.append(callback)

    def unregister_event_hook(self, callback: Callable[[dict[str, Any]], Any]):
        """移除已注册的事件回调钩子"""
        if callback in self._event_hooks:
            self._event_hooks.remove(callback)

    @staticmethod
    def extract_clean_text(event: dict[str, Any]) -> str:
        """将 OneBot 11 消息段数组或 CQ 码转换为 AI 易读的清洗文本"""
        msg = event.get("message")
        if isinstance(msg, list):
            parts = []
            for seg in msg:
                if not isinstance(seg, dict):
                    continue
                stype = seg.get("type", "")
                sdata = seg.get("data", {}) or {}
                if stype == "text":
                    parts.append(sdata.get("text", ""))
                elif stype == "at":
                    qq = sdata.get("qq", "")
                    name = sdata.get("name", "")
                    parts.append(f"@{name or qq} ")
                elif stype == "image":
                    url = sdata.get("url") or sdata.get("file", "")
                    summary = sdata.get("summary", "[图片]")
                    parts.append(f"{summary}({url})" if url else summary)
                elif stype == "file":
                    fname = sdata.get("file", "未知文件")
                    fid = sdata.get("file_id", "")
                    fsize = sdata.get("file_size", "")
                    parts.append(f"[文件: {fname}, file_id={fid}, size={fsize}]")
                elif stype == "record":
                    parts.append(f"[语音: {sdata.get('file', '')}]")
                elif stype == "reply":
                    parts.append(f"[回复消息ID:{sdata.get('id', '')}] ")
                elif stype == "face":
                    parts.append(f"[表情:{sdata.get('id', '')}]")
                elif stype == "json":
                    parts.append("[卡片/小程序消息]")
                elif stype == "forward":
                    parts.append(f"[合并转发ID:{sdata.get('id', '')}]")
                else:
                    parts.append(f"[{stype}]")
            text = "".join(parts).strip()
            if text:
                return text

        raw = event.get("raw_message")
        if raw is not None:
            return str(raw).strip()
        return str(msg or "").strip()

    def push_event(self, event: dict[str, Any]) -> Optional[dict[str, Any]]:
        """处理并缓存收到的 WebSocket 事件"""
        if not isinstance(event, dict):
            return None

        post_type = event.get("post_type")
        if post_type == "meta_event":
            return None

        ts = event.get("time") or int(time.time())
        dt_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

        record: Optional[dict[str, Any]] = None

        if post_type in ("message", "message_sent"):
            msg_type = event.get("message_type", "private")
            sender = event.get("sender") or {}
            user_id = event.get("user_id") or sender.get("user_id")
            group_id = event.get("group_id")
            nickname = sender.get("card") or sender.get("nickname") or str(user_id or "")

            record = {
                "post_type": post_type,
                "message_id": event.get("message_id"),
                "message_type": msg_type,
                "sub_type": event.get("sub_type", ""),
                "user_id": user_id,
                "target_id": event.get("target_id"),
                "nickname": nickname,
                "group_id": group_id,
                "clean_text": self.extract_clean_text(event),
                "raw_message": event.get("raw_message", ""),
                "message": event.get("message", []),
                "segments": event.get("message", []),
                "timestamp": ts,
                "datetime": dt_str,
                "is_self_sent": post_type == "message_sent",
                "raw_event": event,
            }
            self._messages.append(record)

        elif post_type == "notice":
            record = {
                "post_type": "notice",
                "notice_type": event.get("notice_type", ""),
                "sub_type": event.get("sub_type", ""),
                "group_id": event.get("group_id"),
                "user_id": event.get("user_id"),
                "operator_id": event.get("operator_id"),
                "file": event.get("file"),
                "timestamp": ts,
                "datetime": dt_str,
                "raw_event": event
            }
            self._notices.append(record)

        elif post_type == "request":
            record = {
                "post_type": "request",
                "request_type": event.get("request_type", ""),
                "sub_type": event.get("sub_type", ""),
                "user_id": event.get("user_id"),
                "group_id": event.get("group_id"),
                "comment": event.get("comment", ""),
                "flag": event.get("flag", ""),
                "timestamp": ts,
                "datetime": dt_str,
                "raw_event": event
            }
            self._requests.append(record)

        # 触发已注册的外部钩子（支持同步函数与异步协程回调）
        if record:
            import asyncio
            for hook in list(self._event_hooks):
                try:
                    if asyncio.iscoroutinefunction(hook):
                        asyncio.create_task(hook(record))
                    else:
                        hook(record)
                except Exception as e:
                    logger.warning(f"执行事件钩子异常: {e}")

        return record

    def get_recent_messages(
        self,
        count: int = 20,
        chat_type: str = "all",
        target_id: Optional[int] = None,
        keyword: Optional[str] = None,
        include_self_sent: bool = False
    ) -> list[dict[str, Any]]:
        """
        从环形缓冲区检索最近的聊天消息
        :param count: 返回的最大条数
        :param chat_type: 'all' | 'private' | 'group'
        :param target_id: 若指定，则按 user_id (私聊/群内发言人) 或 group_id (群号) 过滤
        :param keyword: 若指定，仅返回包含该关键词的消息
        :param include_self_sent: 是否包含机器人自身发出的回声消息
        """
        results = []
        for item in reversed(self._messages):
            if not include_self_sent and item.get("is_self_sent"):
                continue

            mtype = item.get("message_type")
            if chat_type in ("private", "group") and mtype != chat_type:
                continue

            if target_id is not None:
                tid = int(target_id)
                if mtype == "group":
                    if item.get("group_id") != tid and item.get("user_id") != tid:
                        continue
                else:
                    if item.get("user_id") != tid:
                        continue

            if keyword:
                kw = keyword.lower()
                text = (item.get("clean_text") or "").lower()
                nick = (item.get("nickname") or "").lower()
                if kw not in text and kw not in nick:
                    continue

            results.append(item)
            if len(results) >= max(1, int(count)):
                break

        return list(reversed(results))

    def get_recent_notices_and_requests(self, count: int = 20) -> dict[str, list[dict[str, Any]]]:
        """获取最近的群通知事件（如群文件上传、群成员变动）和加好友/加群请求"""
        n_list = list(self._notices)[-count:]
        r_list = list(self._requests)[-count:]
        return {
            "notices": n_list,
            "requests": r_list
        }

    def clear(self) -> int:
        """清空消息缓冲区，返回清理的消息条数"""
        n = len(self._messages)
        self._messages.clear()
        return n
