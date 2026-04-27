"""
RAG总结服务类：基于健康知识库的智能问答
"""
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from rag.vector_store import VectorStoreService
from project.prompt_loader import load_rag_prompts
from project.config_hander import chroma_conf
from langchain_core.prompts import PromptTemplate
from model.factory import chat_model
from project.logger_handler import logger


class RagSummarizeService(object):
    def __init__(self):
        self.vector_store = VectorStoreService()
        # 根据配置选择retriever类型
        retriever_config = chroma_conf.get("retriever", {})
        search_type = retriever_config.get("search_type", "similarity")
        self.retriever = self.vector_store.get_retrive(search_type=search_type)
        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self._init_chain()

    def _init_chain(self):
        chain = self.prompt_template | self.model | StrOutputParser()
        return chain

    def retriever_docs(self, query: str) -> list[Document]:
        """检索相关文档"""
        docs = self.retriever.invoke(query)
        logger.info(f"[RAG] 检索到 {len(docs)} 个相关文档片段")
        return docs

    def rag_summarize(self, query: str) -> str:
        """RAG问答"""
        context_docs = self.retriever_docs(query)

        # 如果没有检索到相关文档，返回提示
        if not context_docs:
            return "抱歉，知识库中没有找到与您问题相关的资料。请尝试换一种方式提问或提供更多信息。"

        # 构建context，不添加参考资料标记
        context = ""
        for doc in context_docs:
            context += f"{doc.page_content}\n\n"

        return self.chain.invoke(
            {
                "input": query,
                "context": context,
            }
        )


if __name__ == '__main__':
    rag = RagSummarizeService()
    print(rag.rag_summarize("高血压预防方法"))
