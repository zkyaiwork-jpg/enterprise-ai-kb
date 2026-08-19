"""Run the 50-question RAG retrieval Baseline V2 against production retrieval."""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.paths import VECTOR_DB_DIR
from app.database.database import DATABASE_PATH, SessionLocal
from app.models.document import Document
from app.services.embedding_service import MODEL_NAME


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = PROJECT_ROOT / "evals" / "rag_baseline_questions_v2_50.csv"
OUTPUT = PROJECT_ROOT / "evals" / "results" / "rag_baseline_results_v2_50.csv"
TARGET_FILENAMES = (
    "员工休假管理制度.docx",
    "员工考勤管理制度.docx",
    "差旅及费用报销制度.docx",
    "产品售后服务规范.docx",
    "信息安全管理规范.docx",
)
TOP_K = 3
DISTANCE_THRESHOLD = 0.8  # Mirrored for reporting; enforced by search_documents().

OUTPUT_FIELDS = (
    "question_id", "question", "question_type",
    "expected_document_id", "expected_filename",
    *(field for rank in range(1, TOP_K + 1) for field in (
        f"top{rank}_document_id", f"top{rank}_filename",
        f"top{rank}_chunk_index", f"top{rank}_distance",
    )),
    "top1_hit", "top3_hit", "result_count", "status", "error_type",
    "embedding_model", "vector_database", "top_k", "distance_threshold",
    "evaluated_at",
)


def read_dataset() -> list[dict[str, str]]:
    with DATASET.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {
            "question_id", "question", "expected_document_id",
            "expected_filename", "question_type",
        }
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"评测 CSV 缺少字段：{', '.join(sorted(missing))}")
        rows = [{key: (value or "").strip() for key, value in row.items()} for row in reader]
    if len(rows) != 50:
        raise ValueError(f"Baseline V2 必须恰好 50 题，实际为 {len(rows)} 题")
    if len({row["question_id"] for row in rows}) != 50:
        raise ValueError("question_id 存在空值或重复")
    return rows


def load_sql_documents() -> tuple[dict[int, str], dict[str, int]]:
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(f"SQL 数据库不存在：{DATABASE_PATH}")
    with SessionLocal() as database:
        documents = database.execute(select(Document.id, Document.filename)).all()
    ids_to_filenames = {document_id: filename for document_id, filename in documents}
    filenames_to_ids = {filename: document_id for document_id, filename in documents}
    return ids_to_filenames, filenames_to_ids


def validate_target_data(filenames_to_ids: dict[str, int]) -> dict[str, int]:
    """Abort before evaluation if any target SQL/Chroma mapping is incomplete."""
    if not VECTOR_DB_DIR.is_dir():
        raise FileNotFoundError(f"Chroma 目录不存在：{VECTOR_DB_DIR}")
    from app.services.vector_store import collection

    chunk_counts: dict[str, int] = {}
    problems: list[str] = []
    for filename in TARGET_FILENAMES:
        document_id = filenames_to_ids.get(filename)
        if document_id is None:
            problems.append(f"SQL 缺少文档：{filename}")
            continue
        found = collection.get(where={"document_id": document_id}, include=["metadatas"])
        ids = found.get("ids") or []
        metadatas = found.get("metadatas") or []
        chunk_counts[filename] = len(ids)
        if not ids:
            problems.append(f"Chroma 缺少 chunks：{filename} (document_id={document_id})")
        for chunk_id, metadata in zip(ids, metadatas):
            if str(metadata.get("document_id")) != str(document_id):
                problems.append(f"document_id 不一致：{chunk_id}")
            if metadata.get("filename") != filename:
                problems.append(f"filename 不一致：{chunk_id}")
    if problems:
        raise RuntimeError("数据完整性检查失败，停止评测：\n- " + "\n- ".join(problems))
    return chunk_counts


def resolve_expected_id(row: dict[str, str], filenames_to_ids: dict[str, int]) -> int:
    filename = row["expected_filename"]
    filename_id = filenames_to_ids.get(filename)
    if filename_id is None:
        raise ValueError(f"题 {row['question_id']} 的正确文档不在 SQL 中：{filename}")
    if row["expected_document_id"]:
        supplied_id = int(row["expected_document_id"])
        if supplied_id != filename_id:
            raise ValueError(f"题 {row['question_id']} 的 expected_document_id/filename 不一致")
    return filename_id


def evaluate(
    rows: list[dict[str, str]],
    ids_to_filenames: dict[int, str],
    filenames_to_ids: dict[str, int],
) -> list[dict[str, Any]]:
    from app.services.search_service import search_documents

    allowed_document_ids = set(ids_to_filenames)
    evaluated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    outputs: list[dict[str, Any]] = []
    for row in rows:
        expected_id = resolve_expected_id(row, filenames_to_ids)
        output: dict[str, Any] = {field: "" for field in OUTPUT_FIELDS}
        output.update({
            "question_id": row["question_id"], "question": row["question"],
            "question_type": row["question_type"], "expected_document_id": expected_id,
            "expected_filename": row["expected_filename"], "top1_hit": 0,
            "top3_hit": 0, "result_count": 0, "embedding_model": MODEL_NAME,
            "vector_database": "ChromaDB", "top_k": TOP_K,
            "distance_threshold": DISTANCE_THRESHOLD, "evaluated_at": evaluated_at,
        })
        try:
            search_result = search_documents(
                row["question"], top_k=TOP_K,
                allowed_document_ids=allowed_document_ids,
            )
            results = search_result.get("results") or []
            output["result_count"] = len(results)
            ranked_ids: list[int] = []
            for rank, item in enumerate(results[:TOP_K], start=1):
                metadata = item.get("metadata") or {}
                document_id = int(metadata["document_id"])
                ranked_ids.append(document_id)
                output[f"top{rank}_document_id"] = document_id
                output[f"top{rank}_filename"] = item.get("filename") or ""
                output[f"top{rank}_chunk_index"] = item.get("chunk_index", "")
                output[f"top{rank}_distance"] = item.get("distance", "")
            output["top1_hit"] = int(bool(ranked_ids) and ranked_ids[0] == expected_id)
            output["top3_hit"] = int(expected_id in ranked_ids[:TOP_K])
            output["status"] = "ok" if results else "no_result"
        except Exception as exc:
            output["status"] = "search_error"
            output["error_type"] = type(exc).__name__
        outputs.append(output)
    return outputs


def write_results(rows: list[dict[str, Any]]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict[str, Any]], chunk_counts: dict[str, int]) -> None:
    errors = [row for row in rows if row["status"] == "search_error"]
    if errors:
        raise RuntimeError(f"{len(errors)} 题检索失败，不输出不完整的成功率")
    top1 = sum(int(row["top1_hit"]) for row in rows)
    top3 = sum(int(row["top3_hit"]) for row in rows)
    by_type: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        by_type[row["question_type"]].update(
            count=1, top1=int(row["top1_hit"]), top3=int(row["top3_hit"])
        )
    print("数据完整性：")
    for filename in TARGET_FILENAMES:
        print(f"  {filename}: SQL ID={next(row['expected_document_id'] for row in rows if row['expected_filename'] == filename)}, chunks={chunk_counts[filename]}")
    print(f"Top1: {top1}/50 = {top1 / 50:.2%}")
    print(f"Top3: {top3}/50 = {top3 / 50:.2%}")
    for question_type, counts in by_type.items():
        print(f"{question_type}: n={counts['count']}, Top1={counts['top1']}/{counts['count']}, Top3={counts['top3']}/{counts['count']}")
    print(f"结果 CSV：{OUTPUT}")


def main() -> int:
    rows = read_dataset()
    ids_to_filenames, filenames_to_ids = load_sql_documents()
    chunk_counts = validate_target_data(filenames_to_ids)
    results = evaluate(rows, ids_to_filenames, filenames_to_ids)
    if any(row["status"] == "search_error" for row in results):
        print_summary(results, chunk_counts)
    write_results(results)
    print_summary(results, chunk_counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
