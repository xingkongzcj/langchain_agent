# AGENTS.md —— AI 代理指令

> 本文件是给 AI 编程助手（Claude Code、Cursor、Codex 等）的工作手册，用于统一编码规则与开发规范，保证全项目代码风格一致。AI 在修改本项目代码前，必须先阅读并遵守本文件。

---

## 1. 项目概述

- **项目名称**：智学助手（StudyMate）
- **项目定位**：基于 LangChain 的课程知识库问答与出题智能体
- **技术栈**：FastAPI + LangChain + MySQL + Chroma + Docker
- **运行时**：Python 3.11
- **需求文档**：`docs/PRD.md`
- **技术规范**：`docs/SPEC.md`（**实现前必读**，数据模型、API、目录结构均以此为准）

## 2. 快速开始（Setup Commands）

```bash
# 安装依赖
pip install -r requirements.txt

# 复制环境变量样例并填写密钥
# 将 .env.example 复制为 .env，填写 SILICONFLOW_API_KEY 等

# 启动 MySQL（Docker）
docker-compose up -d mysql

# 启动开发服务器
uvicorn app.main:app --reload --port 8000

# 运行测试
pytest
```

> 启动前确保 `.env` 已配置有效的 `SILICONFLOW_API_KEY`，且 MySQL 已启动，否则问答、出题、复习计划等接口会失败。

## 3. 开发规范（强制）

1. **先读文档再动手**：任何功能开发前，先阅读 `docs/PRD.md` 与 `docs/SPEC.md`，严格遵循其中的数据库表设计、API 定义与目录结构。
2. **分层架构**：路由层（`routers/`）只做参数校验与转发，业务逻辑放 `services/`，ORM 模型放 `models/`，请求/响应结构放 `schemas/`，禁止跨层混写。
3. **小步迭代**：一次只实现一个功能模块，完成并验证后再进行下一个，禁止一次性堆砌多个功能。
4. **不破坏可运行状态**：每次改动后确保项目可正常启动（`uvicorn app.main:app`）。
5. **Git 版本控制**：每完成一个功能立即提交（见第 6 节）。

## 4. 代码风格（强制）

### 4.1 语言与运行时

- **必须使用 Python 3.11**，不得使用 3.12+ 专属语法或低于 3.10 的写法；
- 类型标注统一使用现代语法：`str | None`、`list[str]`、`dict[str, Any]`。

### 4.2 Pydantic v2 风格（强制）

- 数据校验一律使用 **Pydantic v2**，禁止使用 v1 写法；
- 模型配置使用 `model_config = ConfigDict(...)`，**禁止**使用 v1 的 `class Config`；
- 序列化使用 `model_dump()` / `model_dump_json()`，**禁止**使用 `.dict()`；
- 校验实例化使用 `model_validate()`，**禁止**使用 `.parse_obj()`；
- 字段约束使用 `Field(...)`（如 `Field(..., description="...")`）；
- 复用字段类型可定义在 `schemas/` 中。

```python
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    """统一接口返回格式。"""
    model_config = ConfigDict(from_attributes=True)
    code: int = Field(default=200, description="业务状态码")
    message: str = Field(default="success", description="提示信息")
    data: T | None = Field(default=None, description="业务数据")
```

### 4.3 接口返回规范（强制）

- **所有接口**必须返回统一 `ApiResponse` 格式，禁止直接返回裸对象；
- 成功：`ApiResponse(code=200, message="success", data=...)`；
- 业务错误通过全局异常处理器统一转换为 `ApiResponse`（code 400/404/500）；
- 返回结构见 `docs/SPEC.md` 第 4.7 节。

### 4.4 命名规范

- 文件/模块：`snake_case`（如 `rag_service.py`）；
- 函数/变量：`snake_case`；
- 类：`PascalCase`；
- 常量：`UPPER_SNAKE_CASE`；
- 数据库表：小写复数（`courses`、`documents`、`questions`、`mistakes`）。

### 4.5 其他

- **语言与注释**：代码标识符用英文；关键业务逻辑、复杂处写中文注释说明意图（不写无意义注释）；
- **导入顺序**：标准库 → 第三方库 → 本地模块，每组之间空一行；
- **字符串**：统一使用双引号，格式化用 f-string；
- **异步**：FastAPI 路由优先 `async def`，阻塞型 I/O（LLM 调用等）放入线程池或使用异步客户端。

## 5. 测试要求

- 核心业务逻辑（文档切分、向量化、检索、出题解析、判题）需编写单元测试；
- 测试命名：`test_*.py`，用例名 `test_<功能>_<场景>`；
- 提交前运行 `pytest` 确保全部通过；
- 涉及真实 LLM / 数据库的测试需使用 mock 或跳过标记，避免依赖外部网络与外部服务。

## 6. Git 版本控制（强制）

- 每完成一个功能模块，立即提交一次 commit；
- Commit message 遵循约定式提交：`feat:` / `fix:` / `docs:` / `refactor:` / `chore:`，描述清晰；
- 禁止将 `.env`、`__pycache__/` 等敏感或生成文件提交到仓库（已在 `.gitignore` 中忽略）；
- 禁止执行破坏性 git 操作（force push、hard reset 等），除非用户明确要求。

## 7. 特殊注意事项

1. **密钥安全**：`SILICONFLOW_API_KEY` 等密钥只能通过 `.env` 读取，**严禁硬编码**或打印到日志/终端。
2. **向量一致性**：文档入库与问答检索必须使用**同一个 embedding 模型**（BAAI/bge-m3）。
3. **Chroma 与 MySQL 同步删除**：删除文档或课程时，必须同步删除 Chroma 中的向量与 MySQL 记录，保持数据一致。
4. **结构化出题**：LLM 返回的题目 JSON 必须解析校验，异常时重试，失败需降级处理，不能直接崩溃。
5. **输入校验**：文件上传校验类型与大小；用户输入做基本转义；数据库操作使用 ORM 参数化。
6. **Docker 兼容**：涉及数据库连接时，host/port 通过环境变量读取，兼容 Docker 与本地开发两种场景。
7. **不擅自增删依赖**：如需新增第三方库，需同步更新 `requirements.txt` 并说明用途。

## 8. 环境配置

- 运行时：Python 3.11；
- 依赖：见 `requirements.txt`；
- 数据库：MySQL 8.0（业务）+ Chroma（本地持久化向量库）；
- 环境变量：见 `.env.example`，本地实际配置写入 `.env`（不提交）。

## 9. AI 代码审查要点（收尾阶段）

功能开发完成后，按以下维度自查或交叉审查：

1. 安全漏洞（明文密钥、注入风险、XSS）；
2. 性能问题（重复向量化、阻塞调用、缺索引）；
3. 代码规范（Python 3.11、Pydantic v2、ApiResponse 统一返回、命名与分层）；
4. 潜在 Bug（边界场景、异常处理缺失、双库一致性）；
5. 交互优化点。
