# 健康智能助手

基于 ReAct Agent + 知识图谱 + RAG 的智能健康管理平台，通过对话式交互提供个性化健康建议、饮食分析、运动推荐等服务。

## 核心特性

- **ReAct 智能体** — 基于 LangGraph `create_react_agent`，LLM 自主推理并调用 14 个工具（BMI 计算器、饮食营养分析、运动推荐、知识图谱查询等）
- **知识图谱** — Neo4j 持久化存储，覆盖疾病、症状、药物、食物、营养素、运动等 16 种实体类型、31 种关系类型，支持 NER 动态抽取
- **KG-Enhanced RAG** — NER 实体识别 → BFS 图采样 → ChromaDB 向量检索 → 重排序 → LLM 融合生成
- **智能路由** — 规则引擎意图分类，FAQ 走 RAG 快速链路，复杂任务走 Agent 多步推理链路
- **SSE 流式对话** — token 级流式输出 + 工具调用"thinking"中间步骤推送，实时响应
- **文档知识库** — 支持 PDF/TXT 上传，后台自动分块、向量化、图谱抽取
- **动态专家提示词** — 5 种专家模式（营养分析师、运动教练、健康诊断师等）按关键词自动匹配
- **Reranker 重排序** — 基于 GTE-Rerank 模型对检索结果二次排序，提升回答质量
- **Web 集成** — 实时天气、DuckDuckGo 搜索、网页抓取

## 技术栈

| 层级 | 技术 |
|------|------|
| **Web 框架** | FastAPI + Uvicorn |
| **AI 框架** | LangChain + LangGraph (ReAct Agent) |
| **LLM** | 通义千问 Qwen-Plus (DashScope) + DeepSeek 备用 |
| **Embedding** | DashScope text-embedding-v4 |
| **向量数据库** | ChromaDB |
| **知识图谱** | Neo4j (Bolt 协议) |
| **关系数据库** | SQLAlchemy 2.0 + SQLite |
| **NER** | LLM 实体抽取 + 预定义实体词典 |
| **文档解析** | PyPDF |
| **流式输出** | SSE-Starlette |
| **前端** | 原生 HTML/CSS/JS + ECharts 5.5 |

## 架构概览

```
用户请求 → InputDenoiser(去噪) → IntentClassifier(意图分类)
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
               FAQ 链路                            Agent 链路
          (知识查询、快速回答)                 (复杂任务、多工具调用)
                    │                                   │
                    ▼                                   ▼
          NER 实体识别                         CQR 查询改写
                    │                                   │
                    ▼                                   ▼
          GraphSampler(BFS)               DynamicPromptBuilder
                    │                                   │
                    ▼                                   ▼
          ChromaDB 向量检索              ReAct Agent (LangGraph)
                    │                          │   14 个 @tool   │
                    ▼                          ▼                 ▼
          Reranker 重排序           ┌─────────────────────────┐
                    │               │  健康分析(6)  用户管理(2) │
                    ▼               │  报告查询(1)  图谱工具(2) │
          LLM 融合生成              │  网络工具(3)              │
                    │               └─────────────────────────┘
                    ▼                          │
               SSE 流式响应 ◄──────────────────┘
               (token级 + thinking事件)
```

## 快速开始

### 1. 环境要求

- Python 3.10+
- DashScope API Key（[申请地址](https://dashscope.console.aliyun.com/)）
- Neo4j 5.x（可选，知识图谱持久化；未配置时自动降级为内存模式）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 填入配置
# DASHSCOPE_API_KEY=sk-your-api-key          # 必填
# DATABASE_URL=sqlite:///data/health_assistant.db  # 默认即可
# NEO4J_URI=bolt://localhost:7687            # 可选
# NEO4J_USER=neo4j                           # 可选
# NEO4J_PASSWORD=password                    # 可选
```

或直接设置环境变量：

```bash
# Windows
set DASHSCOPE_API_KEY=your_api_key

# Linux/Mac
export DASHSCOPE_API_KEY=your_api_key
```

### 4. 启动服务

```bash
# 方式一：直接运行
python api_server.py

# 方式二：使用启动脚本
# Windows
start.bat
# Linux/Mac
bash start.sh
```

### 5. 访问

打开浏览器访问 http://localhost:7958

## 项目结构

```
├── api_server.py                  # FastAPI 入口 (端口 7958)
├── agent/
│   ├── core/
│   │   ├── health_agent.py        # ReAct 智能体 (LangGraph, 14 工具)
│   │   ├── service_registry.py    # 服务注册中心 (单例)
│   │   └── tool_manager.py        # [DEPRECATED] 工具管理器 (已迁移至 health_agent)
│   ├── router/
│   │   ├── router.py              # 智能路由 (FAQ / Agent 分流)
│   │   └── intent_classifier.py   # 意图分类器 (正则匹配)
│   ├── database/
│   │   ├── db_config.py           # 数据库连接、会话管理 (@with_session)
│   │   ├── models.py              # ORM 模型 (7 张表)
│   │   ├── neo4j_config.py        # Neo4j 连接配置
│   │   └── neo4j_kg_store.py      # Neo4j 知识图谱存储
│   ├── knowledge/
│   │   ├── health_kg.py           # 知识图谱门面 (委托 Neo4j)
│   │   ├── kg_qa.py               # 图谱问答系统
│   │   ├── ner.py                 # 命名实体识别
│   │   ├── kg_extractor.py        # 文档实体关系抽取
│   │   ├── kg_extended_data.py    # 扩展知识数据
│   │   ├── entity_types.py        # 16 种实体类型定义
│   │   └── relation_types.py      # 31 种关系类型定义
│   ├── preprocessing/
│   │   ├── input_denoiser.py      # 输入去噪
│   │   ├── query_rewriter.py      # 查询改写 (CQR)
│   │   ├── prompt_matcher.py      # 动态提示词匹配
│   │   └── dynamic_prompt_builder.py  # 动态上下文构建
│   ├── services/
│   │   ├── user_service.py        # 用户 CRUD (SQLAlchemy)
│   │   ├── health_report_service.py # 健康报告 (SQLAlchemy)
│   │   ├── chat_history_service.py  # 对话历史 (SQLAlchemy)
│   │   └── document_service.py    # 文档管理 (SQLAlchemy)
│   └── tools/
│       ├── health_tools.py        # 健康分析工具 (6 个 @tool)
│       ├── kg_tools.py            # 知识图谱工具 (2 个 @tool + 内部辅助函数)
│       ├── web_tools.py           # 网络工具 (3 个 @tool)
│       ├── health_enums.py        # 健康枚举定义
│       └── middleware.py          # ReAct 中间件 (动态提示词解析)
├── rag/
│   ├── rag_service.py             # 基础 RAG 服务
│   ├── kg_enhanced_rag.py         # KG 增强 RAG
│   ├── reranker.py                # 重排序模块 (GTE-Rerank)
│   ├── vector_store.py            # ChromaDB 向量存储
│   └── graph_sampler.py           # BFS 图采样器
├── model/
│   └── factory.py                 # 模型工厂 (ChatTongyi + Embedding)
├── prompts/                       # 提示词模板
│   ├── main_prompt.txt            # 主系统提示词 (含 ReAct 指令)
│   ├── rag_summarize.txt          # RAG 摘要提示词
│   ├── rag_summarize_kg_enhanced.txt  # KG 增强 RAG 摘要提示词
│   ├── health_diagnosis.txt       # 健康诊断提示词
│   ├── health_report.txt          # 健康报告提示词
│   └── *.md                       # 5 种专家提示词
├── config/                        # YAML 配置
│   ├── chroma.yml                 # 向量库配置 (chunk 500, k=5)
│   ├── router.yml                 # 路由规则配置
│   ├── rag.yml                    # RAG 模型 + Reranker 配置
│   ├── kg.yml                     # 图谱抽取配置
│   ├── dynamic_prompts.yml        # 动态提示词规则
│   ├── prompts.yml                # 提示词路径
│   └── agent.yml                  # Agent 配置
├── project/                       # 工具模块
│   ├── config_hander.py           # 配置加载
│   ├── prompt_loader.py           # 提示词加载 (支持 frontmatter)
│   ├── logger_handler.py          # 日志 (控制台 + 按日轮转)
│   ├── llm_client.py             # LLM 备用客户端
│   ├── file_hander.py             # 文件工具 (MD5/目录)
│   └── path_tool.py               # 路径工具
├── web/                           # 前端
│   ├── kg_index.html              # 单页应用入口
│   ├── css/                       # 样式 (暗色主题, 6 个模块)
│   └── js/                        # JS 模块 (app/chat/api/dashboard/health/analysis)
├── data/                          # 运行时数据
│   ├── health_assistant.db        # SQLite 数据库 (自动创建)
│   └── knowledge/                 # 知识库 (文档/元数据)
├── chroma_db/                     # ChromaDB 持久化
└── logs/                          # 应用日志
```

## Agent 工具（14 个 @tool）

Agent 暴露给 LLM 的 14 个工具，按职责分组：

| 分组 | 工具名 | 说明 |
|------|--------|------|
| **健康分析** | `rag_summarize` | RAG 知识检索 |
| | `calculate_bmi` | BMI 计算（含中国标准分类） |
| | `calculate_daily_calorie` | 每日热量计算（Mifflin-St Jeor） |
| | `analyze_nutrition` | 饮食营养分析（KG 优先 → 硬编码食物库回退） |
| | `recommend_exercise` | 运动方案推荐（KG 优先 → 硬编码方案回退） |
| | `assess_sleep` | 睡眠质量评估 |
| **用户管理** | `manage_user` | 统一用户管理（action: list/get/health_data/create） |
| | `add_health_record` | 添加健康记录 |
| **报告查询** | `query_health_reports` | 健康报告查询（action: list/get/search） |
| **知识图谱** | `kg_query` | 自然语言图谱问答 |
| | `kg_entity_lookup` | 实体关联查询（relation: symptoms/treatment/foods/nutrients/path） |
| **网络工具** | `get_weather` | 天气查询（自动 IP 定位 / 指定城市） |
| | `web_search` | 网络搜索 / 网页抓取（自动判断 URL vs 关键词） |
| | `get_current_datetime` | 当前日期时间 |

> 合并策略：相同模式的工具通过 `action` / `relation` 参数区分，辅助性操作（schema 查看、NER 识别）降级为内部函数不暴露给 LLM。内部辅助函数：`_get_kg_schema()`、`_recognize_entities()`、`_kg_food_nutrients()`、`_kg_exercise_for_goal()`。

## API 概览

服务启动后提供 55+ 个 API 端点，主要分为以下几组：

| 分组 | 路径前缀 | 说明 |
|------|----------|------|
| 对话 | `/api/v1/chat/stream` | SSE 流式对话（核心接口） |
| 对话历史 | `/api/v1/chat/history`、`/api/v1/chat/sessions` | 对话记录与会话管理 |
| 知识图谱 | `/api/v1/kg/*` | 图谱查询、可视化数据、NER、实体搜索、图谱编辑 |
| 知识库 | `/api/v1/knowledge/*` | 文档上传、管理、统计、KG 联合检索 |
| 用户 | `/api/v1/users/*` | 用户 CRUD、健康档案 |
| 健康 | `/api/v1/health/*` | BMI 计算、每日热量 |
| 报告 | `/api/v1/reports/*`、`/api/v1/report/generate` | 健康报告生成与管理 |
| 仪表盘 | `/api/v1/dashboard/*` | 统计数据、用户画像 |
| 路由分析 | `/api/v1/route/analyze` | 意图分类调试 |
| 天气 | `/api/v1/weather` | 实时天气查询 |
| 服务调用 | `/api/execute` | Lealone 风格统一调用接口 |

## 配置说明

主要配置文件位于 `config/` 目录：

| 文件 | 关键配置 |
|------|----------|
| `chroma.yml` | chunk_size: 500, chunk_overlap: 75, 检索 top_k: 5, 相似度阈值: 0.3 |
| `router.yml` | 意图分类正则规则、置信度阈值 |
| `rag.yml` | 对话模型 qwen-plus, Embedding 模型 text-embedding-v4, Reranker: gte-rerank-v2 |
| `kg.yml` | NER 开关、LLM 抽取开关、分块限制、置信度阈值 |
| `dynamic_prompts.yml` | 5 种专家提示词触发规则 |
| `agent.yml` | Agent 参数配置 |
| `.env` | DASHSCOPE_API_KEY、DATABASE_URL、NEO4J_URI/USER/PASSWORD、备用 API 地址（可选） |

## 许可证

MIT License
