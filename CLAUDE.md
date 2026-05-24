# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

健康智能助手 — 基于 ReAct Agent + 知识图谱 + RAG 的智能健康管理平台。FastAPI 后端 (端口 7958)，原生 HTML/JS 单页前端。全中文代码库（注释、提示词、UI 均为中文）。

## Commands

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量（复制并编辑）
cp .env.example .env
# 必填：DASHSCOPE_API_KEY
# 可选：FALLBACK_API_KEY, FALLBACK_BASE_URL, FALLBACK_MODEL, NEO4J_*

# 启动服务
python api_server.py
# 或：python -m uvicorn api_server:app --host 0.0.0.0 --port 7958 --reload

# Windows 启动脚本
start.bat

# 访问：http://localhost:7958
```

暂无测试套件和 linter 配置。

## Architecture

### Request Flow

用户输入 → `InputDenoiser` → `IntentClassifier`（基于正则） → 两条路径：

- **FAQ 路径**（知识查询）：`NER` → `GraphSampler`（BFS）→ `ChromaDB` 向量检索 → `Reranker` → `KGEnhancedRAG` LLM 融合生成 → SSE 响应
- **Agent 路径**（复杂任务）：`QueryRewriter`（CQR）→ `DynamicPromptBuilder` → `ReAct Agent`（LangGraph `create_react_agent`）携带 31 个工具 → SSE 响应

### Key Modules

- **`api_server.py`** — FastAPI 入口，40+ 端点。处理 SSE 流式、文件上传、服务调用。通过 lifespan 上下文初始化 DB/Neo4j。
- **`agent/core/health_agent.py`** — 通过 `langgraph.prebuilt.create_react_agent` 创建 ReAct 智能体。Agent 带缓存，仅在 system prompt 变化时重建。异步流式使用 `astream(stream_mode=["messages","updates"], version="v2")` 实现 token 级输出 + 工具调用 "thinking" 事件。
- **`agent/router/router.py`** — `HealthRouter` 分发 FAQ 和 Agent 路径。`route_stream_async()` 是 SSE 端点的主要接口。
- **`agent/core/service_registry.py`** — 单例注册中心，映射 `service_name.method_name` → handler 可调用对象。供 `/api/execute` 端点进行 Lealone 风格统一服务调用。
- **`agent/core/tool_manager.py`** — 管理工具前端展示名，用于 "thinking" 指示器。
- **`rag/kg_enhanced_rag.py`** — 核心 RAG 流水线：NER 实体抽取 → `GraphSampler` BFS 子图 → ChromaDB 检索 → GTE-Rerank → LLM chain（`PromptTemplate | model | StrOutputParser`）。支持同步和异步流式接口。
- **`model/factory.py`** — 创建 `ChatTongyi`（DashScope）和 `DashScopeEmbeddings` 单例。通过 `FALLBACK_*` 环境变量配置可选备用客户端。

### Data Layer

- **SQLite** — 通过 SQLAlchemy 2.0（`agent/database/db_config.py`）。7 个 ORM 模型在 `agent/database/models.py`。服务层使用 `@with_session` 装饰器自动管理 session。FastAPI 路由使用 `get_db()` 依赖。
- **ChromaDB** — 向量存储（`rag/vector_store.py`），持久化在 `chroma_db/`。配置在 `config/chroma.yml`。
- **Neo4j** — 知识图谱（`agent/database/neo4j_kg_store.py`），可选 — 未配置时优雅降级为内存模式。通过 `NEO4J_*` 环境变量配置。

### Knowledge Graph

- 16 种实体类型定义在 `agent/knowledge/entity_types.py`，31 种关系类型在 `agent/knowledge/relation_types.py`
- `agent/knowledge/health_kg.py` — 门面模式，可用时委托给 Neo4j 存储
- `agent/knowledge/ner.py` — 基于实体词典匹配的 NER（可选使用 jieba/thulac 分词器）
- `agent/knowledge/kg_extractor.py` — 基于 LLM 的文档实体/关系抽取

### Configuration

所有 YAML 配置在导入时由 `project/config_hander.py` 加载（模块级副作用）：
- `config/rag.yml` — LLM 模型名称、reranker 设置
- `config/chroma.yml` — chunk size/overlap、检索参数
- `config/router.yml` — 意图分类规则
- `config/dynamic_prompts.yml` — 专家提示词匹配规则
- `config/kg.yml` — 图谱抽取设置

### Preprocessing Pipeline

`agent/preprocessing/` 包含四个阶段，从 `dynamic_prompts.yml` 初始化：
1. `input_denoiser.py` — 输入去噪
2. `query_rewriter.py` — CQR（对话查询改写），解决指代消解
3. `prompt_matcher.py` — 将查询匹配到 5 种专家提示词模式（营养分析师、运动教练等）
4. `dynamic_prompt_builder.py` — 组装最终系统提示词，融合匹配的专家上下文

### Path Resolution

`project/path_tool.py` 将所有路径解析为相对于项目根目录（`project/` 的上两级目录）。`project/config_hander.py` 中的配置加载器使用 `get_abs_path()`。

### Prompts

`prompts/` 中的文本模板由 `project/prompt_loader.py` 加载（支持 frontmatter）。`main_prompt.txt` 包含基础 ReAct 系统提示词。Markdown 文件（`.md`）为专家模式提示词。

### Global Singletons

许多模块在模块级别导出已初始化的单例：`health_agent`、`health_router`、`service_registry`、`health_kg`、`kg_qa`、`chat_model`、`embed_model`、`chroma_conf`、`rag_conf` 等。可直接导入使用。

## Key Conventions

- 所有工具函数使用 LangChain 的 `@tool` 装饰器，并在 `tool_manager`（展示名）和 `service_registry`（执行处理器）中双重注册
- SSE 事件协议：`router:intent`、`router:graph_data`、`thinking`、`message`、`error`、`done`
- Agent 递归限制：10（5 次工具调用 + 5 轮 LLM 推理）
- `db_config.py` 中的 `with_session` 装饰器管理 session 生命周期 — 服务接受可选 `session` kwarg 以参与外部事务
- 前端为 `web/kg_index.html` 单文件，JS 模块化在 `web/js/`

## Development Standards（开发代码规范）

本仓库附带 `开发代码规范/` 目录，包含详细的编码标准。以下是必须遵守的要点：

### 语言与沟通

- 默认使用**简体中文**进行所有交流、解释和思考过程的陈述
- 所有代码实体（变量名、函数名、类名等）及技术术语保持**英文原文**
- 代码注释使用**中文**，遵循 PEP 257 文档字符串规范
- 所有函数和方法必须添加**类型注解**（Type Hints）

### 三阶段工作流

1. **【分析问题】** — 深入理解需求，搜索分析相关代码/配置/文档，识别根因，提供 1~3 个有差异化的解决方案并评估优劣。此阶段禁止修改任何代码。
2. **【细化方案】** — 用户选定方案后，列出所有需要变更的文件清单，提供伪代码或详细描述，定义关键接口签名，规划测试用例。此阶段禁止生成完整可运行代码。
3. **【执行方案】** — 用户批准细化方案后，严格按照计划实现代码，执行质量检查，报告检查结果。禁止实现超出方案范围的功能（YAGNI）。

### 编码原则

- **DRY** — 通过函数、类、模块和装饰器消除重复
- **高内聚，低耦合** — 利用模块系统和包结构实现清晰组织
- **KISS** — 优先选择最简单、最直接的方案
- **禁止伪造实现** — 严禁使用 `pass` 作为功能实现，所有代码必须具备真实逻辑
- **禁止 `any` 类型** — 所有类型注解必须精确

### Debug 技巧

- 通过在功能前后使用**日志输出**进行功能调试测试
- 对**输入输出进行核验**
- 对超过 10k token 的行为需要进行**切块（chunk）**来处理
- 每次计划完成后需对可能存在的 bug（如内存泄漏、数据库索引）进行 debug 检查

### 项目维护

- 严格遵守 **PEP 8** 代码风格，使用 black 进行格式化
- 使用 **isort** 进行导入语句排序和分组
- 所有公共函数和类必须有**详细的文档字符串**
- 定期清理未使用的导入和变量
