# 企业 AI 知识库助手

> 面向企业内部知识问答场景的 RAG 知识库系统，支持企业组织架构、RBAC 权限控制、文档级可见性、会话隔离、审计日志与 RAG 检索效果评测。

基于 FastAPI + React + Chroma + BGE + DeepSeek 构建。

系统将企业内部文档进行解析、分块和向量化存储，在用户提问时通过语义检索召回相关知识片段，并结合 DeepSeek 生成带来源引用的回答。

相比普通 RAG Demo，本项目重点解决企业知识库中的两个实际问题：

1. 回答是否能检索到正确知识
2. 用户是否有权限检索这些知识

---

# 项目背景

企业内部通常存在大量规章制度、业务规范和内部资料。

员工遇到问题时，传统方式往往需要：

* 人工查找文档
* 在多个文件中搜索关键词
* 询问其他员工
* 联系管理人员确认制度

而通用大模型本身并不了解企业内部知识。

例如：

> 公司事假应该怎么申请？

DeepSeek 无法直接知道某家企业内部的请假制度。

因此，本项目通过 RAG（Retrieval-Augmented Generation） 将企业内部知识库与大语言模型结合：

```text
企业文档
   ↓
文档解析
   ↓
文本分块
   ↓
Embedding 向量化
   ↓
Chroma 向量数据库
   ↓
用户问题
   ↓
语义检索
   ↓
相关知识片段
   ↓
DeepSeek
   ↓
生成企业知识回答
```

同时，企业知识并不是所有员工都可以访问，因此项目进一步加入组织架构、RBAC 和文档可见性控制，使知识检索遵循企业权限边界。

---

# 核心亮点

## 1. 企业级 RAG 知识问答

实现完整 RAG 链路：

```text
文档上传
  ↓
DOCX 解析
  ↓
Chunk 文本分块
  ↓
BGE Embedding
  ↓
Chroma 向量存储
  ↓
语义检索
  ↓
TopK 候选知识
  ↓
Distance Threshold 过滤
  ↓
构建 Context
  ↓
DeepSeek
  ↓
回答 + Sources
```

回答不仅返回生成内容，同时返回对应知识来源，方便用户确认回答依据。

---

## 2. 企业 RBAC 权限体系

系统实现基于角色的权限控制，不同用户拥有不同的数据访问范围。

主要角色包括：

| 角色       | 主要权限范围   |
| -------- | ----------   | 
| admin    | 企业级管理权限    |
| manager  | 部门级管理与访问权限 |
| leader   | 团队级权限     |
| employee | 普通员工权限   |

接口访问通过 JWT 身份认证与 RBAC 权限进行控制。

---

## 3. 文档级可见性控制

企业文档支持不同可见范围：

| Visibility | 含义           |
| ---------- | ------------ |
| private    | 仅指定用户/上传者可访问 |
| team       | 团队内部可访问      |
| department | 部门内部可访问      |
| company    | 企业内部可访问      |

系统不会简单地将所有知识检索后交给大模型判断权限，而是在进入 LLM 之前完成权限过滤。

---

## 4. RAG 检索前权限过滤

项目将权限控制放在知识检索链路中，而不是仅依赖 Prompt 约束模型。

核心流程：

```text
用户问题
   ↓
JWT 身份认证
   ↓
file_view 权限检查
   ↓
SQL 查询当前用户可访问文档
   ↓
生成文档白名单
   ↓
Embedding
   ↓
Chroma 在允许范围内检索
   ↓
返回结果二次权限校验
   ↓
Distance Threshold
   ↓
构建 Context
   ↓
DeepSeek
```

如果用户没有任何可访问文档：

```text
Allowed Documents = []
        ↓
直接返回空检索结果
        ↓
不会继续检索企业知识
```

采用 Fail-Closed 思路：权限无法确认时默认拒绝访问，而不是默认放行。

这样可以降低无权限文档进入 LLM Context 的风险。

---

## 5. 企业组织架构

系统建立：

```text
Company
   ↓
Department
   ↓
Team
   ↓
User
```

Department 与 Team 建立组织关系，用户可以归属于对应部门和团队。

组织架构不仅用于用户管理，同时参与文档权限计算。

---

## 6. 会话隔离

系统建立 Conversation 与 ChatMessage 数据模型。

不同用户之间的 AI 对话相互隔离，用户只能访问自己的会话记录，避免不同账号之间出现会话数据串用。

---

## 7. 审计日志

系统记录关键管理操作和访问行为，为企业内部系统提供操作追踪能力。

管理员可以通过审计接口查看相关记录。

---

## 8. 数据库迁移

项目使用 Alembic 管理数据库 Schema 变化。

数据库结构升级通过 Migration 管理，而不是依赖手动修改数据库表结构。

---

# 系统架构

```text
┌─────────────────────────────┐
│       React + TypeScript    │
│           Frontend          │
└──────────────┬──────────────┘
               │ HTTP API
               ↓
┌─────────────────────────────┐
│           FastAPI           │
│                             │
│ Authentication / JWT        │
│ RBAC Permission             │
│ Document Permission         │
│ Conversation Isolation      │
│ Audit Log                   │
└──────────────┬──────────────┘
               │
               ↓
┌─────────────────────────────┐
│          RAG Service        │
│                             │
│ SQL Document Whitelist      │
│ Embedding                   │
│ Vector Search               │
│ Permission Recheck          │
│ Distance Filter             │
└─────────┬───────────┬───────┘
          │           │
          ↓           ↓
┌──────────────┐  ┌──────────────┐
│    Chroma    │  │   DeepSeek   │
│ Vector Store │  │     LLM      │
└──────────────┘  └──────────────┘
```

---

# RAG 检索链路

当前核心检索流程：

```text
POST /chat
    ↓
JWT
    ↓
当前 User
    ↓
file_view Permission
    ↓
SQL 查询可访问 Documents
    ↓
Document Whitelist
    ↓
Question Embedding
    ↓
Chroma TopK Search
    ↓
Permission Recheck
    ↓
Distance < Threshold
    ↓
Top Knowledge Chunks
    ↓
Build Context
    ↓
DeepSeek
    ↓
Answer + Sources
```

当前主要检索参数：

```text
Embedding Model:
BAAI/bge-small-zh-v1.5

Vector Database:
Chroma

Chunk Size:
200

Chunk Overlap:
0

TopK:
3

Distance Threshold:
0.8
```

---

# RAG 检索评测

为了避免仅通过主观体验判断 RAG 效果，项目建立了独立检索评测流程。

评测重点关注：

* Top1 Hit
* Top3 Hit
* No Result
* Bad Case
* 原始检索距离
* 不同检索策略的结果变化

## Baseline 测试

早期使用 15 道企业知识问题进行 Baseline 测试。

结果：

| 指标       |      结果 |
| -------- | ------: |
| 测试问题     |      15 |
| Top1 命中  | 14 / 15 |
| Top1 命中率 |  93.33% |
| Top3 命中  | 15 / 15 |
| Top3 命中率 |    100% |
| 无结果      |       0 |

测试发现：

部分语义接近的问题虽然正确文档已经进入 Top3，但 Top1 仍可能被其他相似制度文档占据。

例如：

```text
用户问题
   ↓
Embedding
   ↓
Top3 Candidate Chunks
   ↓
Top1：相似但并非最佳答案
Top2：正确答案
Top3：其他候选
```

因此，仅关注“正确答案是否进入 Top3”并不足以完整评估检索质量，还需要关注候选结果排序。

---

## 扩展评测

后续将测试集扩展至 50 道正向问题，对生产检索参数进行离线复现。

Baseline V2：

| 指标       |      结果 |
| -------- | ------: |
| 测试问题     |      50 |
| Top1 命中  | 43 / 50 |
| Top1 命中率 |     86% |
| Top3 命中  | 47 / 50 |
| Top3 命中率 |     94% |
| 正向无结果    |       3 |

同时构造负向问题，用于检查知识库不存在答案时系统是否错误召回无关内容。

对 Top1 Bad Case 进行单独记录和分析，为后续 Chunk、Embedding、Threshold 和 Rerank 优化提供依据。

---

# Rerank 实验

针对“正确答案已经进入 Top3，但排序不理想”的问题，项目进行了独立 Rerank 实验。

实验模型：

```text
BAAI/bge-reranker-base
```

流程：

```text
Question
   ↓
Embedding Retrieval
   ↓
Chroma Candidates
   ↓
Reranker
   ↓
重新计算 Question / Chunk 相关性
   ↓
重新排序
   ↓
LLM
```

Rerank 实验与生产检索链路分离，先通过离线评测验证效果，再决定是否接入生产流程。

这样可以避免未经验证的检索策略直接影响线上 RAG 行为。

---

# 技术栈

## Frontend

* React
* TypeScript
* Vite
* Tailwind CSS
* Axios

## Backend

* Python 3.11
* FastAPI
* Pydantic
* Uvicorn
* SQLAlchemy
* Alembic

## AI / RAG

* DeepSeek
* BAAI/bge-small-zh-v1.5
* Sentence Transformers
* BAAI/bge-reranker-base（实验）
* Chroma

## Document Processing

* python-docx

当前后端文档解析器主要支持 DOCX。

PDF、TXT 等格式尚未实现正式后端解析。

---

# 核心功能

### 知识库

* DOCX 文档上传
* 文档解析
* 文本 Chunk
* Embedding
* Chroma 向量存储
* 文档列表
* 文档删除
* 语义检索
* RAG 问答
* Sources 来源展示

### 权限

* JWT 身份认证
* RBAC
* 用户角色权限
* 文档可见性
* SQL 文档白名单
* Chroma 检索范围限制
* 检索结果二次权限校验

### 企业管理

* User
* Department
* Team
* Role
* Permission

### 系统能力

* Conversation 会话隔离
* ChatMessage 消息记录
* AuditLog 审计日志
* Alembic 数据库迁移
* RAG Evaluation
---

---

# 项目目录

```text
enterprise-ai-kb/
│
├── app/
│   ├── api/                 # FastAPI API 路由
│   ├── auth/                # JWT 与权限认证
│   ├── database/            # 数据库初始化与配置
│   ├── models/              # 数据模型
│   ├── services/            # 核心业务服务
│   ├── utils/               # 工具模块
│   └── main.py              # FastAPI 应用入口
│
├── alembic/                 # 数据库 Migration
│
├── evals/                   # RAG 检索评测
│
├── tests/                   # 后端测试
│
├── frontend-react/          # React 前端
│
├── frontend/                # 旧前端实现
│
├── scripts/                 # 项目脚本
│
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── pytest.ini
├── requirements.txt
├── .env.example
└── README.md
```

---

# 快速开始

## 1. 克隆项目

```bash
git clone <your-repository-url>
cd enterprise-ai-kb
```

---

## 2. 创建 Python 虚拟环境

Windows：

```bash
python -m venv venv
venv\Scripts\activate
```

安装依赖：

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. 配置环境变量

在项目根目录创建：

```text
.env
```

根据 `.env.example` 配置实际运行环境。

例如：

```text
DEEPSEEK_API_KEY=your_deepseek_api_key
JWT_SECRET_KEY=your_random_secret
MODEL_CONFIG_ENCRYPTION_KEY=your_encryption_key
```

请勿将真实 API Key、JWT Secret 或其他敏感信息提交到 Git。

---

# 首次部署

系统不开放匿名注册。

首先执行数据库 Migration：

```bash
python -m alembic upgrade head
```

然后初始化 RBAC 权限并创建首个管理员：

```bash
python -m app.database.bootstrap
```

建议组织创建顺序：

```text
Department
    ↓
Team
    ↓
User
```

admin 不强制要求所属 Team。

---

# 启动后端

```bash
python -m uvicorn app.main:app --reload
```

默认地址：

```text
http://127.0.0.1:8000
```

FastAPI Swagger：

```text
http://127.0.0.1:8000/docs
```

---

# 启动前端

```bash
cd frontend-react
npm install
npm run dev
```

Vite 会在终端输出实际访问地址。

开发环境通常为：

```text
http://127.0.0.1:5173
```

生产构建：

```bash
npm run build
```

---

# 测试

项目包含后端功能、权限和数据完整性相关测试。

测试内容主要包括：

```text
Document Permission
Team Permission Matrix
Document Mutation
Document List Permission
Conversation Isolation
Audit
User Management
Migration
Data Integrity
```

同时 `evals/` 用于 RAG 检索效果评测，与普通功能测试分开管理。

---

# 数据与安全

项目按照企业知识库场景对敏感数据进行隔离。

以下内容不应提交至 Git：

```text
.env
API Key
JWT Secret
真实企业文档
Chroma 本地数据
模型缓存
运行日志
本地数据库敏感数据
```

权限设计遵循：

```text
Authentication
      ↓
Authorization
      ↓
Document Permission
      ↓
Retrieval
      ↓
LLM
```

即：

**先判断用户能够看到什么，再进行知识检索，而不是先检索敏感知识再让 LLM 判断是否应该回答。**

---

# 后续计划

当前项目仍在持续迭代，后续重点包括：

* [ ] 完善 Team 管理功能
* [ ] 扩展 PDF / TXT 等文档解析
* [ ] 继续扩大 RAG Evaluation Dataset
* [ ] 分析并优化 Top1 Bad Case
* [ ] 对比 Embedding / Rerank 策略
* [ ] 优化 Chunk Strategy
* [ ] 完善前端权限管理体验
* [ ] 完善自动化测试
* [ ] 完善部署流程

---

# 项目定位

该项目主要用于学习和实践企业级 AI 应用开发中的：

**RAG、Embedding、Vector Database、LLM API、FastAPI、RBAC、企业权限控制、数据库设计、检索评测和 AI 应用工程化。**

项目重点并非单纯调用大模型 API，而是尝试解决企业 AI 知识库实际落地过程中涉及的：

> **知识从哪里来、如何检索、谁可以访问、检索是否准确、如何评测以及如何避免越权访问。**

