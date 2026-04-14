"""
文档管理服务 - 负责文档上传、元数据管理、状态追踪
"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from project.path_tool import get_abs_path
from project.logger_handler import logger
from project.file_hander import get_file_md5_hex


class DocumentService:
    """
    文档管理服务

    功能：
    - 文档元数据管理（JSON文件存储）
    - MD5校验（兼容现有md5.text）
    - 文档状态追踪（pending/processing/completed/failed）
    - 协调VectorStoreService处理文档
    """

    def __init__(self):
        self.metadata_file = get_abs_path("data/knowledge/document_metadata.json")
        self.md5_file = get_abs_path("md5.text")
        self.knowledge_dir = get_abs_path("data/knowledge")

        # 确保目录存在
        os.makedirs(self.knowledge_dir, exist_ok=True)

        # 加载或初始化元数据
        self._metadata = self._load_metadata()

    def _load_metadata(self) -> Dict:
        """加载元数据文件"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[DocumentService] 加载元数据失败: {e}")
                return {"documents": {}}
        return {"documents": {}}

    def _save_metadata(self):
        """保存元数据文件"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self._metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[DocumentService] 保存元数据失败: {e}")

    def _check_md5_exists(self, md5_hex: str) -> bool:
        """检查MD5是否已存在（兼容md5.text）"""
        # 检查md5.text
        if os.path.exists(self.md5_file):
            with open(self.md5_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip() == md5_hex:
                        return True

        # 检查元数据中的MD5
        for doc in self._metadata.get("documents", {}).values():
            if doc.get("md5_hex") == md5_hex:
                return True

        return False

    def _save_md5(self, md5_hex: str):
        """保存MD5到md5.text"""
        with open(self.md5_file, 'a', encoding='utf-8') as f:
            f.write(md5_hex + "\n")

    def generate_doc_id(self) -> str:
        """生成唯一文档ID"""
        return f"doc_{uuid.uuid4().hex[:12]}"

    def create_document_record(self,
                                original_filename: str,
                                saved_path: str,
                                md5_hex: str,
                                file_size: int) -> Dict:
        """
        创建文档记录

        Args:
            original_filename: 原始文件名
            saved_path: 保存后的文件路径
            md5_hex: 文件MD5值
            file_size: 文件大小(字节)

        Returns:
            文档记录字典
        """
        doc_id = self.generate_doc_id()

        record = {
            "doc_id": doc_id,
            "original_filename": original_filename,
            "saved_filename": os.path.basename(saved_path),
            "saved_path": saved_path,
            "md5_hex": md5_hex,
            "file_size": file_size,
            "status": "pending",
            "chunk_count": 0,
            "entity_count": 0,
            "relation_count": 0,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "processed_at": None,
            "error_message": None
        }

        self._metadata["documents"][doc_id] = record
        self._save_metadata()

        logger.info(f"[DocumentService] 创建文档记录: {doc_id}, 文件: {original_filename}")
        return record

    def update_document_status(self,
                                doc_id: str,
                                status: str,
                                chunk_count: int = 0,
                                entity_count: int = 0,
                                relation_count: int = 0,
                                error_message: Optional[str] = None):
        """
        更新文档状态

        Args:
            doc_id: 文档ID
            status: 新状态 (pending/processing/completed/failed)
            chunk_count: chunk数量
            entity_count: 实体数量
            relation_count: 关系数量
            error_message: 错误信息
        """
        if doc_id not in self._metadata.get("documents", {}):
            logger.warning(f"[DocumentService] 文档不存在: {doc_id}")
            return

        doc = self._metadata["documents"][doc_id]
        doc["status"] = status

        if status == "completed":
            doc["chunk_count"] = chunk_count
            doc["entity_count"] = entity_count
            doc["relation_count"] = relation_count
            doc["processed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 保存MD5到md5.text
            self._save_md5(doc.get("md5_hex", ""))

        if status == "failed":
            doc["error_message"] = error_message

        self._save_metadata()
        logger.info(f"[DocumentService] 更新文档状态: {doc_id} -> {status}")

    def get_document(self, doc_id: str) -> Optional[Dict]:
        """获取文档记录"""
        return self._metadata.get("documents", {}).get(doc_id)

    def list_documents(self,
                       status: Optional[str] = None,
                       page: int = 1,
                       page_size: int = 20) -> Dict:
        """
        列出文档

        Args:
            status: 状态过滤 (可选)
            page: 页码
            page_size: 每页数量

        Returns:
            包含文档列表和分页信息的字典
        """
        all_docs = list(self._metadata.get("documents", {}).values())

        # 按状态过滤
        if status:
            all_docs = [d for d in all_docs if d.get("status") == status]

        # 按创建时间倒序
        all_docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # 分页
        total = len(all_docs)
        start = (page - 1) * page_size
        end = start + page_size
        docs = all_docs[start:end]

        return {
            "documents": docs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
        }

    def delete_document(self, doc_id: str) -> bool:
        """
        删除文档记录

        Args:
            doc_id: 文档ID

        Returns:
            是否成功删除
        """
        doc = self.get_document(doc_id)
        if not doc:
            logger.warning(f"[DocumentService] 文档不存在: {doc_id}")
            return False

        # 删除文件
        saved_path = doc.get("saved_path")
        if saved_path and os.path.exists(saved_path):
            try:
                os.remove(saved_path)
                logger.info(f"[DocumentService] 删除文件: {saved_path}")
            except Exception as e:
                logger.error(f"[DocumentService] 删除文件失败: {e}")

        # 删除md5.text中的MD5记录
        md5_hex = doc.get("md5_hex")
        if md5_hex:
            self._remove_md5_from_file(md5_hex)

        # 删除元数据记录
        del self._metadata["documents"][doc_id]
        self._save_metadata()

        logger.info(f"[DocumentService] 删除文档记录: {doc_id}")
        return True

    def _remove_md5_from_file(self, md5_hex: str):
        """从md5.text中删除指定MD5"""
        if not os.path.exists(self.md5_file):
            return

        try:
            with open(self.md5_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 过滤掉要删除的MD5
            new_lines = [line for line in lines if line.strip() != md5_hex]

            with open(self.md5_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            logger.info(f"[DocumentService] 从md5.text删除MD5: {md5_hex}")
        except Exception as e:
            logger.error(f"[DocumentService] 删除MD5记录失败: {e}")

    def get_stats(self) -> Dict:
        """获取文档统计信息"""
        all_docs = list(self._metadata.get("documents", {}).values())

        stats = {
            "total": len(all_docs),
            "completed": sum(1 for d in all_docs if d.get("status") == "completed"),
            "processing": sum(1 for d in all_docs if d.get("status") == "processing"),
            "pending": sum(1 for d in all_docs if d.get("status") == "pending"),
            "failed": sum(1 for d in all_docs if d.get("status") == "failed"),
            "total_chunks": sum(d.get("chunk_count", 0) for d in all_docs),
            "total_entities": sum(d.get("entity_count", 0) for d in all_docs),
            "total_relations": sum(d.get("relation_count", 0) for d in all_docs),
            "total_size_bytes": sum(d.get("file_size", 0) for d in all_docs)
        }

        return stats

    def check_file_duplicate(self, file_path: str) -> Optional[Dict]:
        """
        检查文件是否重复

        Args:
            file_path: 文件路径

        Returns:
            如果重复，返回已存在的文档记录；否则返回None
        """
        md5_hex = get_file_md5_hex(file_path)
        if not md5_hex:
            return None

        # 检查md5.text
        if self._check_md5_exists(md5_hex):
            # 找到对应的文档记录
            for doc in self._metadata.get("documents", {}).values():
                if doc.get("md5_hex") == md5_hex:
                    return doc
            # 如果在md5.text中但不在元数据中，返回一个简单的重复提示
            return {"md5_hex": md5_hex, "status": "duplicate"}

        return None


# 全局服务实例
document_service = DocumentService()