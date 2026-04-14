项目结构

├── api_server.py              # FastAPI 服务入口 (端口7958)
├── agent/
│   ├── core/
│   │   ├── health_agent.py        # 健康智能体
│   │   ├── service_registry.py    # 服务注册中心
│   │   └── tool_manager.py        # 工具管理器
│   ├── router/                    # 智能路由模块 ★新增
│   │   ├── intent_classifier.py   # 意图分类器
│   │   └── router.py              # 核心路由器
│   ├── knowledge/
│   │   ├── entity_types.py        # 实体类型定义 (15种)
│   │   ├── relation_types.py      # 关系类型定义
│   │   ├── health_kg.py           # 知识图谱存储
│   │   ├── kg_qa.py               # 图谱问答系统
│   │   ├── ner.py                 # 命名实体识别
│   │   ├── kg_extractor.py        # 实体关系抽取 ★新增
│   │   └── kg_extended_data.py    # 扩展图谱数据 ★新增
│   ├── services/
│   │   ├── user_service.py        # 用户CRUD服务
│   │   ├── health_report_service.py # 健康报告服务
│   │   ├── chat_history_service.py  # 对话历史服务
│   │   └── document_service.py      # 文档管理服务 ★新增
│   └── tools/
│       ├── health_tools.py        # 健康分析工具
│       ├── health_enums.py        # 健康枚举定义
│       ├── kg_tools.py            # KG工具封装
│       └── web_tools.py           # 网络工具
├── prompts/
│   ├── main_prompt.txt            # 主提示词
│   ├── rag_summarize_prompt.txt   # RAG摘要提示词
│   ├── report_prompt.txt          # 报告生成提示词
│   └── *.md                       # 专家提示词
├── config/
│   ├── chroma.yml                 # 向量库配置
│   ├── router.yml                 # 路由配置 ★新增
│   └── model.yml                  # 模型配置
├── data/
│   ├── health_data/               # 用户健康数据
│   ├── health_reports/            # 健康知识报告
│   ├── chat_history/              # 对话历史
│   └── knowledge/                 # 知识库数据 ★新增
│       ├── document_metadata.json # 文档元数据
│       └── kg_data.json           # 图谱持久化数据
├── model/                         # 模型工厂（通义千问）
├── rag/
│   ├── rag_service.py             # RAG问答服务
│   └── vector_store.py            # 向量存储服务
├── web/
│   ├── kg_index.html              # 知识图谱前端
│   └── js/                        # JavaScript模块
│       ├── app.js, chat.js, api.js, dashboard.js, etc.
├── project/                       # 工具模块
│   ├── config_hander.py           # 配置处理
│   ├── prompt_loader.py           # 提示词加载
│   ├── logger_handler.py          # 日志处理
│   ├── file_hander.py             # 文件处理
│   ├── path_tool.py               # 路径工具
│   └── llm_client.py              # LLM客户端
└── requirements.txt



快速开始

 1. 安装依赖
pip install -r requirements.txt
2. 配置环境变量
# Windows
set DASHSCOPE_API_KEY=your_api_key

# Linux/Mac
export DASHSCOPE_API_KEY=your_api_key
3. 运行应用
4. 访问
打开浏览器访问 http://localhost:7958  python api_server.py
