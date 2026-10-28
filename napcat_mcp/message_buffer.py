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
        self._accounts: dict[str, tuple[deque, deque, deque]] = {}
        self.active_account = ''
        self._account_generation = 0
        self._messages, self._notices, self._requests = self._account_buffers('')
        self._event_hooks: list[Callable[[dict[str, Any]], Any]] = []
        self._hook_tasks = set()
        self._hook_queue = None
        self._hook_worker = None

    def _account_buffers(self, account: str):
        if account not in self._accounts:
            self._accounts[account] = (deque(maxlen=self.maxlen), deque(maxlen=100), deque(maxlen=100))
        return self._accounts[account]

    def select_account(self, account: str):
        """Change the visible account without discarding the previous account's history."""
        account = str(account).strip()
        if not account.isdigit():
            raise ValueError('QQ account must be numeric')
        if account != self.active_account:
            self._account_generation += 1
        self.active_account = account
        self._messages, self._notices, self._requests = self._account_buffers(account)

    async def close(self):
        import asyncio
        if self._hook_queue is not None:
            try:
                await asyncio.wait_for(self._hook_queue.join(), timeout=5)
            except asyncio.TimeoutError:
                logger.warning('事件钩子未在关闭期限内处理完毕')
        if self._hook_worker is not None:
            self._hook_worker.cancel()
            await asyncio.gather(self._hook_worker, return_exceptions=True)
        tasks = list(self._hook_tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def push_event_async(self, event: dict[str, Any]):
        """Receive events with bounded hook backpressure and ordered callbacks."""
        import asyncio
        record = self.push_event(event, dispatch_hooks=False)
        if record and self._event_hooks and str(event.get('self_id') or '') == self.active_account:
            if self._hook_queue is None:
                self._hook_queue = asyncio.Queue(maxsize=200)
                self._hook_worker = asyncio.create_task(self._drain_hooks())
            await self._hook_queue.put((self.active_account, self._account_generation, record))
        return record

    async def _drain_hooks(self):
        import asyncio
        while True:
            account, generation, record = await self._hook_queue.get()
            try:
                for hook in list(self._event_hooks):
                    if account != self.active_account or generation != self._account_generation:
                        break
                    try:
                        if asyncio.iscoroutinefunction(hook):
                            await hook(record)
                        else:
                            await asyncio.to_thread(hook, record)
                    except Exception:
                        logger.exception('事件钩子失败')
            finally:
                self._hook_queue.task_done()

    def _spawn_hook(self, hook, record):
        import asyncio
        async def run():
            try:
                await hook(record)
            except Exception:
                logger.exception('异步事件钩子失败')
        task = asyncio.create_task(run())
        self._hook_tasks.add(task)
        task.add_done_callback(self._hook_tasks.discard)

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
                if not isinstance(sdata, dict):
                    continue
                if stype == "text":
                    parts.append(str(sdata.get("text") or ""))
                elif stype == "at":
                    qq = sdata.get("qq", "")
                    name = sdata.get("name", "")
                    parts.append(f"@{name or qq} ")
                elif stype == "image":
                    url = sdata.get("url") or sdata.get("file", "")
                    summary = str(sdata.get("summary") or "[图片]")
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
                elif stype == "mface":
                    parts.append(f"[商城表情:{sdata.get('summary') or sdata.get('emoji_id', '')}]")
                elif stype == "video":
                    parts.append(f"[视频:{sdata.get('url') or sdata.get('file', '')}]")
                elif stype == "json":
                    parts.append("[卡片/小程序消息]")
                elif stype in ("music", "location", "contact", "miniapp", "xml", "markdown",
                               "onlinefile", "flashtransfer", "dice", "rps", "poke"):
                    parts.append(f"[{stype}:{sdata.get('title') or sdata.get('name') or sdata.get('result') or ''}]")
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

    def push_event(self, event: dict[str, Any], dispatch_hooks: bool = True) -> Optional[dict[str, Any]]:
        """处理并缓存收到的 WebSocket 事件"""
        if not isinstance(event, dict):
            return None

        account = str(event.get('self_id') or '')
        if account and not account.isdigit():
            return None
        if not account:
            if self.active_account:
                logger.warning('丢弃缺少 self_id 的事件，避免混入当前账号缓存')
                return None
            account = ''
        elif not self.active_account:
            self.select_account(account)
        messages, notices, requests = self._account_buffers(account)

        post_type = event.get("post_type")
        if post_type == "meta_event":
            return None

        try:
            ts = float(event.get("time") or time.time())
            dt_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        except (TypeError, ValueError, OverflowError, OSError):
            ts = time.time()
            dt_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

        record: Optional[dict[str, Any]] = None

        if post_type in ("message", "message_sent"):
            msg_type = event.get("message_type", "private")
            sender = event.get("sender") or {}
            if not isinstance(sender, dict):
                sender = {}
            user_id = event.get("user_id") or sender.get("user_id")
            group_id = event.get("group_id")
            nickname = str(sender.get("card") or sender.get("nickname") or user_id or "")

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
            messages.append(record)

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
            notices.append(record)

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
            requests.append(record)

        # 触发已注册的外部钩子（支持同步函数与异步协程回调）
        if record and account == self.active_account and dispatch_hooks:
            import asyncio
            for hook in list(self._event_hooks):
                try:
                    if asyncio.iscoroutinefunction(hook):
                        self._spawn_hook(hook, record)
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
        limit = max(1, int(count))
        tid = int(target_id) if target_id is not None else None
        kw = keyword.lower() if keyword else None
        for item in reversed(self._messages):
            if not include_self_sent and item.get("is_self_sent"):
                continue

            mtype = item.get("message_type")
            if chat_type in ("private", "group") and mtype != chat_type:
                continue

            if tid is not None:
                if mtype == "group":
                    if item.get("group_id") != tid and (chat_type == 'group' or item.get("user_id") != tid):
                        continue
                else:
                    peer = item.get('target_id') if item.get('is_self_sent') else item.get('user_id')
                    if peer != tid:
                        continue

            if kw:
                text = (item.get("clean_text") or "").lower()
                nick = (item.get("nickname") or "").lower()
                if kw not in text and kw not in nick:
                    continue

            results.append(item)
            if len(results) >= limit:
                break

        return list(reversed(results))

    def get_recent_notices_and_requests(self, count: int = 20) -> dict[str, list[dict[str, Any]]]:
        """获取最近的群通知事件（如群文件上传、群成员变动）和加好友/加群请求"""
        count = max(0, int(count))
        n_list = list(self._notices)[-count:] if count else []
        r_list = list(self._requests)[-count:] if count else []
        return {
            "notices": n_list,
            "requests": r_list
        }

    def clear(self) -> int:
        """清空当前账号的消息、通知与请求，返回清理的记录总数。"""
        n = len(self._messages) + len(self._notices) + len(self._requests)
        self._messages.clear()
        self._notices.clear()
        self._requests.clear()
        return n
