# 智学助手（StudyMate）

> 基于 LangChain 的课程知识库问答与出题智能体，打通「上传资料 → 智能问答 → 自动出题 → 错题本 → 复习计划」的完整学习闭环。

## 项目简介

智学助手是一款面向个人学习场景的轻量化智能学习工具。用户上传课程资料后，系统自动完成文档解析、切分与向量化，构建课程专属知识库，并提供五大核心能力：

1. **上传文档（F1）**：解析 PDF / Word / Markdown / TXT，构建向量知识库；
2. **智能问答（F2）**：基于 RAG 检索增强生成，回答可溯源；
3. **自动出题（F3）**：按题型、难度、数量生成题目，客观题自动判分、简答题 AI 评分；
4. **错题本（F4）**：答错自动沉淀，支持标记掌握；
5. **复习计划（F5）**：基于错题生成 7 天复习计划。

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 语言 | Python 3.11 |
| Web 框架 | FastAPI + Uvicorn |
| AI 编排 | LangChain |
| 业务数据库 | MySQL 8.0 |
| 向量数据库 | Chroma（本地持久化） |
| LLM / Embedding | 硅基流动（SiliconFlow）OpenAI 兼容接口：`deepseek-ai/DeepSeek-V4-Flash` + `BAAI/bge-m3` |
| 前端 | 原生 HTML + CSS + JavaScript |
| 部署 | Docker + docker-compose |

## 架构设计

```mermaid
flowchart LR
    A[浏览器<br/>原生 HTML/CSS/JS] -->|HTTP / RESTful| B[FastAPI 后端]
    B --> C[(MySQL 8.0<br/>业务数据)]
    B --> D[(Chroma<br/>向量库)]
    D --> E[硅基流动 SiliconFlow<br/>LLM + Embedding]
    B --> E
```

- **MySQL** 存储课程、文档、题目、错题、复习计划等结构化数据；
- **Chroma** 存储文档向量（每个课程一个独立 collection）；
- **硅基流动** 提供 LLM（生成）与 Embedding（向量化）能力。

## 目录结构

```
langchain_agent/
├── app/
│   ├── main.py              # FastAPI 应用入口（挂载路由、静态目录、lifespan）
│   ├── config.py            # pydantic-settings 配置（读取 .env）
│   ├── core/                # 核心基础
│   │   ├── response.py      # ApiResponse 统一返回
│   │   └── exceptions.py    # 全局异常处理
│   ├── db/                  # 数据库连接
│   │   ├── base.py          # SQLAlchemy ORM 基类
│   │   ├── mysql.py         # MySQL 连接与会话
│   │   └── chroma.py        # Chroma 向量库工厂 + Embedding
│   ├── models/              # SQLAlchemy ORM 模型
│   ├── schemas/             # Pydantic v2 请求/响应 Schema
│   ├── routers/             # API 路由层（控制层）
│   ├── services/            # 业务逻辑层
│   └── prompts/             # Prompt 模板
├── static/                  # 前端静态资源（HTML/CSS/JS）
├── docs/                    # PRD / SPEC / AGENTS 规范文档
├── .env                     # 环境变量（不提交）
├── .env.example             # 环境变量样例
├── requirements.txt
├── docker-compose.yml       # MySQL 容器编排
└── README.md
```

## 快速开始

### 1. 环境要求

- Python 3.11+
- Docker（用于运行 MySQL）

### 2. 配置 .env

复制 `.env.example` 为 `.env`，并填写密钥：

```bash
# Linux / macOS
cp .env.example .env

# Windows（cmd）
copy .env.example .env
```

编辑 `.env`，至少填写：

```ini
SILICONFLOW_API_KEY=sk-你的密钥
```

其余配置（模型、MySQL、Chroma）已有合理默认值，可按需调整。

### 3. 启动 MySQL

```bash
docker-compose up -d
```

### 4. 安装依赖并启动后端

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 5. 访问

| 地址 | 说明 |
| --- | --- |
| http://127.0.0.1:8000 | 前端页面 |
| http://127.0.0.1:8000/docs | Swagger API 文档 |
| http://127.0.0.1:8000/api/health | 健康检查（MySQL / Chroma 连通性） |

## 核心功能

### F1 上传文档

- **前端**：左侧「新建课程」创建课程 → 选中课程 → 「文档管理」Tab → 点「上传文档」选择文件。
- **支持格式**：PDF、Word（.docx/.doc）、Markdown、TXT。
- **Markdown 特化切分**：按 `#/##/###` 标题两层切分，保留章节 metadata（h1/h2/h3），提升检索命中率。
- **相关 API**：`POST /api/courses/{id}/documents`、`GET /api/courses/{id}/documents`。

### F2 智能问答

- **前端**：「智能问答」Tab，输入问题回车发送，展示 AI 回答 + 引用来源卡片。
- **实现**：查询加 bge-m3 前缀 → Chroma 相似度检索（top_k）→ 拼接上下文 → LLM 生成，回答可溯源、不编造。
- **相关 API**：`POST /api/courses/{id}/chat`。

### F3 自动出题

- **前端**：「自动出题」Tab，选择题型（单选/多选/判断/简答）、难度、数量 → 生成题目卡片。
- **作答**：客观题点击选项 → 「提交答案」自动判分；简答题输入答案 → AI 语义打分（含评分与理由）。
- **相关 API**：`POST /api/courses/{id}/quizzes/generate`、`POST /api/questions/{id}/submit`。

### F4 错题本

- **前端**：「错题本」Tab，展示题干、你的答案、正确答案、解析。
- **交互**：答错自动入错题本；「标记已掌握」后从列表移除。
- **相关 API**：`GET /api/courses/{id}/mistakes`、`PATCH /api/mistakes/{id}`、`DELETE /api/mistakes/{id}`。

### F5 复习计划

- **前端**：「复习计划」Tab，点「生成复习计划」→ 按日期分组展示复习条目，勾选完成。
- **实现**：读取未掌握错题 → LLM 生成 7 天计划（只返回第 N 天，日期由 Python 计算）→ 写入 `review_plans` / `review_items`。
- **相关 API**：`POST /api/courses/{id}/review-plans`、`GET /api/courses/{id}/review-plans`、`GET /api/review-plans/{id}`、`PATCH /api/review-items/{id}`。

## 项目文档

| 文档 | 说明 |
| --- | --- |
| [docs/PRD.md](docs/PRD.md) | 产品需求文档 |
| [docs/SPEC.md](docs/SPEC.md) | 技术规范文档 |
| [AGENTS.md](AGENTS.md) | AI 编程规范 |
