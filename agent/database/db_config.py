"""
SQLAlchemy 数据库配置

提供引擎、Session 管理、Base 声明。
同步引擎，适用于 SQLite 开发 / PostgreSQL 生产。
"""
import os
import functools
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# ── 数据库 URL ──────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/health_assistant.db")

_is_sqlite = DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


# ── Base ────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── 上下文管理器：服务独立调用时使用 ─────────────────────
@contextmanager
def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── FastAPI 依赖：路由层获取 session ────────────────────
def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── 服务层事务辅助装饰器 ─────────────────────────────────
def with_session(method):
    """
    装饰器：自动处理 session 生命周期。

    - 如果调用方传入了 session，复用它（参与外部事务）
    - 如果未传入，自动创建 session 并在方法返回时 commit / 异常时 rollback
    """
    @functools.wraps(method)
    def wrapper(*args, session=None, **kwargs):
        if session is not None:
            return method(*args, session=session, **kwargs)
        with get_session() as session:
            return method(*args, session=session, **kwargs)
    return wrapper


# ── 初始化 / 健康检查 ───────────────────────────────────
def init_db():
    """创建所有表"""
    # 确保数据目录存在（SQLite）
    if _is_sqlite:
        db_path = DATABASE_URL.split("///", 1)[1]
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    Base.metadata.create_all(engine)


def check_db_connection() -> bool:
    """数据库健康检查"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
