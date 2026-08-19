import chromadb
import logging
from app.core.paths import VECTOR_DB_DIR
from app.services.embedding_service import encode_texts

logger = logging.getLogger(__name__)

# 创建Chroma数据库
client = chromadb.PersistentClient(
    path=str(VECTOR_DB_DIR)
)

# 创建知识库集合
collection = client.get_or_create_collection(
    name="enterprise_documents"
)


def save_chunks(
        chunks: list[str],
        document_metadata: dict | str | None = None,
        filename: str | None = None
):
    """保存文本块及其可追踪的文档、分块 metadata。

    新调用应把完整的 ``document_metadata`` 字典传入本函数。文档信息由
    上传服务生成，向量存储层只负责为每个 chunk 补充分块级字段。

    为兼容现有 ``save_chunks(chunks, filename)`` 调用，第二个位置参数仍
    可以是文件名字符串；兼容模式下使用 filename 作为 document_id。
    """
    if isinstance(document_metadata, str):
        # 兼容旧调用：save_chunks(chunks, filename)
        legacy_filename = document_metadata
        base_metadata = {
            "document_id": legacy_filename,
            "filename": legacy_filename
        }
    elif isinstance(document_metadata, dict):
        # 使用副本，避免为 chunk 增加字段时修改调用方传入的数据。
        base_metadata = document_metadata.copy()

        if filename and "filename" not in base_metadata:
            base_metadata["filename"] = filename

        if not base_metadata.get("document_id"):
            raise ValueError("document_metadata 缺少 document_id")

        if not base_metadata.get("filename"):
            raise ValueError("document_metadata 缺少 filename")
    elif document_metadata is None and filename:
        # 兼容可能存在的旧关键字调用：save_chunks(chunks, filename=...)
        base_metadata = {
            "document_id": filename,
            "filename": filename
        }
    else:
        raise ValueError("必须提供 document_metadata 或 filename")

    chunk_count = len(chunks)

    if chunk_count == 0:
        return {
            "count": 0
        }

    vectors = encode_texts(chunks)

    ids = []
    chunk_metadatas = []

    for chunk_index in range(chunk_count):
        chunk_id = f"{base_metadata['document_id']}:{chunk_index}"

        ids.append(chunk_id)

        # chunk_index 用于恢复原始顺序、来源定位和后续精确管理。
        # 每条向量都保留文档 metadata，便于 Chroma 直接过滤和追踪来源。
        chunk_metadata = base_metadata.copy()
        chunk_metadata.update(
            {
                "chunk_id": chunk_id,
                "chunk_index": chunk_index,
                "chunk_count": chunk_count
            }
        )
        chunk_metadatas.append(chunk_metadata)


    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=vectors,
        metadatas=chunk_metadatas
    )


    return {
        "count": len(chunks)
    }

def delete_document(filename:str):

    result = collection.get(
        where={
            "filename": filename
        }
    )


    logger.info("Vector deletion started filename=%s match_count=%s", filename, len(result["ids"]))


    ids = result["ids"]


    if ids:
        collection.delete(
            ids=ids
        )


    result_after = collection.get(
        where={
            "filename": filename
        }
    )


    logger.info("Vector deletion completed filename=%s remaining_count=%s", filename, len(result_after["ids"]))


    return {
        "delete_count": len(ids)
    }
