"""
对话历史存储服务
"""
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from project.logger_handler import logger

# 每个会话最大消息数限制
MAX_MESSAGES_PER_SESSION = 500


class ChatHistoryService:
    """对话历史存储服务，支持按用户/会话隔离"""

    def __init__(self, history_dir: str = None):
        if history_dir is None:
            project_root = Path(__file__).parent.parent.parent
            history_dir = project_root / "data" / "chat_history"

        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def _history_file(self, session_id: Optional[str] = None) -> Path:
        if session_id:
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
            return self.history_dir / f"chat_history_{safe_name}.json"
        return self.history_dir / "chat_history.json"

    def load_history(self, session_id: Optional[str] = None) -> List[Dict]:
        history_file = self._history_file(session_id)
        if not history_file.exists():
            return []

        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("messages", [])
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"加载对话历史失败: {e}")
            return []
        except OSError as e:
            logger.error(f"读取对话历史文件失败: {e}")
            return []

    def save_history(self, messages: List[Dict], session_id: Optional[str] = None) -> bool:
        try:
            # 消息数量限制：保留最新的消息
            if len(messages) > MAX_MESSAGES_PER_SESSION:
                messages = messages[-MAX_MESSAGES_PER_SESSION:]

            data = {
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message_count": len(messages),
                "messages": messages,
            }

            history_file = self._history_file(session_id)
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"保存对话历史成功，共 {len(messages)} 条消息")
            return True
        except OSError as e:
            logger.error(f"保存对话历史失败: {e}")
            return False

    def clear_history(self, session_id: Optional[str] = None) -> bool:
        try:
            history_file = self._history_file(session_id)
            if history_file.exists():
                history_file.unlink()
            logger.info("对话历史已清空")
            return True
        except OSError as e:
            logger.error(f"清空对话历史失败: {e}")
            return False

    def get_history_info(self, session_id: Optional[str] = None) -> Dict:
        history_file = self._history_file(session_id)
        if not history_file.exists():
            return {
                "exists": False,
                "message_count": 0,
                "last_updated": None,
            }

        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    "exists": True,
                    "message_count": data.get("message_count", 0),
                    "last_updated": data.get("last_updated", "未知"),
                }
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.error(f"获取对话历史信息失败: {e}")
            return {
                "exists": False,
                "message_count": 0,
                "last_updated": None,
            }

    def load_recent_history(
        self,
        session_id: Optional[str] = None,
        max_rounds: int = 10,
        max_chars_per_msg: int = 1000,
    ) -> List[Dict]:
        """加载最近 N 轮对话历史（一轮 = user + assistant），用于注入 LLM 上下文"""
        messages = self.load_history(session_id)
        if not messages:
            return []

        # 保留最后 max_rounds * 2 条消息
        tail = messages[-(max_rounds * 2):]

        # 每条消息截断
        result = []
        for msg in tail:
            content = msg.get("content", "")
            if len(content) > max_chars_per_msg:
                content = content[:max_chars_per_msg] + "..."
            result.append({"role": msg.get("role", "user"), "content": content})

        return result

    def list_sessions(self) -> List[Dict]:
        """列出所有会话摘要信息"""
        sessions = []
        try:
            for history_file in self.history_dir.glob("chat_history*.json"):
                try:
                    with open(history_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # 从文件名提取 session_id
                    filename = history_file.stem  # e.g. chat_history or chat_history_abc123
                    if filename == "chat_history":
                        sid = None
                    else:
                        sid = filename[len("chat_history_"):]

                    messages = data.get("messages", [])
                    # 取第一条用户消息作为预览
                    preview = ""
                    for m in messages:
                        if m.get("role") == "user":
                            preview = m.get("content", "")[:50]
                            break

                    sessions.append({
                        "session_id": sid,
                        "message_count": data.get("message_count", len(messages)),
                        "last_updated": data.get("last_updated", "未知"),
                        "preview": preview,
                    })
                except (json.JSONDecodeError, OSError):
                    continue
        except OSError:
            pass

        # 按更新时间倒序排列
        sessions.sort(key=lambda s: s["last_updated"] or "", reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """删除指定会话的历史文件"""
        if not session_id:
            return False
        try:
            history_file = self._history_file(session_id)
            if history_file.exists():
                history_file.unlink()
            return True
        except OSError as e:
            logger.error(f"删除会话失败: {e}")
            return False

    def get_all_stats(self) -> Dict:
        """获取所有聊天历史的统计信息"""
        total_messages = 0
        session_count = 0

        try:
            for history_file in self.history_dir.glob("chat_history*.json"):
                try:
                    with open(history_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        total_messages += data.get("message_count", len(data.get("messages", [])))
                        session_count += 1
                except (json.JSONDecodeError, OSError):
                    continue
        except OSError:
            pass

        return {
            "session_count": session_count,
            "total_messages": total_messages
        }


chat_history_service = ChatHistoryService()
