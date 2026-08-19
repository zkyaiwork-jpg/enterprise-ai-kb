# 企业 AI 知识库助手

企业 AI 知识库助手是一个基于 FastAPI、React 和 RAG 的企业内部知识问答系统。系统可以将企业 DOCX 文档解析、切分并写入 Chroma 向量数据库，随后通过语义检索和 DeepSeek 生成带来源引用的回答。

## 技术架构

```text
React + TypeScript + Vite
          ↓
       FastAPI
          ↓
          RAG
     ↙           ↘
Chroma + BGE     DeepSeek
```

主要技术栈：

- 前端：React、TypeScript、Vite、Tailwind CSS、Axios
- 后端：FastAPI、Pydantic、Uvicorn
- 文档处理：python-docx
- Embedding：BAAI/bge-small-zh-v1.5、Sentence Transformers
- 向量数据库：Chroma
- 大模型：DeepSeek Chat（OpenAI 兼容接口）

## 功能列表

- DOCX 文档上传、解析、切分与向量化
- 企业文档列表、详情和删除
- 企业知识库语义检索
- 基于知识库的 RAG 问答
- 回答来源、Chunk、引用文本和检索距离展示
- 工作台文档与知识片段统计
- React 前端加载、空数据和错误状态

> 当前后端文档解析器只支持 DOCX。PDF、TXT 等格式尚未实现后端解析。

## 环境要求

- Python 3.11（当前开发环境：3.11.9）
- Node.js 20 或更高版本（当前开发环境：24.18.0）
- npm 10 或更高版本
- Windows PowerShell（以下命令以 Windows 为例）
- 可访问 Hugging Face 模型仓库和 DeepSeek API

首次启动后端时，Sentence Transformers 可能需要下载 Embedding 模型。

## 环境变量

在项目根目录创建 `.env`：

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
```

在 `frontend-react/` 目录创建 `.env`：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

可以复制 `frontend-react/.env.example` 作为前端配置模板。修改 Vite 环境变量后需要重新启动前端开发服务。

## 后端安装与启动
> 组织初始化顺序：先创建 Department，再创建 Team，最后创建 employee/leader。admin 不要求 Team，bootstrap 不会自动创建虚构 Team。

## 首次部署

全新环境不开放匿名注册。第一个管理员通过本地CLI安全创建：

1. 在`.env`或部署环境中配置高熵密钥（不要提交真实值）：

```env
JWT_SECRET_KEY=使用至少32字节的随机密钥
MODEL_CONFIG_ENCRYPTION_KEY=使用Fernet.generate_key生成的密钥
```

2. 将数据库升级到最新版本：

```powershell
venv\Scripts\python.exe -m alembic upgrade head
```

3. 初始化默认RBAC权限并创建首个管理员：

```powershell
venv\Scripts\python.exe -m app.database.bootstrap
```

密码通过隐藏输入读取，不会显示在终端。自动化部署可临时设置`BOOTSTRAP_ADMIN_PASSWORD`，但初始化完成后必须立即删除该环境变量；不要把密码作为命令行参数。

4. 使用管理员账号登录，然后通过受保护的管理接口创建部门、员工账号和企业模型配置。重复执行bootstrap不会创建第二个首始管理员。


在项目根目录执行：

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

后端默认地址：

```text
http://127.0.0.1:8000
```

FastAPI 接口文档：

```text
http://127.0.0.1:8000/docs
```

## 前端安装与启动

打开新的 PowerShell 窗口：

```powershell
cd frontend-react
npm.cmd install
npm.cmd run dev
```

Vite 会在终端输出实际访问地址，通常为：

```text
http://127.0.0.1:5173
```

生产构建：

```powershell
npm.cmd run build
```

## 主要接口

| 方法 | 路径 | 功能 |
| --- | --- | --- |
| GET | `/` | 后端运行信息 |
| GET | `/stats` | 工作台统计 |
| GET | `/documents` | 文档列表 |
| POST | `/upload` | 上传并索引文档 |
| DELETE | `/documents/{filename}` | 删除文档和向量 |
| GET | `/search?query=...` | 语义检索 |
| POST | `/chat` | RAG 问答 |

## 项目目录结构

```text
enterprise-ai-kb/
├── app/
│   ├── api/                 # FastAPI 路由
│   ├── core/                # 核心配置预留
│   ├── services/            # 文档、向量、检索和 RAG 服务
│   ├── utils/               # 通用工具预留
│   └── main.py              # FastAPI 应用入口
├── frontend-react/
│   ├── src/
│   │   ├── api/             # Axios API 请求层
│   │   ├── components/      # React 可复用组件
│   │   ├── hooks/           # React Hooks 预留
│   │   ├── pages/           # Dashboard、Knowledge、Assistant 等页面
│   │   └── styles/          # 全局样式
│   └── package.json
├── frontend/                # 旧 Streamlit 前端（保留参考）
├── data/
│   ├── documents/           # 本地上传文档，不提交 Git
│   └── vector_db/           # Chroma 数据，不提交 Git
├── logs/                    # 本地日志
├── tests/                   # 后端测试与检查脚本
├── .env                     # 后端敏感配置，不提交 Git
├── requirements.txt         # Python 依赖
└── README.md
```

## 数据与安全说明

- `.env`、上传文档、Chroma 数据库、模型缓存和日志均不应提交到 Git。
- 开发环境 CORS 当前仅允许本机 Vite 地址。
- 测试脚本可能访问本地 Chroma 或 DeepSeek，执行前请确认测试数据与环境变量。
