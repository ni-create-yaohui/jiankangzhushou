"""
文档管理服务 - 负责文档上传、元数据管理、状态追踪
（SQLAlchemy 2.0 后端）
"""
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from agent.database.db_config import SessionLocal, with_session
from agent.database.models import Document, DocumentMd5
from project.path_tool import get_abs_path
from project.logger_handler import logger
from project.file_hander import get_file_md5_hex


class DocumentService:
    """
    文档管理服务

    功能：
    - 文档元数据管理（SQLAlchemy ORM）
    - MD5 校验（数据库存储）
    - 文档状态追踪（pending/processing/completed/failed）
    """

    def __init__(self):
        self.knowledge_dir = get_abs_path("data/knowledge")
        os.makedirs(self.knowledge_dir, exist_ok=True)

    def generate_doc_id(self) -> str:
        return f"doc_{uuid.uuid4().hex[:12]}"

    # ── 内部辅助 ──────────────────────────────────────────

    @staticmethod
    def _doc_to_dict(doc: Document) -> Dict:
        return {
            "doc_id": doc.doc_id,
            "original_filename": doc.original_filename,
            "saved_filename": doc.saved_filename,
            "saved_path": doc.saved_path,
            "md5_hex": doc.md5_hex,
            "file_size": doc.file_size,
            "status": doc.status,
            "chunk_count": doc.chunk_count,
            "entity_count": doc.entity_count,
            "relation_count": doc.relation_count,
            "created_at": doc.created_at,
            "processed_at": doc.processed_at,
            "error_message": doc.error_message,
        }

    # ── CRUD ──────────────────────────────────────────────

    @with_session
    def create_document_record(
        self,
        original_filename: str,
        saved_path: str,
        md5_hex: str,
        file_size: int,
        doc_id: str = None,
        session: Session = None,
    ) -> Dict:
        doc_id = doc_id or self.generate_doc_id()
        doc = Document(
            doc_id=doc_id,
            original_filename=original_filename,
            saved_filename=os.path.basename(saved_path),
            saved_path=saved_path,
            md5_hex=md5_hex,
            file_size=file_size,
        )
        session.add(doc)
        logger.info(f"[DocumentService] 创建文档记录: {doc_id}, 文件: {original_filename}")
        return self._doc_to_dict(doc)

    @with_session
    def update_document_status(
        self,
        doc_id: str,
        status: str,
        chunk_count: int = 0,
        entity_count: int = 0,
        relation_count: int = 0,
        error_message: Optional[str] = None,
        session: Session = None,
    ):
        doc = session.query(Document).filter_by(doc_id=doc_id).first()
        if doc is None:
            logger.warning(f"[DocumentService] 文档不存在: {doc_id}")
            return

        doc.status = status

        if status == "completed":
            doc.chunk_count = chunk_count
            doc.entity_count = entity_count
            doc.relation_count = relation_count
            doc.processed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 记录 MD5
            existing_md5 = session.query(DocumentMd5).filter_by(md5_hex=doc.md5_hex).first()
            if not existing_md5:
                session.add(DocumentMd5(md5_hex=doc.md5_hex, doc_id=doc_id))

        if status == "failed":
            doc.error_message = error_message

        logger.info(f"[DocumentService] 更新文档状态: {doc_id} -> {status}")

    @with_session
    def get_document(self, doc_id: str, session: Session = None) -> Optional[Dict]:
        doc = session.query(Document).filter_by(doc_id=doc_id).first()
        return self._doc_to_dict(doc) if doc else None

    @with_session
    def list_documents(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        session: Session = None,
    ) -> Dict:
        query = session.query(Document)
        if status:
            query = query.filter_by(status=status)

        total = query.count()
        docs = (
            query.order_by(Document.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {
            "documents": [self._doc_to_dict(d) for d in docs],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    @with_session
    def delete_document(self, doc_id: str, session: Session = None) -> bool:
        doc = session.query(Document).filter_by(doc_id=doc_id).first()
        if doc is None:
            logger.warning(f"[DocumentService] 文档不存在: {doc_id}")
            return False

        # 删除磁盘文件
        if doc.saved_path and os.path.exists(doc.saved_path):
            try:
                os.remove(doc.saved_path)
                logger.info(f"[DocumentService] 删除文件: {doc.saved_path}")
            except Exception as e:
                logger.error(f"[DocumentService] 删除文件失败: {e}")

        # 删除 MD5 记录
        session.query(DocumentMd5).filter_by(doc_id=doc_id).delete()

        # 删除文档记录
        session.delete(doc)

        logger.info(f"[DocumentService] 删除文档记录: {doc_id}")
        return True

    @with_session
    def get_stats(self, session: Session = None) -> Dict:
        total = session.query(func.count(Document.doc_id)).scalar()
        completed = session.query(func.count(Document.doc_id)).filter_by(status="completed").scalar()
        processing = session.query(func.count(Document.doc_id)).filter_by(status="processing").scalar()
        pending = session.query(func.count(Document.doc_id)).filter_by(status="pending").scalar()
        failed = session.query(func.count(Document.doc_id)).filter_by(status="failed").scalar()
        total_chunks = session.query(func.sum(Document.chunk_count)).scalar() or 0
        total_entities = session.query(func.sum(Document.entity_count)).scalar() or 0
        total_relations = session.query(func.sum(Document.relation_count)).scalar() or 0
        total_size = session.query(func.sum(Document.file_size)).scalar() or 0

        return {
            "total": total,
            "completed": completed,
            "processing": processing,
            "pending": pending,
            "failed": failed,
            "total_chunks": total_chunks,
            "total_entities": total_entities,
            "total_relations": total_relations,
            "total_size_bytes": total_size,
        }

    def check_file_duplicate(self, file_path: str, session: Session = None) -> Optional[Dict]:
        """检查文件是否重复"""
        md5_hex = get_file_md5_hex(file_path)
        if not md5_hex:
            return None

        own_session = session is None
        if own_session:
            session = SessionLocal()
        try:
            # 检查 MD5 表
            md5_record = session.query(DocumentMd5).filter_by(md5_hex=md5_hex).first()
            if md5_record is None:
                # 也检查 Document 表
                doc = session.query(Document).filter_by(md5_hex=md5_hex).first()
                if doc:
                    return self._doc_to_dict(doc)
                return None

            # MD5 存在，找对应文档
            doc = session.query(Document).filter_by(doc_id=md5_record.doc_id).first()
            if doc:
                return self._doc_to_dict(doc)
            return {"md5_hex": md5_hex, "status": "duplicate"}
        finally:
            if own_session:
                session.close()


# 全局服务实例
document_service = DocumentService()
