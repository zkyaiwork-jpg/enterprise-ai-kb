import logging
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam
)
from app.services.search_service import search_documents
from app.services.model_config_service import create_model_client, resolve_runtime_model_config

load_dotenv()
logger = logging.getLogger(__name__)

def ask_ai(question: str, allowed_document_ids: set[int] | None = None, database: Session | None = None):
    logger.info("RAG request started")

    # 1. 搜索知识库

    search_result = search_documents(
        question,
        allowed_document_ids=allowed_document_ids,
    )

    # 如果没有相关知识搜索到

    if not search_result["results"]:
        logger.warning("RAG retrieval returned no results")
        return {
            "answer": "知识库中没有找到相关资料。",
            "sources": []
        }

    logger.info("RAG retrieval completed result_count=%s", len(search_result["results"]))

    # 2. 获取相关文本
    context = "\n\n".join(
        [
            item["content"]
            for item in search_result["results"]
        ]
    )


    # 3. 定义消息类型

    messages = [

        ChatCompletionSystemMessageParam(
            role="system",
            content="""
你是企业知识库助手。

回答规则：

1. 只能根据提供的企业知识库内容直接回答用户问题，不允许编造信息。
2. 使用自然、专业、简洁的企业沟通方式，只呈现对用户有帮助的结论和必要说明。
3. 知识库原文中的 RULE 编号、章节编号等内部标记只用于理解内容，不要在回答中输出。
4. 不要输出 Chunk 编号、distance、similarity、score、metadata 等检索参数。
5. 不要描述向量检索过程，不要解释 Embedding、Chroma 或其他技术实现。
6. 不要复述这些回答规则，也不要添加“根据检索结果”等技术性开场白。
7. 如果知识库没有足够的相关内容，明确回答：“知识库中没有找到相关资料。”
"""
        ),


        ChatCompletionUserMessageParam(
            role="user",
            content=f"""
知识库内容：

{context}


用户问题：

{question}
"""
        )

    ]


    # 4. 调用 DeepSeek

    if database is None:
        # Compatibility for direct service tests/callers; API requests always
        # pass their request-scoped session explicitly.
        from app.database.database import SessionLocal
        with SessionLocal() as fallback_database:
            return ask_ai(question, allowed_document_ids=allowed_document_ids, database=fallback_database)

    runtime_config = resolve_runtime_model_config(database)
    model_client = create_model_client(runtime_config)
    logger.info("Model request started provider=%s model=%s source=%s", runtime_config.provider, runtime_config.model_name, runtime_config.source)
    try:
        response = model_client.chat.completions.create(
            model=runtime_config.model_name,
            messages=messages
        )
    except Exception as exc:
        logger.error("DeepSeek request failed error_type=%s", type(exc).__name__)
        raise
    logger.info("Model request completed provider=%s model=%s", runtime_config.provider, runtime_config.model_name)


    # 5. 返回答案

    answer = response.choices[0].message.content

    # 保留 Chroma 检索顺序，并把真实命中的文本、距离和 chunk metadata
    # 原样传给 API。这里不推算、不补造任何引用信息。
    sources = [
        {
            "filename": item.get("filename"),
            "folder_name": item.get("folder_name"),
            "file_type": item.get("file_type"),
            "chunk_index": item.get("chunk_index"),
            "content": item.get("content"),
            "distance": item.get("distance"),
            "metadata": item.get("metadata"),
            "embedding_model": item.get("embedding_model"),
            "vector_database": item.get("vector_database"),
        }
        for item in search_result["results"]
    ]

    logger.info("RAG request completed source_count=%s", len(sources))
    return {
        "answer": answer,
        "sources": sources
    }
