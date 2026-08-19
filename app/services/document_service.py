import logging
import os
from pathlib import Path
import tempfile
import uuid

from fastapi import HTTPException, UploadFile

from app.core.paths import DOCUMENTS_DIR
from app.services.parsers.parser_factory import SUPPORTED_EXTENSIONS, get_parser
from app.services.folder_service import get_folder
from app.services.text_splitter import split_text
from app.services.vector_store import collection, save_chunks
from app.utils.datetime import normalize_aware_iso_datetime, serialize_utc_datetime, utc_now


UPLOAD_DIR = DOCUMENTS_DIR
logger = logging.getLogger(__name__)


def _normalize_uploaded_at(value: object) -> str | None:
    """Normalize trusted offset-aware metadata without guessing naive values."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return normalize_aware_iso_datetime(value)
    except ValueError:
        logger.warning("Document metadata timestamp omitted explicit_timezone=false")
        return None


def _delete_vector_ids(ids: list[str]) -> None:
    if ids:
        collection.delete(ids=ids)


def _restore_vector_snapshot(snapshot: dict) -> None:
    """Restore any old vectors missing after a failed replacement."""
    ids = snapshot.get("ids") or []
    if not ids:
        return

    existing_ids = set((collection.get(ids=ids).get("ids") or []))
    missing_indexes = [index for index, item_id in enumerate(ids) if item_id not in existing_ids]
    if not missing_indexes:
        return

    documents = snapshot.get("documents") or []
    embeddings = snapshot.get("embeddings")
    metadatas = snapshot.get("metadatas") or []

    add_kwargs = {
        "ids": [ids[index] for index in missing_indexes],
        "documents": [documents[index] for index in missing_indexes],
        "metadatas": [metadatas[index] for index in missing_indexes],
    }
    if embeddings is not None:
        add_kwargs["embeddings"] = [embeddings[index] for index in missing_indexes]

    collection.add(**add_kwargs)


def save_document(
    file: UploadFile,
    folder_id: int | None = None,
    access_metadata: dict | None = None,
):
    original_filename = file.filename or ""
    filename = Path(original_filename).name

    file_extension = Path(filename).suffix.lower()
    if file_extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="当前仅支持DOCX、TXT和PDF文件")

    if not filename or filename != original_filename:
        raise HTTPException(status_code=400, detail="文件名不合法")

    folder = get_folder(folder_id) if folder_id is not None else None
    if folder_id is not None and folder is None:
        raise HTTPException(status_code=400, detail="所选文件夹不存在")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    final_path = UPLOAD_DIR / filename
    temp_path: Path | None = None
    document_id = (access_metadata or {}).get("document_id") or str(uuid.uuid4())
    new_vector_ids: list[str] = []
    logger.info("Document upload started filename=%s document_id=%s", filename, document_id)

    # 在写入新版本前保留旧向量的完整快照。新流程中任何步骤失败，
    # 都可以删除新向量并恢复旧版本。
    try:
        old_snapshot = collection.get(
            where={"filename": filename},
            include=["documents", "embeddings", "metadatas"],
        )
    except Exception as exc:
        logger.error(
            "Old vector snapshot failed filename=%s document_id=%s error_type=%s",
            filename, document_id, type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail=f"读取旧文档向量失败：{exc}") from exc

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=file_extension,
            prefix="upload-",
            dir=UPLOAD_DIR,
            delete=False,
        ) as temp_file:
            temp_file.write(file.file.read())
            temp_path = Path(temp_file.name)

        file_size = temp_path.stat().st_size
    except Exception as exc:
        if temp_path and temp_path.exists():
            temp_path.unlink()
        logger.error(
            "Temporary upload save failed filename=%s document_id=%s error_type=%s",
            filename, document_id, type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail=f"文件临时保存失败：{exc}") from exc

    document_metadata = {
        "document_id": document_id,
        "filename": filename,
        "file_type": file_extension.lstrip("."),
        "file_size": file_size,
        "status": "processing",
        "uploaded_at": serialize_utc_datetime(utc_now()),
    }
    if access_metadata:
        document_metadata.update(access_metadata)
    if folder:
        document_metadata.update({
            "category": folder["name"],
            "folder_id": folder["id"],
            "folder_name": folder["name"],
        })

    try:
        parser = get_parser(temp_path)
        content = parser.parse(temp_path)
        chunks = split_text(content)
        if not chunks:
            raise ValueError("文档中没有可索引的文本内容")
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        logger.error(
            "Document parse or split failed filename=%s document_id=%s error_type=%s",
            filename, document_id, type(exc).__name__,
        )
        raise HTTPException(status_code=422, detail=f"文档解析或切分失败：{exc}") from exc

    try:
        document_metadata["status"] = "indexed"
        vector_result = save_chunks(chunks, document_metadata)
        new_vector_ids = [f"{document_id}:{index}" for index in range(len(chunks))]
    except Exception as exc:
        # collection.add 通常是原子操作；仍尝试清理可能已经写入的部分新 ID。
        try:
            _delete_vector_ids([f"{document_id}:{index}" for index in range(len(chunks))])
        except Exception:
            pass
        temp_path.unlink(missing_ok=True)
        logger.error(
            "Vector write failed filename=%s document_id=%s chunk_count=%s error_type=%s",
            filename, document_id, len(chunks), type(exc).__name__,
        )
        raise HTTPException(status_code=500, detail=f"向量写入失败：{exc}") from exc

    try:
        # 新向量已经完整可用后，才移除旧向量并原子替换正式文件。
        _delete_vector_ids(old_snapshot.get("ids") or [])
        os.replace(temp_path, final_path)
    except Exception as exc:
        rollback_errors = []
        try:
            _delete_vector_ids(new_vector_ids)
        except Exception as rollback_exc:
            rollback_errors.append(f"清理新向量失败：{rollback_exc}")
        try:
            _restore_vector_snapshot(old_snapshot)
        except Exception as rollback_exc:
            rollback_errors.append(f"恢复旧向量失败：{rollback_exc}")
        temp_path.unlink(missing_ok=True)

        rollback_detail = f"；{'；'.join(rollback_errors)}" if rollback_errors else ""
        logger.error(
            "Document replacement rolled back filename=%s document_id=%s error_type=%s rollback_errors=%s",
            filename, document_id, type(exc).__name__, len(rollback_errors),
        )
        raise HTTPException(
            status_code=500,
            detail=f"文档版本替换失败，已执行回滚：{exc}{rollback_detail}",
        ) from exc

    logger.info(
        "Document upload succeeded filename=%s document_id=%s file_type=%s chunk_count=%s status=indexed",
        filename, document_id, document_metadata["file_type"], vector_result["count"],
    )
    return {
        "file_path": final_path,
        "content": content,
        "chunks": chunks,
        "vector_count": vector_result["count"],
        "document_id": document_metadata["document_id"],
        "filename": document_metadata["filename"],
        "file_type": document_metadata["file_type"],
        "file_size": document_metadata["file_size"],
        "category": document_metadata.get("category"),
        "folder_id": document_metadata.get("folder_id"),
        "folder_name": document_metadata.get("folder_name"),
        "status": document_metadata["status"],
        "uploaded_at": document_metadata["uploaded_at"],
        "uploader_id": document_metadata.get("uploader_id"),
        "department_id": document_metadata.get("department_id"),
        "team_id": document_metadata.get("team_id"),
        "visibility": document_metadata.get("visibility"),
    }


def remove_document_file(filename: str):
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        file_path.unlink()
        return True
    return False


def list_documents():
    try:
        result = collection.get(include=["metadatas"])
    except Exception as exc:
        logger.error("Document list read failed error_type=%s", type(exc).__name__)
        raise HTTPException(status_code=500, detail=f"读取知识库 metadata 失败：{exc}") from exc

    metadatas = result.get("metadatas") or []
    if not metadatas:
        return []

    documents_by_id = {}
    for metadata in metadatas:
        if not isinstance(metadata, dict):
            continue

        filename = metadata.get("filename")
        document_id = metadata.get("document_id")
        document_key = document_id or filename
        if not document_key:
            continue

        if document_key not in documents_by_id:
            file_type = metadata.get("file_type")
            file_size = metadata.get("file_size")
            local_path = UPLOAD_DIR / filename if filename else None
            if local_path and local_path.is_file():
                if file_size is None:
                    file_size = local_path.stat().st_size
                legacy_type = local_path.suffix
            else:
                legacy_type = f".{file_type}" if file_type else None

            documents_by_id[document_key] = {
                "document_id": document_id,
                "filename": filename,
                "file_type": file_type or (legacy_type.lstrip(".") if legacy_type else None),
                "file_size": file_size,
                "category": metadata.get("category"),
                "folder_id": metadata.get("folder_id"),
                "folder_name": metadata.get("folder_name"),
                "uploader_id": metadata.get("uploader_id"),
                "department_id": metadata.get("department_id"),
                "team_id": metadata.get("team_id"),
                "visibility": metadata.get("visibility"),
                "status": metadata.get("status"),
                "chunk_count": metadata.get("chunk_count"),
                "uploaded_at": metadata.get("uploaded_at"),
                "size": file_size,
                "type": legacy_type,
                "_actual_chunk_count": 0,
            }

        document = documents_by_id[document_key]
        document["_actual_chunk_count"] += 1
        for field in (
            "document_id",
            "filename",
            "file_type",
            "file_size",
            "category",
            "folder_id",
            "folder_name",
            "uploader_id",
            "department_id",
            "visibility",
            "status",
            "chunk_count",
            "uploaded_at",
        ):
            if document.get(field) is None and metadata.get(field) is not None:
                document[field] = metadata[field]

    documents = []
    for document in documents_by_id.values():
        declared_chunk_count = document.get("chunk_count")
        if not isinstance(declared_chunk_count, int) or declared_chunk_count < 1:
            document["chunk_count"] = document["_actual_chunk_count"]
        if document.get("size") is None:
            document["size"] = document.get("file_size")
        if document.get("type") is None and document.get("file_type"):
            document["type"] = f".{document['file_type']}"
        document["uploaded_at"] = _normalize_uploaded_at(document.get("uploaded_at"))
        document.pop("_actual_chunk_count")
        documents.append(document)

    return documents
