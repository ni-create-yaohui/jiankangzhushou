# CLAUDE.md - 健康智能助手项目规范

用中文回答。所有代码实体（变量名、函数名、类名）保持英文原文，注释使用中文。

---

## 项目概览

中文 AI 健康助手，基于 FastAPI + LangChain + LangGraph 构建，提供健康问答、BMI/卡路里/饮食/运动/睡眠分析、知识图谱 KGQA、RAG 文档检索、健康报告生成等功能。

- **后端**: FastAPI (端口 7958), Python 3.10+
- **LLM**: 通义千问 (qwen-plus) via DashScope, 备用 OpenAI 兼容 API (DeepSeek)
- **Agent**: LangChain @tool + LangGraph agent (25+ 工具)
- **向量库**: ChromaDB (持久化)
- **知识图谱**: 自研内存图 HealthKG (16 实体类型, DFS 寻路, JSON 持久化)
- **前端**: 原生 HTML/CSS/JS SPA, ECharts 图谱可视化
- **数据存储**: JSON 文件 (无数据库)
- **报告生成**: python-docx + matplotlib

---

## 项目结构

```
api_server.py          # FastAPI 入口 (50+ REST 端点)
agent/
  core/                # HealthAgent, ServiceRegistry, ToolManager
  router/              # HealthRouter (FAQ/Agent 路由), IntentClassifier
  knowledge/           # HealthKG, NER, KGQA, KG 提取器
  preprocessing/       # InputDenoiser, QueryRewriter, PromptMatcher, DynamicPromptBuilder
  services/            # UserService, ChatHistoryService, DocumentService, HealthReportService
  tools/               # health_tools, kg_tools, web_tools, middleware
model/factory.py       # ChatTongyi + DashScopeEmbeddings 工厂
project/               # config_handler, prompt_loader, llm_client, logger, file utils
config/                # 6 个 YAML 配置 (rag, chroma, prompts, agent, router, dynamic_prompts)
prompts/               # 提示词模板 (.txt/.md, 支持 YAML frontmatter)
rag/                   # RAG pipeline (基础 RAG + KG 增强型 RAG)
web/                   # 前端 SPA (kg_index.html + css/js)
data/                  # 运行时 JSON 数据 (用户、聊天历史、知识库、报告)
chroma_db/             # ChromaDB 持久化数据
logs/                  # 应用日志
```

---

## 三阶段工作流（必须遵守）

每个任务严格按三阶段执行，**禁止在一次回复中执行两个或以上阶段**。

### 阶段一：【分析问题】

- 深入理解需求核心目标与边界条件
- 搜索并分析所有相关代码、配置和文档
- 识别问题真正根因，而非表面现象
- 评估对现有架构的潜在影响
- 提供 1~3 个有差异化方案，评估优劣（复杂度、性能、可扩展性、侵入性）
- **绝对禁止**: 修改任何代码

### 阶段二：【细化方案】

- 前置条件: 用户已明确选择方案
- 列出所有变更文件清单（新增/修改/删除）
- 对每个文件提供伪代码或详细描述
- 定义关键函数签名、类接口、数据结构变更
- 指出需添加的测试用例（临时测试放 `temp_tests/`，验证后删除）
- **绝对禁止**: 生成完整可运行代码

### 阶段三：【执行方案】

- 前置条件: 用户已批准细化方案
- 检查并激活 venv 虚拟环境 (`.\venv\Scripts\activate`)
- 严格按细化方案实现代码
- 执行质量检查 (格式化、lint、类型检查、测试)
- 清理临时测试目录
- **绝对禁止**: 超出方案范围 (YAGNI)、全局环境操作、自行提交代码、启动开发服务器

---

## 编码规范

### Python 规范

- **类型注解**: 所有函数和方法必须添加类型注解
- **PEP 8**: 严格遵守，使用 black 格式化、isort 排序导入
- **文档字符串**: 公共函数和类必须有中文 docstring (PEP 257)
- **虚拟环境**: 必须使用 venv，禁止全局环境安装依赖
- **异步**: 异步函数使用 async/await，不使用回调
- **禁止 `pass` 作为功能实现**: 所有代码必须具备真实逻辑
- **日志**: 使用 `logging.getLogger(__name__)`，前后加日志用于调试

### 前端规范

- 代码实体英文，注释中文
- 移动优先响应式设计
- 交互元素需有 ARIA 标签和键盘导航支持
- 合理使用代码分割和懒加载

### 通用规范

- DRY: 消除任何形式的重复（代码、逻辑、配置）
- KISS: 优先选择最简单直接的方案
- DDD: 按业务领域组织代码结构（agent/knowledge, agent/services, agent/tools）
- TDD: 使用 pytest，核心业务逻辑覆盖率 90%+

---

## 关键设计模式

| 模式 | 说明 |
|------|------|
| **模块级单例** | `health_agent`, `health_router`, `health_kg`, `service_registry` 等均为模块级实例 |
| **ServiceRegistry** | Lealone 风格中心化注册表，统一 `execute()` 调用接口 |
| **意图路由** | Regex 匹配将查询分为 "faq" (KG+RAG 快速路径) 或 "agent" (完整 LangGraph agent) |
| **预处理管道** | InputDenoiser → QueryRewriter → PromptMatcher → DynamicPromptBuilder |
| **KG 增强型 RAG** | NER 实体提取 → 图谱子图采样 → 向量检索 → LLM 生成 |
| **FallbackLLM** | 异步 OpenAI 客户端，主 API 失败自动切换备用 API，指数退避重试 |
| **JSON 文件存储** | 无数据库，所有数据持久化为 JSON 文件 |

---

## 请求处理流程

```
用户输入 → InputDenoiser → IntentClassifier
  ├─ FAQ: KGQA / KGEnhancedRAG → SSE 流式响应
  └─ Agent: QueryRewriter → PromptMatcher → DynamicPromptBuilder
           → HealthAgent (25+ tools) → Middleware → SSE 流式响应
```

---

## 常用命令

```bash
# 激活虚拟环境
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务 (端口 7958)
python api_server.py

# 测试
pytest
pytest --cov=agent --cov-report=html

# 代码检查
black . && isort .
pylint agent/ model/ project/ rag/
mypy agent/ model/ project/ rag/
```

---

## 配置文件

| 文件 | 用途 |
|------|------|
| `config/rag.yml` | LLM 模型名 (qwen-plus, text-embedding-v4) |
| `config/chroma.yml` | ChromaDB: collection, chunk size 300, overlap 30, k=5 |
| `config/prompts.yml` | 提示词文件路径 |
| `config/agent.yml` | Agent 数据路径 |
| `config/router.yml` | 意图路由: patterns, keywords, thresholds |
| `config/dynamic_prompts.yml` | 预处理: 去噪, CQR, 5 个专家提示规则, 动态上下文 |

环境变量: `.env` 文件中设置 `DASHSCOPE_API_KEY`（必填）和备用 API 配置。

---

## 开发额外要求

- 每次确认规范后将具体计划写成 md 文档保存
- 每次计划完成后写开发日志 (md 文档)
- 每次计划完成时检查潜在 bug（内存泄漏、索引问题等）
- 超过 10k token 的内容需切块 (chunk) 处理
- 通过在功能前后加日志输出进行调试测试
- 对输入输出进行核验
