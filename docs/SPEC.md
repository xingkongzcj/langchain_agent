# 智学助手 —— 技术规范文档（SPEC）

> 项目名称：智学助手（StudyMate）
> 关联文档：`docs/PRD.md`
> 文档版本：v1.0
> 更新日期：2026-09-26

---

## 1. 系统架构

### 1.1 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                        浏览器（前端）                          │
│          原生 HTML / CSS / JS（static 目录静态页面）            │
│       课程管理 / 上传文档 / 问答 / 出题 / 错题本 / 复习计划      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (RESTful, JSON / multipart)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 应用（后端）                        │
│  ┌───────────┐  ┌───────────────┐  ┌─────────────────────┐  │
│  │  Routers   │→│   Services     │→│   LangChain 编排     │  │
│  │ (API 路由) │  │ (业务逻辑)      │  │ 加载/切分/检索/出题   │  │
│  └───────────┘  └───────┬───────┘  └──────────┬──────────┘  │
└──────────────────────────┼─────────────────────┼────────────┘
                           │                     │
              ┌────────────▼──────┐    ┌─────────▼──────────────┐
              │  MySQL 8.0        │    │ PostgreSQL + pgvector  │
              │ 课程/文档/题目/    │    │ 文档向量 + 聊天记忆     │
              │ 错题/复习计划      │    └────────────────────────┘
              └───────────────────┘
                           │
              ┌────────────▼──────────────────────────┐
              │  硅基流动 SiliconFlow（OpenAI 兼容接口）  │
              │  LLM：Qwen 系列   Embedding：BAAI/bge-m3│
              └───────────────────────────────────────┘
```

### 1.2 数据库分工

| 数据库 | 职责 | 关键表 |
| --- | --- | --- |
| MySQL 8.0 | 业务结构化数据 | courses、documents、quiz_batches、questions、mistakes、review_plans、review_items |
| PostgreSQL + pgvector | 向量存储 + 聊天记忆 | document_embeddings（向量表）、chat_messages（会话记忆） |

### 1.3 关键数据流

**文档入库**：上传文件 → 类型/大小校验 → LangChain Loader 解析 → TextSplitter 切分 → Embedding 向量化 → 写入 PostgreSQL（pgvector）→ 写入 MySQL（documents）。

**智能问答**：提问 → Embedding 向量化 → pgvector 相似度检索（top_k）→ 拼接上下文 → 填充 Prompt → LLM 生成 → 返回回答 + 引用来源。

**自动出题**：出题参数 → pgvector 检索相关片段 → 填充出题 Prompt → LLM 生成结构化 JSON → 解析校验 → 写入 MySQL（questions）→ 返回。

**错题本**：判题答错 → 写入 MySQL（mistakes）→ 供错题本与复习计划使用。

**复习计划**：错题/知识库内容 → 生成计划 → 写入 MySQL（review_plans / review_items）。

## 2. 技术选型与理由

| 组件 | 选型 | 理由 |
| --- | --- | --- |
| 语言 | Python 3.11 | 稳定、性能与生态均衡，符合项目规范要求 |
| Web 框架 | FastAPI | 异步高性能、原生 Pydantic v2 校验、自动生成 OpenAPI 文档 |
| AI 编排 | LangChain | 内置文档 Loader、TextSplitter、向量库、Prompt 模板等 RAG 抽象 |
| 业务库 | MySQL 8.0 | 成熟稳定，适合关系型结构化业务数据 |
| 向量库 | PostgreSQL + pgvector | 一个库同时承载向量检索与聊天记忆，减少组件数量 |
| LLM/Embedding | SiliconFlow OpenAI 兼容接口 | 国内直连、按量付费，LLM（Qwen）+ Embedding（BAAI/bge-m3）统一接入 |
| 前端 | 原生 HTML/CSS/JS | 无构建工具、无框架依赖 |
| 部署 | Docker + docker-compose | MySQL、PostgreSQL、Backend 一键编排启动 |

## 3. 数据库表设计

### 3.1 MySQL 业务库（`study_mate`）

#### courses（课程表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PRIMARY KEY AUTO_INCREMENT | 课程 ID |
| name | VARCHAR(255) | NOT NULL | 课程名称 |
| description | TEXT | 可空 | 课程描述 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

#### documents（文档表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PRIMARY KEY AUTO_INCREMENT | 文档 ID |
| course_id | BIGINT | NOT NULL，FK → courses.id | 所属课程 |
| filename | VARCHAR(512) | NOT NULL | 原始文件名 |
| file_type | VARCHAR(32) | 可空 | 扩展名（pdf/docx/md/txt） |
| file_size | BIGINT | 可空 | 文件大小（字节） |
| chunk_count | INT | DEFAULT 0 | 切分块数 |
| status | VARCHAR(32) | DEFAULT 'processing' | processing / completed / failed |
| error | TEXT | 可空 | 失败原因 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

#### quiz_batches（出题批次表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PRIMARY KEY AUTO_INCREMENT | 批次 ID |
| course_id | BIGINT | NOT NULL，FK → courses.id | 所属课程 |
| topic | VARCHAR(255) | 可空 | 出题主题/范围 |
| question_type | VARCHAR(32) | NOT NULL | single / multiple / judge / short / mixed |
| difficulty | VARCHAR(16) | DEFAULT 'medium' | easy / medium / hard |
| count | INT | NOT NULL | 题目数量 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

#### questions（题目表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PRIMARY KEY AUTO_INCREMENT | 题目 ID |
| batch_id | BIGINT | NOT NULL，FK → quiz_batches.id | 所属批次 |
| course_id | BIGINT | NOT NULL，FK → courses.id | 所属课程 |
| type | VARCHAR(32) | NOT NULL | single / multiple / judge / short |
| question | TEXT | NOT NULL | 题干 |
| options | JSON | 可空 | 选项数组 |
| answer | VARCHAR(255) | 可空 | 正确答案 |
| explanation | TEXT | 可空 | 解析 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

#### mistakes（错题本表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PRIMARY KEY AUTO_INCREMENT | 错题 ID |
| course_id | BIGINT | NOT NULL，FK → courses.id | 所属课程 |
| question_id | BIGINT | NOT NULL，FK → questions.id | 关联题目 |
| user_answer | VARCHAR(255) | NOT NULL | 用户答案 |
| status | VARCHAR(16) | DEFAULT 'unmastered' | unmastered / mastered |
| review_count | INT | DEFAULT 0 | 复习次数 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 加入时间 |
| updated_at | DATETIME | ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

#### review_plans（复习计划表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PRIMARY KEY AUTO_INCREMENT | 计划 ID |
| course_id | BIGINT | NOT NULL，FK → courses.id | 所属课程 |
| name | VARCHAR(255) | NOT NULL | 计划名称 |
| description | TEXT | 可空 | 计划说明 |
| status | VARCHAR(16) | DEFAULT 'active' | active / completed |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

#### review_items（复习条目表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGINT | PRIMARY KEY AUTO_INCREMENT | 条目 ID |
| plan_id | BIGINT | NOT NULL，FK → review_plans.id | 所属计划 |
| question_id | BIGINT | 可空，FK → questions.id | 关联题目（错题复习） |
| knowledge_point | VARCHAR(512) | 可空 | 知识点描述 |
| review_date | DATE | NOT NULL | 计划复习日期 |
| completed | TINYINT(1) | DEFAULT 0 | 是否完成 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

### 3.2 PostgreSQL（`study_mate`）

#### document_embeddings（文档向量表，pgvector）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGSERIAL | PRIMARY KEY | 向量 ID |
| course_id | BIGINT | NOT NULL，索引 | 所属课程 |
| document_id | BIGINT | NOT NULL，索引 | 对应 MySQL documents.id |
| chunk_index | INT | NOT NULL | 块序号 |
| content | TEXT | NOT NULL | 文本片段 |
| embedding | vector(1024) | NOT NULL | 向量（BAAI/bge-m3，1024 维） |
| metadata | JSONB | 可空 | 附加元数据 |
| created_at | TIMESTAMPTZ | DEFAULT now() | 创建时间 |

> 索引：`CREATE INDEX ON document_embeddings USING ivfflat (embedding vector_cosine_ops);`（或 HNSW）

#### chat_messages（聊天记忆表）

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | BIGSERIAL | PRIMARY KEY | 消息 ID |
| session_id | VARCHAR(64) | NOT NULL，索引 | 会话 ID |
| course_id | BIGINT | NOT NULL，索引 | 所属课程 |
| role | VARCHAR(16) | NOT NULL | user / assistant |
| content | TEXT | NOT NULL | 消息内容 |
| created_at | TIMESTAMPTZ | DEFAULT now() | 创建时间 |

## 4. API 接口设计（RESTful）

统一前缀 `/api`；所有接口统一返回 `ApiResponse` 格式（见 4.7）。

### 4.1 课程管理

| 方法 | 路径 | 说明 | 请求 | 响应 data |
| --- | --- | --- | --- | --- |
| GET | `/api/courses` | 课程列表 | - | `[{id,name,description,doc_count,created_at}]` |
| POST | `/api/courses` | 创建课程 | `{name, description?}` | `{id,name,description,created_at}` |
| GET | `/api/courses/{course_id}` | 课程详情 | - | `{id,name,description,documents:[...],created_at}` |
| DELETE | `/api/courses/{course_id}` | 删除课程 | - | `{message}` |

### 4.2 上传文档

| 方法 | 路径 | 说明 | 请求 | 响应 data |
| --- | --- | --- | --- | --- |
| POST | `/api/courses/{course_id}/documents` | 上传文档 | `multipart/form-data`，字段 `file` | `{id,filename,file_type,file_size,chunk_count,status}` |
| GET | `/api/courses/{course_id}/documents` | 文档列表 | - | `[{id,filename,file_type,chunk_count,status,created_at}]` |
| DELETE | `/api/documents/{document_id}` | 删除文档 | - | `{message}` |

### 4.3 智能问答

| 方法 | 路径 | 说明 | 请求 | 响应 data |
| --- | --- | --- | --- | --- |
| POST | `/api/courses/{course_id}/chat` | RAG 问答 | `{question, session_id?}` | `{answer, sources:[{filename,text}]}` |

### 4.4 自动出题

| 方法 | 路径 | 说明 | 请求 | 响应 data |
| --- | --- | --- | --- | --- |
| POST | `/api/courses/{course_id}/quizzes/generate` | 生成题目 | `{topic?,question_type,difficulty?,count}` | `{batch_id,questions:[...]}` |
| GET | `/api/courses/{course_id}/quizzes` | 题目列表 | 可选 `?batch_id=` | `[{id,type,question,options,answer,explanation}]` |
| GET | `/api/quizzes/batches/{batch_id}` | 批次详情 | - | `{id,course_id,question_type,difficulty,count,questions:[...]}` |

### 4.5 判题与错题本

| 方法 | 路径 | 说明 | 请求 | 响应 data |
| --- | --- | --- | --- | --- |
| POST | `/api/questions/{question_id}/submit` | 提交答案并判题 | `{user_answer}` | `{correct,correct_answer,explanation,mistake_id?}` |
| GET | `/api/courses/{course_id}/mistakes` | 错题本列表 | `?status=` | `[{id,question,user_answer,correct_answer,explanation,status}]` |
| PATCH | `/api/mistakes/{mistake_id}` | 标记掌握 | `{status}` | `{id,status}` |
| DELETE | `/api/mistakes/{mistake_id}` | 移除错题 | - | `{message}` |

### 4.6 复习计划

| 方法 | 路径 | 说明 | 请求 | 响应 data |
| --- | --- | --- | --- | --- |
| POST | `/api/courses/{course_id}/review-plans` | 生成复习计划 | `{name?}` | `{id,name,items:[...]}` |
| GET | `/api/courses/{course_id}/review-plans` | 计划列表 | - | `[{id,name,status,created_at}]` |
| GET | `/api/review-plans/{plan_id}` | 计划详情 | - | `{id,name,items:[{review_date,completed,...}]}` |
| PATCH | `/api/review-items/{item_id}` | 标记完成 | `{completed}` | `{id,completed}` |

### 4.7 统一返回格式 `ApiResponse`

```json
{
  "code": 200,
  "message": "success",
  "data": { }
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | 业务状态码：200 成功、400 参数错误、404 不存在、500 服务器错误 |
| message | str | 提示信息 |
| data | object / array / null | 业务数据 |

错误示例：

```json
{ "code": 404, "message": "课程不存在", "data": null }
```

### 4.8 题目 JSON 结构示例（客观题）

```json
{
  "type": "single",
  "question": "RAG 的全称是什么？",
  "options": ["A. Retrieval-Augmented Generation", "B. ...", "C. ...", "D. ..."],
  "answer": "A",
  "explanation": "RAG 即检索增强生成……"
}
```

## 5. 项目目录结构

```
langchain_agent/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 应用入口，挂载路由与静态目录
│   ├── config.py                # 环境变量与模型配置
│   ├── core/                    # 核心基础
│   │   ├── __init__.py
│   │   ├── response.py          # ApiResponse 统一返回
│   │   └── exceptions.py        # 全局异常处理
│   ├── db/                      # 数据库连接
│   │   ├── __init__.py
│   │   ├── mysql.py             # SQLAlchemy MySQL 连接
│   │   └── postgres.py          # PostgreSQL + pgvector 连接
│   ├── models/                  # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   ├── course.py
│   │   ├── document.py
│   │   ├── quiz.py
│   │   ├── mistake.py
│   │   └── review.py
│   ├── schemas/                 # Pydantic v2 请求/响应 Schema
│   │   ├── __init__.py
│   │   ├── course.py
│   │   ├── document.py
│   │   ├── quiz.py
│   │   ├── chat.py
│   │   ├── mistake.py
│   │   └── review.py
│   ├── routers/                 # API 路由层
│   │   ├── __init__.py
│   │   ├── courses.py
│   │   ├── documents.py
│   │   ├── chat.py
│   │   ├── quiz.py
│   │   ├── mistake.py
│   │   └── review.py
│   ├── services/                # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── document_service.py  # 文档解析/切分/向量化
│   │   ├── rag_service.py       # 检索 + 问答生成
│   │   ├── quiz_service.py      # 出题 + 判题
│   │   ├── mistake_service.py   # 错题本
│   │   └── review_service.py    # 复习计划
│   ├── vectorstore/             # 向量库封装
│   │   ├── __init__.py
│   │   └── pgvector_store.py    # pgvector 客户端与 embedding 封装
│   └── prompts/
│       ├── __init__.py
│       └── templates.py         # 问答/出题/复习计划 Prompt 模板
├── static/                      # 前端静态资源
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── api.js               # 统一 fetch 封装
│       ├── courses.js
│       ├── chat.js
│       ├── quiz.js
│       ├── mistake.js
│       └── review.js
├── docs/
│   ├── PRD.md
│   ├── SPEC.md
│   └── AGENTS.md
├── .env.example
├── .env                         # git 忽略
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 6. 关键技术点与难点

1. **Embedding 一致性**：文档入库与问答检索必须使用同一 embedding 模型（BAAI/bge-m3），避免向量空间不一致；
2. **文档解析**：不同格式使用对应 LangChain Loader，解析异常需捕获并标记失败；
3. **结构化出题**：LLM 输出 JSON 需用 Prompt 约束格式，返回后解析校验与重试，失败降级；
4. **双库一致性**：删除文档/课程时需同步删除 PostgreSQL 向量与 MySQL 记录，防止"幽灵"数据；
5. **pgvector 索引**：向量量大时建立 ivfflat/hnsw 索引提升检索性能；
6. **Prompt 模板管理**：问答/出题/复习计划 Prompt 独立维护；
7. **配置安全**：密钥通过 `.env` 注入，`.env` 加入 `.gitignore`。

## 7. Docker 部署

### 7.1 服务编排（docker-compose.yml 概览）

| 服务 | 镜像/构建 | 说明 |
| --- | --- | --- |
| mysql | `mysql:8.0` | 业务库，暴露 3306 |
| postgres | `pgvector/pgvector:pg16` | 向量库 + 记忆，暴露 5432 |
| backend | 基于 `Dockerfile` 构建 | FastAPI 应用，暴露 8000 |

### 7.2 启动方式

```bash
# 一键构建并启动全部容器
docker-compose up --build

# 本地开发（非 Docker）
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

启动后访问 `http://127.0.0.1:8000` 打开前端，`/docs` 查看 API 文档。

## 8. 环境配置（`.env`）

```ini
# SiliconFlow（硅基流动）OpenAI 兼容接口
SILICONFLOW_API_KEY=sk-xxxxxxxx
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

# 模型配置
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
EMBEDDING_MODEL=BAAI/bge-m3

# 检索参数
TOP_K=4

# MySQL
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DATABASE=study_mate

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DATABASE=study_mate
```
