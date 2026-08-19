# 企业 AI 知识库助手：知识库 Metadata 升级审查与改造方案

## 项目信息

- 项目名称：企业 AI 知识库助手
- 项目路径：`<project-root>`
- 本次工作：只读检查并制定 metadata 升级方案
- 代码修改：无

## 1. 文档上传入口

### 文件路径

- `app/api/document.py`
- `app/services/document_service.py`

### 函数

- API：`upload_document()`
- Service：`save_document()`

### 接口

```http
POST /upload
Content-Type: multipart/form-data
file: UploadFile
```

### 当前流程

```text
UploadFile
  ↓
upload_document()
  ↓
save_document(file)
  ↓
获取 file.filename
  ↓
按 filename 删除旧向量
  ↓
保存至 data/documents
  ↓
parse_docx() 解析正文
  ↓
split_text() 文本切分
  ↓
save_chunks(chunks, filename)
  ↓
生成 Embedding
  ↓
写入 Chroma
  ↓
返回文件路径、正文、chunks 和向量数量
```

### 当前上传返回字段

- `filename`
- `path`
- `content`
- `chunks`
- `vector_count`
- `message`

### 注意事项

- 异步接口内部执行同步文件读写、解析和向量化。
- 同名上传通过 filename 删除旧向量，没有 document ID 或版本概念。
- 删除旧向量发生在新文档解析成功之前，存在数据一致性风险。

## 2. 向量保存位置

### 文件路径

- `app/services/vector_store.py`

### 函数

```python
save_chunks(chunks: list[str], filename: str)
```

### Chroma 配置

```python
client = chromadb.PersistentClient(
    path=BASE_DIR / "data/vector_db"
)

collection = client.get_or_create_collection(
    name="enterprise_documents"
)
```

### 保存调用

```python
collection.add(
    ids=ids,
    documents=chunks,
    embeddings=vectors,
    metadatas=...
)
```

### 当前 ID 结构

```text
{filename}_{chunk_index}
```

例如：

```text
员工制度.docx_0
员工制度.docx_1
```

### 当前 metadata 结构

```json
{
  "filename": "员工制度.docx"
}
```

每个 chunk 只保存一个 `filename` 字段。

### 当前缺失字段

- 文档唯一 ID
- Chunk 序号和总数
- 文件类型和大小
- 分类、项目和标签
- 内容 hash
- 文件版本
- 上传时间和更新时间
- 上传人
- 页码和章节
- 文档状态
- 权限信息

## 3. 文档列表接口

### 文件路径

- `app/api/document.py`
- `app/services/document_service.py`

### 接口与函数

```http
GET /documents
```

- API：`get_documents()`
- Service：`list_documents()`

### 当前实现

- 遍历本地 `data/documents` 目录。
- 返回目录中的所有文件。
- 不读取 Chroma metadata。
- 无法判断文件是否真正完成向量化。

### 当前返回结构

```json
{
  "documents": [
    {
      "filename": "员工制度.docx",
      "size": 38809,
      "type": ".docx"
    }
  ]
}
```

### 当前返回字段

- `filename`
- `size`
- `type`

### 当前缺失

- `document_id`
- `category`
- `tags`
- `project_id`
- `status`
- `chunk_count`
- `vector_count`
- `uploaded_at`
- `updated_at`
- `version`
- `content_hash`
- `uploader`
- 索引错误信息

`app/services/document_manager.py` 也存在一个未被当前路由使用的 `list_documents()`，属于重复实现。

## 4. 删除接口

### 文件路径

- `app/api/manage.py`
- `app/services/vector_store.py`
- `app/services/document_service.py`

### 接口

```http
DELETE /documents/{filename}
```

### API 函数

```python
remove_document(filename: str)
```

### 当前实现

```text
接收 filename
  ↓
vector_store.delete_document(filename)
  ↓
collection.get(where={"filename": filename})
  ↓
获取匹配向量 IDs
  ↓
collection.delete(ids=ids)
  ↓
remove_document_file(filename)
  ↓
删除 data/documents/<filename>
  ↓
返回文件和向量删除结果
```

### 当前返回结构

```json
{
  "filename": "员工制度.docx",
  "file_deleted": true,
  "delete_vector": 10,
  "message": "删除成功"
}
```

### 存在的问题

- filename 被当作唯一标识，无法妥善处理重名、改名和版本。
- 文件删除与向量删除不是事务操作。
- 向量先删除、本地文件后删除，第二步失败会导致不一致。
- 返回消息始终是“删除成功”。
- filename 缺少完整路径安全校验。
- metadata 升级后应优先按 `document_id` 删除。

特别注意：`app/services/document_manager.py` 中另有一个未被当前 API 使用的 `delete_document()`。该函数获取 collection 中的全部 IDs 并删除全部向量，没有 filename 过滤，未来不能误接入。

# 《知识库 Metadata 升级改造方案》

## 当前结构

系统目前有两套文档信息来源：

```text
本地文件系统
  └── filename、size、type

Chroma metadata
  └── filename
```

两者通过 filename 松散关联。当前向量记录可抽象为：

```json
{
  "id": "员工制度.docx_0",
  "document": "某个知识片段",
  "embedding": [0.1, 0.2],
  "metadata": {
    "filename": "员工制度.docx"
  }
}
```

主要限制：

- filename 同时承担名称、关联键和删除键。
- 无法准确管理重名文档。
- 无法支持分类、标签、项目隔离和版本控制。
- 文档列表无法反映索引状态。
- 搜索结果无法返回页码、章节和精确引用。
- 无法判断本地文件与向量数据是否一致。

## 需要增加的字段

### 文档级字段

| 字段 | 类型 | 作用 | 优先级 |
| --- | --- | --- | --- |
| `document_id` | string/UUID | 文档稳定唯一标识 | P0 |
| `filename` | string | 当前文件名 | P0 |
| `original_filename` | string | 用户上传时的原始文件名 | P1 |
| `file_type` | string | DOCX 等文件类型 | P0 |
| `file_size` | integer | 文件字节数 | P1 |
| `content_hash` | string | 重复上传检测和内容变更判断 | P0 |
| `category` | string | 公司制度、技术文档等分类 | P1 |
| `project_id` | string | 所属项目或知识库 | P1 |
| `tags` | string | 标签；Chroma 中建议先序列化 | P2 |
| `version` | integer/string | 文件版本 | P1 |
| `status` | string | `processing/indexed/failed` | P0 |
| `uploaded_at` | string | ISO 8601 上传时间 | P0 |
| `updated_at` | string | ISO 8601 更新时间 | P1 |
| `uploader_id` | string | 上传用户 | P2 |
| `error_message` | string | 索引失败原因 | P1 |

### Chunk 级字段

| 字段 | 类型 | 作用 | 优先级 |
| --- | --- | --- | --- |
| `document_id` | string | 关联所属文档 | P0 |
| `chunk_id` | string | Chunk 稳定唯一标识 | P0 |
| `chunk_index` | integer | Chunk 顺序 | P0 |
| `chunk_count` | integer | 文档 Chunk 总数 | P0 |
| `filename` | string | 显示及旧数据兼容 | P0 |
| `category` | string | 支持检索过滤 | P1 |
| `project_id` | string | 支持项目隔离检索 | P1 |
| `version` | integer/string | 标识所属版本 | P1 |
| `section_title` | string | 所属章节 | P1 |
| `page_number` | integer | 来源页码 | P1 |
| `char_start` | integer | 原文开始位置 | P2 |
| `char_end` | integer | 原文结束位置 | P2 |
| `created_at` | string | Chunk 创建时间 | P2 |

### 推荐 Chunk metadata

```json
{
  "document_id": "3da15bc8-...",
  "filename": "员工制度.docx",
  "file_type": "docx",
  "file_size": 38809,
  "content_hash": "sha256:...",
  "category": "公司制度",
  "project_id": "default",
  "version": 1,
  "status": "indexed",
  "uploaded_at": "2026-08-10T15:30:00+08:00",
  "chunk_id": "3da15bc8-...:1:0",
  "chunk_index": 0,
  "chunk_count": 12,
  "section_title": "请假审批",
  "page_number": 3
}
```

Chroma metadata 值应优先采用字符串、整数、浮点数或布尔值。标签数组的过滤能力需要结合当前 Chroma 版本验证；在没有独立文档数据库时可暂存为 JSON 字符串，但不适合高效按单个标签过滤。

## 推荐数据架构

长期不建议把所有文档管理信息重复写入每个 Chroma chunk。建议分为两层：

```text
文档注册表
  ├── document_id
  ├── filename
  ├── category
  ├── content_hash
  ├── version
  ├── status
  ├── chunk_count
  └── uploaded_at

Chroma Chunk metadata
  ├── document_id
  ├── filename
  ├── chunk_id
  ├── chunk_index
  ├── category
  ├── project_id
  ├── version
  ├── section_title
  └── page_number
```

MVP 阶段可以先把文档级字段重复保存到每个 Chunk，后续再引入 SQLite 或 PostgreSQL 文档注册表。

## 涉及文件

### 必须修改

1. `app/services/document_service.py`
   - 生成 `document_id`。
   - 计算文件 hash、大小和上传时间。
   - 接收或推断 category。
   - 将 metadata 传给 `save_chunks()`。
   - 升级文档列表字段。

2. `app/services/vector_store.py`
   - 扩展 `save_chunks()` 参数。
   - 生成稳定 `chunk_id`。
   - 保存新的 Chunk metadata。
   - 增加按 `document_id` 删除能力。
   - 保留旧 filename 兼容或迁移逻辑。

3. `app/api/document.py`
   - 上传接口接收可选 category/project 信息。
   - 返回 document ID、状态、时间和 chunk 数量。
   - 文档列表返回升级后的字段。

4. `app/api/manage.py`
   - 删除入口从 filename 逐步切换到 document ID。
   - 返回准确的文件和向量删除状态。

### 可能需要修改

5. `app/services/search_service.py`
   - 支持 `document_id`、category、project_id 等过滤。
   - 搜索结果返回 chunk、页码和章节信息。

6. `app/services/rag_service.py`
   - sources 升级为结构化引用。

7. `frontend/api_client.py`
   - 适配新的上传、列表、删除和搜索响应。

8. `frontend/pages/knowledge.py`
   - 使用真实 category、uploaded_at、chunk_count 和 status。
   - 移除文件名推断分类的临时逻辑。

9. `frontend/components/document_card.py`
   - 展示真实 metadata。

10. `tests/`
   - 增加 metadata 保存、过滤、更新、删除和迁移测试。

### 应清理或隔离

- `app/services/document_manager.py`

该文件与 `document_service.py` 职责重复，并包含可能删除全部向量的危险函数。正式改造前应明确唯一的文档管理服务。

## 修改顺序

### 第一步：确定 metadata 契约

优先固定字段：

```text
document_id
filename
file_type
file_size
content_hash
category
status
version
uploaded_at
chunk_id
chunk_index
chunk_count
```

### 第二步：升级 Chunk 和切分结果

让切分结果能够携带：

- `content`
- `chunk_index`
- `section_title`
- `page_number`
- 位置信息

如果暂时不改切分器，至少在保存向量时补充 `chunk_index` 和 `chunk_count`。

### 第三步：升级向量保存

```text
chunks + document_metadata
  ↓
生成 chunk_id
  ↓
为每个 chunk 合并文档级与 chunk 级 metadata
  ↓
写入 Chroma
```

推荐 ID：

```text
{document_id}:{version}:{chunk_index}
```

### 第四步：升级上传服务

1. 安全保存临时文件。
2. 计算 SHA-256。
3. 判断重复或更新。
4. 生成或复用 document ID。
5. 解析和切分。
6. 写入新向量。
7. 成功后清理旧版本。
8. 更新文档状态。

### 第五步：升级文档列表

文档列表不应继续只扫描本地目录，至少需要合并文件系统状态、Chroma 索引状态和文档 metadata。

建议返回：

```json
{
  "documents": [
    {
      "document_id": "3da15bc8-...",
      "filename": "员工制度.docx",
      "file_type": "docx",
      "file_size": 38809,
      "category": "公司制度",
      "status": "indexed",
      "chunk_count": 12,
      "version": 1,
      "uploaded_at": "2026-08-10T15:30:00+08:00"
    }
  ]
}
```

### 第六步：升级删除接口

推荐增加：

```http
DELETE /documents/{document_id}
```

删除流程：

```text
查找文档记录
  ↓
按 document_id 删除向量
  ↓
删除本地文件
  ↓
删除或标记文档记录
```

为兼容当前前端，可暂时保留 filename 删除接口，内部先解析成 document ID。

### 第七步：升级搜索和 sources

搜索支持：

```text
category
project_id
document_id
tags
```

RAG sources 建议返回：

```json
{
  "document_id": "3da15bc8-...",
  "filename": "员工制度.docx",
  "chunk_index": 4,
  "page_number": 3,
  "section_title": "请假审批"
}
```

### 第八步：迁移与测试

- 备份当前 `data/vector_db`。
- 为现有文档生成 document ID 和 metadata。
- 最可靠方案是重新解析并重建全部向量。
- 验证旧 filename 删除逻辑不会误删。
- 测试使用临时 Chroma 目录，不操作正式库。

## 风险点

1. **现有数据没有 document ID**：新代码必须兼容旧数据或执行一次性重建。
2. **Chroma 不是文档主数据库**：文档级字段重复存储，长期应增加独立文档注册表。
3. **ID 结构变化**：会影响保存、删除、更新、搜索和测试逻辑。
4. **同名覆盖一致性**：当前先删除旧向量，新处理失败会造成旧知识丢失。
5. **旧数据过滤兼容**：按新字段过滤时，没有新字段的旧向量会被排除。
6. **Chroma 字段类型限制**：同一字段必须保持类型一致，避免整数、字符串和空值混用。
7. **空值处理**：不要依赖 Chroma 保存 `None`；缺失字段应省略或使用统一占位值。
8. **标签设计**：数组 metadata 未必适合按单个标签过滤，需要先验证版本或单独建表。
9. **删除接口兼容**：直接把 filename 改成 document ID 会破坏当前前端，需要过渡方案。
10. **重复服务实现**：`document_service.py` 与 `document_manager.py` 容易导致改错入口。
11. **索引状态真实性**：只有全部向量成功写入后才能设置 `status=indexed`。
12. **搜索与权限**：未来加入项目和用户 metadata 后，检索必须在服务端强制权限过滤。

## 建议交给 ChatGPT 的任务说明

请基于本文档为项目制定具体的 metadata 升级实施计划。在开始编码前，先确认：

1. metadata 字段契约和 Chroma 支持的数据类型；
2. 是否采用独立 SQLite 文档注册表；
3. 旧 Chroma 数据的迁移或全量重建策略；
4. filename 删除接口向 document ID 删除接口的兼容方案；
5. 上传失败时的数据回滚与状态管理方式。

实施时需要优先保证：旧接口兼容、正式向量数据不被测试污染、失败不删除旧知识、按 document ID 精确删除，以及 sources 可追溯到具体 Chunk。
