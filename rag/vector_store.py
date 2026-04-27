from langchain_core.documents import Document

from project.config_hander import chroma_conf
from model.factory import embed_model
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
from project.path_tool import get_abs_path
from project.logger_handler import logger
from project.file_hander import listdir_with_allowed_type, get_file_md5_hex
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from typing import Dict, List, Optional, Any


class VectorStoreService:
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=chroma_conf["persist_directory"],
        )

        self.spiliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
        )

        # 加载retriever配置
        self._retriever_config = chroma_conf.get("retriever", {})
        self._default_k = self._retriever_config.get("k", 5)

    def get_retrive(self, search_type: str = None, k: int = None):
        """
        获取retriever实例

        Args:
            search_type: 搜索类型 ("similarity", "similarity_score_threshold", "mmr")
            k: 返回文档数量（默认使用配置值）

        Returns:
            retriever实例
        """
        # 使用传入参数或配置默认值
        if search_type is None:
            search_type = self._retriever_config.get("search_type", "similarity")
        if k is None:
            k = self._retriever_config.get("k", self._default_k)

        # 构建search_kwargs
        if search_type == "similarity":
            # 简单相似度搜索
            search_kwargs = {"k": k}

        elif search_type == "similarity_score_threshold":
            # 带阈值过滤的相似度搜索
            score_threshold = self._retriever_config.get("score_threshold", 0.3)
            search_kwargs = {
                "k": k,
                "score_threshold": score_threshold
            }

        elif search_type == "mmr":
            # MMR检索（提高多样性）
            fetch_k = self._retriever_config.get("fetch_k", 20)
            lambda_mult = self._retriever_config.get("lambda_mult", 0.5)
            search_kwargs = {
                "k": k,
                "fetch_k": fetch_k,
                "lambda_mult": lambda_mult
            }

        else:
            # 默认使用相似度搜索
            search_kwargs = {"k": k}

        logger.info(f"[Retriever] 创建retriever: search_type={search_type}, kwargs={search_kwargs}")
        return self.vector_store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )

    def load_single_document(self, file_path: str, doc_id: str) -> int:
        """
        加载单个文档到向量库

        Args:
            file_path: 文件路径
            doc_id: 文档ID

        Returns:
            chunk数量
        """
        def get_file_documents(read_path: str):
            if read_path.endswith(".txt"):
                return TextLoader(read_path, encoding='utf-8').load()
            if read_path.endswith(".pdf"):
                return PyPDFLoader(read_path).load()
            return []

        try:
            documents: list[Document] = get_file_documents(file_path)

            if not documents:
                logger.warning(f"[加载文档]{file_path}内容没有有效文本内容")
                return 0

            # 为每个文档添加doc_id元数据
            for doc in documents:
                doc.metadata["doc_id"] = doc_id
                doc.metadata["source_file"] = os.path.basename(file_path)

            split_document: list[Document] = self.spiliter.split_documents(documents)

            if not split_document:
                logger.warning(f"[加载文档]{file_path}分片后没有有效内容")
                return 0

            self.vector_store.add_documents(split_document)
            logger.info(f"[加载文档]{file_path}加载成功, chunk数量: {len(split_document)}")
            return len(split_document)

        except Exception as e:
            logger.error(f"[加载文档]{file_path}加载失败, {str(e)}", exc_info=True)
            raise

    def delete_by_doc_id(self, doc_id: str) -> int:
        """
        根据doc_id删除向量库中的所有chunks

        Args:
            doc_id: 文档ID

        Returns:
            删除的chunk数量
        """
        try:
            # 获取该doc_id的所有文档
            collection = self.vector_store._collection
            results = collection.get(where={"doc_id": doc_id})

            if not results or not results.get("ids"):
                logger.info(f"[删除文档]doc_id={doc_id} 没有找到对应的chunks")
                return 0

            ids_to_delete = results["ids"]
            count = len(ids_to_delete)

            if count > 0:
                collection.delete(ids=ids_to_delete)
                logger.info(f"[删除文档]doc_id={doc_id} 删除了 {count} 个chunks")

            return count

        except Exception as e:
            logger.error(f"[删除文档]doc_id={doc_id} 删除失败, {str(e)}", exc_info=True)
            raise

    def load_document(self):
        def check_md5_hex(md5_for_check:str):
            if not(os.path.exists(get_abs_path(chroma_conf["md5_hex_store"]))):
                open(get_abs_path(chroma_conf["md5_hex_store"]), "w", encoding="utf-8").close()
                return False

            with open(get_abs_path(chroma_conf["md5_hex_store"]), "r", encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line == md5_for_check:
                        return True
                return False

        def save_md5_hex(md5_for_check:str):
            with open(get_abs_path(chroma_conf["md5_hex_store"]), "a", encoding="utf-8") as f:
                f.write(md5_for_check + "\n")

        def get_file_documents(read_path:str):
            if read_path.endswith(".txt"):
                return TextLoader(read_path, encoding='utf-8').load()
            if read_path.endswith(".pdf"):
                return PyPDFLoader(read_path).load()
            return []

        allowed_file_path = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        for path in allowed_file_path:
            md5_hex = get_file_md5_hex(path)

            if check_md5_hex(md5_hex):
                logger.info(f"[加载知识库]{path}内容已存在知识库内，跳过")
                continue
            try:
                documents:list[Document] = get_file_documents(path)

                if not documents:
                    logger.warning(f"[加载知识库]{path}内容没有有效文本内容，跳过")
                    continue

                split_document:list[Document] = self.spiliter.split_documents(documents)

                if not split_document:
                    logger.warning(f"[加载知识库]{path}分片后没有有效内容，跳过")
                    continue

                self.vector_store.add_documents(split_document)
                save_md5_hex(md5_hex)
                logger.info(f"[加载知识库]{path}内容加载成功")
            except Exception as e:
                logger.error(f"[加载知识库]{path}加载失败,{str(e)}", exc_info=True)
                continue

    def load_single_document_with_kg(
        self,
        file_path: str,
        doc_id: str,
        extraction_results: Optional[Dict] = None
    ) -> int:
        """
        加载单个文档到向量库（带图谱元数据）

        Args:
            file_path: 文件路径
            doc_id: 文档ID
            extraction_results: 图谱抽取结果 {"entities": [...], "relations": [...]}

        Returns:
            chunk数量
        """
        def get_file_documents(read_path: str):
            if read_path.endswith(".txt"):
                return TextLoader(read_path, encoding='utf-8').load()
            if read_path.endswith(".pdf"):
                return PyPDFLoader(read_path).load()
            return []

        try:
            documents: list[Document] = get_file_documents(file_path)

            if not documents:
                logger.warning(f"[加载文档KG]{file_path}内容没有有效文本内容")
                return 0

            # 为每个文档添加doc_id元数据
            for doc in documents:
                doc.metadata["doc_id"] = doc_id
                doc.metadata["source_file"] = os.path.basename(file_path)

            # 添加图谱元数据
            if extraction_results:
                kg_entities = extraction_results.get("entities", [])
                kg_relations = extraction_results.get("relations", [])

                for doc in documents:
                    doc.metadata["kg_entities"] = [e.get("name", "") for e in kg_entities]
                    doc.metadata["kg_relations"] = [
                        f"{r.get('entity1', '')}-{r.get('relation', '')}-{r.get('entity2', '')}"
                        for r in kg_relations
                    ]
                    doc.metadata["kg_entity_count"] = len(kg_entities)
                    doc.metadata["kg_relation_count"] = len(kg_relations)

            split_document: list[Document] = self.spiliter.split_documents(documents)

            if not split_document:
                logger.warning(f"[加载文档KG]{file_path}分片后没有有效内容")
                return 0

            self.vector_store.add_documents(split_document)
            logger.info(f"[加载文档KG]{file_path}加载成功, chunk数量: {len(split_document)}, KG实体: {len(extraction_results.get('entities', []) if extraction_results else [])}")
            return len(split_document)

        except Exception as e:
            logger.error(f"[加载文档KG]{file_path}加载失败, {str(e)}", exc_info=True)
            raise

    def search_with_kg_context(
        self,
        query: str,
        k: int = 5,
        include_kg: bool = True
    ) -> Dict:
        """
        搜索向量库并返回图谱上下文

        Args:
            query: 查询文本
            k: 返回数量
            include_kg: 是否包含图谱信息

        Returns:
            {
                "chunks": [...],
                "kg_entities": [...],
                "kg_relations": [...],
                "kg_context": "图谱上下文文本"
            }
        """
        try:
            retriever = self.vector_store.as_retriever(search_kwargs={"k": k})
            docs = retriever.invoke(query)

            chunks = []
            all_kg_entities: set = set()
            all_kg_relations: set = set()

            for doc in docs:
                chunk_data = {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                chunks.append(chunk_data)

                if include_kg:
                    entities = doc.metadata.get("kg_entities", [])
                    relations = doc.metadata.get("kg_relations", [])
                    all_kg_entities.update(entities)
                    all_kg_relations.update(relations)

            # 构建图谱上下文文本
            kg_context = ""
            if all_kg_entities:
                kg_context += f"相关实体: {', '.join(all_kg_entities)}\n"
            if all_kg_relations:
                kg_context += f"相关关系: {', '.join(all_kg_relations)}\n"

            return {
                "chunks": chunks,
                "kg_entities": list(all_kg_entities),
                "kg_relations": list(all_kg_relations),
                "kg_context": kg_context,
                "total_chunks": len(chunks)
            }

        except Exception as e:
            logger.error(f"[搜索KG上下文]失败: {str(e)}", exc_info=True)
            return {"chunks": [], "kg_entities": [], "kg_relations": [], "kg_context": "", "total_chunks": 0}
