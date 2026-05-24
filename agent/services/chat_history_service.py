"""
对话历史存储服务
（SQLAlchemy 2.0 后端）
"""
from datetime import datetime
from typing import List, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from agent.database.db_config import SessionLocal, with_session
from agent.database.models import ChatSession, ChatMessage
from project.logger_handler import logger

# 每个会话最大消息数限制
MAX_MESSAGES_PER_SESSION = 500

# 默认 session_id（兼容匿名用户）
_DEFAULT_SESSION_ID = "__default__"


class ChatHistoryService:
    """对话历史存储服务，支持按会话隔离"""

    def __init__(self):
        pass  # 不再需要初始化文件目录

    def _resolve_session_id(self, session_id: Optional[str]) -> str:
        return session_id if session_id else _DEFAULT_SESSION_ID

    # ── CRUD ──────────────────────────────────────────────

    @with_session
    def load_history(self, session_id: Optional[str] = None, session: Session = None) -> List[Dict]:
        sid = self._resolve_session_id(session_id)
        messages = (
            session.query(ChatMessage)
            .filter_by(session_id=sid)
            .order_by(ChatMessage.id)
            .all()
        )
        return [{"role": m.role, "content": m.content} for m in messages]

    @with_session
    def save_history(self, messages: List[Dict], session_id: Optional[str] = None, session: Session = None) -> bool:
        sid = self._resolve_session_id(session_id)

        # 消息数量限制
        if len(messages) > MAX_MESSAGES_PER_SESSION:
            messages = messages[-MAX_MESSAGES_PER_SESSION:]

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 取第一条用户消息作为预览
        preview = ""
        for m in messages:
            if m.get("role") == "user":
                preview = m.get("content", "")[:50]
                break

        # Upsert ChatSession
        chat_session = session.query(ChatSession).filter_by(session_id=sid).first()
        if chat_session is None:
            chat_session = ChatSession(
                session_id=sid,
                created_at=now,
            )
            session.add(chat_session)

        chat_session.message_count = len(messages)
        chat_session.last_message_at = now
        chat_session.preview = preview

        # 删除旧消息，重新插入
        session.query(ChatMessage).filter_by(session_id=sid).delete()
        for m in messages:
            msg = ChatMessage(
                session_id=sid,
                role=m.get("role", "user"),
                content=m.get("content", ""),
                created_at=now,
            )
            session.add(msg)

        logger.info(f"保存对话历史成功，共 {len(messages)} 条消息")
        return True

    @with_session
    def clear_history(self, session_id: Optional[str] = None, session: Session = None) -> bool:
        sid = self._resolve_session_id(session_id)
        chat_session = session.query(ChatSession).filter_by(session_id=sid).first()
        if chat_session:
            session.delete(chat_session)  # cascade 会删掉 messages
        logger.info("对话历史已清空")
        return True

    @with_session
    def get_history_info(self, session_id: Optional[str] = None, session: Session = None) -> Dict:
        sid = self._resolve_session_id(session_id)
        chat_session = session.query(ChatSession).filter_by(session_id=sid).first()
        if chat_session is None:
            return {"exists": False, "message_count": 0, "last_updated": None}
        return {
            "exists": True,
            "message_count": chat_session.message_count,
            "last_updated": chat_session.last_message_at or "未知",
        }

    @with_session
    def load_recent_history(
        self,
        session_id: Optional[str] = None,
        max_rounds: int = 10,
        max_chars_per_msg: int = 1000,
        session: Session = None,
    ) -> List[Dict]:
        """加载最近 N 轮对话历史"""
        sid = self._resolve_session_id(session_id)
        limit = max_rounds * 2
        messages = (
            session.query(ChatMessage)
            .filter_by(session_id=sid)
            .order_by(ChatMessage.id.desc())
            .limit(limit)
            .all()
        )
        messages = list(reversed(messages))

        result = []
        for m in messages:
            content = m.content
            if len(content) > max_chars_per_msg:
                content = content[:max_chars_per_msg] + "..."
            result.append({"role": m.role, "content": content})
        return result

    @with_session
    def list_sessions(self, session: Session = None) -> List[Dict]:
        sessions = (
            session.query(ChatSession)
            .order_by(ChatSession.last_message_at.desc())
            .all()
        )
        result = []
        for s in sessions:
            sid = s.session_id
            # 对匿名用户隐藏内部 session_id
            display_sid = sid if sid != _DEFAULT_SESSION_ID else None
            result.append({
                "session_id": display_sid,
                "message_count": s.message_count,
                "last_updated": s.last_message_at or "未知",
                "preview": s.preview or "",
            })
        return result

    @with_session
    def delete_session(self, session_id: str, session: Session = None) -> bool:
        if not session_id:
            return False
        chat_session = session.query(ChatSession).filter_by(session_id=session_id).first()
        if chat_session:
            session.delete(chat_session)
        return True

    @with_session
    def get_all_stats(self, session: Session = None) -> Dict:
        session_count = session.query(func.count(ChatSession.session_id)).scalar()
        total_messages = session.query(func.sum(ChatSession.message_count)).scalar() or 0
        return {
            "session_count": session_count,
            "total_messages": total_messages,
        }


# 全局单例
chat_history_service = ChatHistoryService()
