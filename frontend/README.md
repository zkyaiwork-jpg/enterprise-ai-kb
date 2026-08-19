# 企业 AI 知识库助手前端

## Vue 3 Web 前端（当前）

新 Web 前端使用 Vue 3、Vite、TypeScript、Element Plus 和 Axios。

```bash
cd frontend
npm install
npm run dev
```

默认访问 <http://127.0.0.1:5173>，连接 <http://127.0.0.1:8000> 的 FastAPI。
如需修改后端地址，复制 `.env.example` 为 `.env.local` 并调整 `VITE_API_BASE_URL`。

## Streamlit 历史前端（保留）

这是企业 AI 知识库助手的 Streamlit 前端，包含产品首页、知识库管理、RAG 对话和语义检索四个页面。

## 安装依赖

在项目虚拟环境中执行：

```bash
pip install streamlit requests
```

## 启动后端

前端默认连接 `http://127.0.0.1:8000`，请先在项目根目录启动 FastAPI：

```bash
uvicorn app.main:app --reload
```

如后端使用其他地址，可通过环境变量指定：

```bash
set KB_API_BASE_URL=http://127.0.0.1:8000
```

## 启动前端

在项目根目录执行：

```bash
streamlit run frontend/app.py
```

## 访问地址

浏览器打开：

<http://localhost:8501>

## 页面说明

- **首页**：根据文档 metadata 汇总真实知识片段数量，并展示最近文档卡片。
- **知识库**：使用后端真实分类、索引状态、Chunk 数量和上传时间展示文档。
- **AI 助手**：进行带历史记录和来源展示的 RAG 对话。
- **知识检索**：查看语义搜索命中的来源、distance 和文本片段。

## 常见问题

- 显示“后端服务未连接”：确认 FastAPI 已在 8000 端口启动。
- 上传或问答超时：文档向量化和 AI 生成可能耗时较长，请稍后重试。
- 文档缺少某项 metadata 时，对应位置会显示“暂无数据”。
