import chromadb
import logging
from app.core.paths import VECTOR_DB_DIR
from app.services.embedding_service import MODEL_NAME, encode_texts
from app.services import reranker_service

logger = logging.getLogger(__name__)

client = chromadb.PersistentClient(
    path=str(VECTOR_DB_DIR)
)


collection = client.get_or_create_collection(
    name="enterprise_documents"
)


def search_documents(
    query: str,
    top_k: int = 3,
    folder_id: int | None = None,
    file_type: str | None = None,
    allowed_document_ids: set[int] | None = None,
):
    logger.info("Knowledge search started top_k=%s", top_k)

    if not allowed_document_ids:
        logger.info(
            "Knowledge search skipped missing_or_empty_permission_scope=true"
        )
        return {"results": []}

    try:
        query_vector = encode_texts([query])
        filters = []
        if folder_id is not None:
            filters.append({"folder_id": folder_id})
        if file_type:
            filters.append({"file_type": file_type.lower()})
        filters.append({
            "document_id": {
                "$in": sorted(allowed_document_ids),
            }
        })
        where = None
        if len(filters) == 1:
            where = filters[0]
        elif filters:
            where = {"$and": filters}

        query_kwargs = {
            "query_embeddings": query_vector.tolist(),
            "n_results": top_k,
        }
        if where:
            query_kwargs["where"] = where
        result = collection.query(
            **query_kwargs
        )
    except Exception as exc:
        logger.error("Knowledge search failed top_k=%s error_type=%s", top_k, type(exc).__name__)
        raise

    authorized_candidates = []

    for doc, distance, metadata in zip(
            result["documents"][0],
            result["distances"][0],
            result["metadatas"][0]
    ):
        metadata_document_id = metadata.get("document_id")
        try:
            metadata_document_id = int(metadata_document_id)
        except (TypeError, ValueError):
            logger.warning("Knowledge search discarded invalid document_id metadata")
            continue
        if metadata_document_id not in allowed_document_ids:
            logger.warning(
                "Knowledge search discarded result outside permission scope document_id=%s",
                metadata_document_id,
            )
            continue

        authorized_candidates.append(
            {
                "content": doc,
                "distance": distance,
                "filename": metadata.get("filename"),
                "folder_id": metadata.get("folder_id"),
                "folder_name": metadata.get("folder_name"),
                "file_type": metadata.get("file_type"),
                # chunk_index 直接来自 Chroma metadata，供 RAG 返回精确引用来源。
                "chunk_index": metadata.get("chunk_index"),
                "metadata": metadata,
                "embedding_model": MODEL_NAME,
                "vector_database": "ChromaDB",
            }
        )

    ranked_candidates = authorized_candidates
    if authorized_candidates:
        try:
            ranked_candidates = reranker_service.rerank_documents(
                query,
                authorized_candidates,
            )
        except Exception as exc:
            # Rerank is an ordering enhancement. Preserve the permission-safe
            # Chroma order when loading or inference fails; never log content.
            logger.error(
                "Knowledge search rerank failed fallback=chroma_order "
                "candidate_count=%s error_type=%s",
                len(authorized_candidates),
                type(exc).__name__,
            )

    # 距离越小越相似；Rerank 只改变排序，不改变原始距离和阈值。
    results = [
        item
        for item in ranked_candidates
        if item["distance"] < 0.8
    ]

    logger.info("Knowledge search completed top_k=%s result_count=%s", top_k, len(results))
    return {
        "results": results
    }
