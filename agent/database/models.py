"""
SQLAlchemy 2.0 ORM 模型定义

7 个模型：User, HealthRecord, ChatSession, ChatMessage,
         Document, DocumentMd5, HealthReport
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from agent.database.db_config import Base


# ────────────────────────────────────────────────────────
# User
# ────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    gender: Mapped[str] = mapped_column(String(10), default="男")
    age: Mapped[int] = mapped_column(Integer, default=25)
    height: Mapped[float] = mapped_column(Float, default=170.0)
    weight: Mapped[float] = mapped_column(Float, default=65.0)
    activity_level: Mapped[str] = mapped_column(String(20), default="轻度活动")
    health_goal: Mapped[str] = mapped_column(String(50), default="保持健康")
    created_at: Mapped[str] = mapped_column(
        String(30), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    health_records: Mapped[List["HealthRecord"]] = relationship(
        "HealthRecord", back_populates="user", cascade="all, delete-orphan"
    )


# ────────────────────────────────────────────────────────
# HealthRecord
# ────────────────────────────────────────────────────────
class HealthRecord(Base):
    __tablename__ = "health_records"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("users.user_id"), nullable=False
    )
    date: Mapped[str] = mapped_column(String(20), nullable=False)
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bp_systolic: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bp_diastolic: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    heart_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sleep_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sleep_quality: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    calories_intake: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="health_records")


# ────────────────────────────────────────────────────────
# ChatSession
# ────────────────────────────────────────────────────────
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[str] = mapped_column(
        String(30), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    last_message_at: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    preview: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )


# ────────────────────────────────────────────────────────
# ChatMessage
# ────────────────────────────────────────────────────────
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("chat_sessions.session_id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(
        String(30), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")


# ────────────────────────────────────────────────────────
# Document
# ────────────────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    saved_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    saved_path: Mapped[str] = mapped_column(String(500), nullable=False)
    md5_hex: Mapped[str] = mapped_column(String(32), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    entity_count: Mapped[int] = mapped_column(Integer, default=0)
    relation_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(
        String(30), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    processed_at: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ────────────────────────────────────────────────────────
# DocumentMd5
# ────────────────────────────────────────────────────────
class DocumentMd5(Base):
    __tablename__ = "document_md5"

    md5_hex: Mapped[str] = mapped_column(String(32), primary_key=True)
    doc_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("documents.doc_id"), nullable=False
    )
    created_at: Mapped[str] = mapped_column(
        String(30), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )


# ────────────────────────────────────────────────────────
# HealthReport
# ────────────────────────────────────────────────────────
class HealthReport(Base):
    __tablename__ = "health_reports"

    report_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    date: Mapped[str] = mapped_column(String(30), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[list] = mapped_column(JSON, default=list)
