"""Evaluate the current production retrieval baseline without mutating business data."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.paths import VECTOR_DB_DIR
from app.database.database import DATABASE_PATH, SessionLocal
from app.models.document import Document
from app.services.embedding_service import MODEL_NAME


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "evals" / "rag_baseline.csv"
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "evals" / "results"
TOP_K = 3
# search_documents() currently applies this production threshold internally.
DISTANCE_THRESHOLD = 0.8
VECTOR_DATABASE = "ChromaDB"

INPUT_FIELDS = ("question", "expected_document_id", "expected_filename")
RANK_FIELDS = tuple(
    field
    for rank in range(1, TOP_K + 1)
    for field in (
        f"top{rank}_document_id",
        f"top{rank}_filename",
        f"top{rank}_chunk_index",
        f"top{rank}_distance",
    )
)
OUTPUT_FIELDS = (
    "case_index",
    "question",
    "expected_document_id",
    "expected_filename",
    *RANK_FIELDS,
    "top1_hit",
    "top3_hit",
    "result_count",
    "status",
    "error_type",
    "embedding_model",
    "vector_database",
    "top_k",
    "distance_threshold",
    "evaluated_at",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用当前正式search_documents()评测RAG检索Top1/Top3命中率",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"评测CSV路径（默认：{DEFAULT_DATASET}）",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_RESULTS_DIR,
        help=f"结果目录（默认：{DEFAULT_RESULTS_DIR}）",
    )
    return parser.parse_args()


def _read_dataset(dataset_path: Path) -> list[dict[str, str]]:
    with dataset_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing_fields = [field for field in INPUT_FIELDS if field not in (reader.fieldnames or [])]
        if missing_fields:
            raise ValueError(f"评测CSV缺少字段：{', '.join(missing_fields)}")
        return [
            {field: (row.get(field) or "").strip() for field in INPUT_FIELDS}
            for row in reader
        ]


def _load_document_scope() -> tuple[set[int], dict[int, str], dict[str, int]]:
    with SessionLocal() as database:
        documents = database.execute(select(Document.id, Document.filename)).all()
    ids_to_filenames = {document_id: filename for document_id, filename in documents}
    filenames_to_ids = {filename: document_id for document_id, filename in documents}
    return set(ids_to_filenames), ids_to_filenames, filenames_to_ids


def _validate_data_sources() -> None:
    """Fail before connecting when APP_DATA_DIR points at missing baseline data."""
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(f"SQL数据库不存在：{DATABASE_PATH}")
    if not VECTOR_DB_DIR.is_dir():
        raise FileNotFoundError(f"Chroma目录不存在：{VECTOR_DB_DIR}")


def _base_result(case_index: int, row: dict[str, str], evaluated_at: str) -> dict[str, Any]:
    result: dict[str, Any] = {field: "" for field in OUTPUT_FIELDS}
    result.update(
        {
            "case_index": case_index,
            "question": row["question"],
            "expected_document_id": row["expected_document_id"],
            "expected_filename": row["expected_filename"],
            "top1_hit": False,
            "top3_hit": False,
            "result_count": 0,
            "embedding_model": MODEL_NAME,
            "vector_database": VECTOR_DATABASE,
            "top_k": TOP_K,
            "distance_threshold": DISTANCE_THRESHOLD,
            "evaluated_at": evaluated_at,
        }
    )
    return result


def _resolve_expected_document(
    row: dict[str, str],
    allowed_document_ids: set[int],
    ids_to_filenames: dict[int, str],
    filenames_to_ids: dict[str, int],
) -> tuple[int | None, str | None]:
    question = row["question"]
    raw_document_id = row["expected_document_id"]
    expected_filename = row["expected_filename"]
    if not question or (not raw_document_id and not expected_filename):
        return None, "invalid_dataset"

    expected_document_id: int | None = None
    if raw_document_id:
        try:
            expected_document_id = int(raw_document_id)
        except ValueError:
            return None, "invalid_dataset"
        if expected_document_id <= 0:
            return None, "invalid_dataset"
        if expected_document_id not in allowed_document_ids:
            return None, "invalid_expected_outside_scope"

    filename_document_id: int | None = None
    if expected_filename:
        filename_document_id = filenames_to_ids.get(expected_filename)
        if filename_document_id is None:
            return None, "invalid_dataset"

    if expected_document_id is not None and filename_document_id is not None:
        if expected_document_id != filename_document_id:
            return None, "invalid_dataset"

    resolved_id = expected_document_id if expected_document_id is not None else filename_document_id
    if resolved_id is None:
        return None, "invalid_dataset"
    if expected_filename and ids_to_filenames.get(resolved_id) != expected_filename:
        return None, "invalid_dataset"
    return resolved_id, None


def _metadata_document_id(item: dict[str, Any]) -> int | None:
    metadata = item.get("metadata")
    if not isinstance(metadata, dict):
        return None
    try:
        return int(metadata.get("document_id"))
    except (TypeError, ValueError):
        return None


def _record_ranked_results(output: dict[str, Any], results: list[dict[str, Any]]) -> list[int | None]:
    ranked_document_ids: list[int | None] = []
    for rank, item in enumerate(results[:TOP_K], start=1):
        document_id = _metadata_document_id(item)
        ranked_document_ids.append(document_id)
        output[f"top{rank}_document_id"] = document_id if document_id is not None else ""
        output[f"top{rank}_filename"] = item.get("filename") or ""
        chunk_index = item.get("chunk_index")
        output[f"top{rank}_chunk_index"] = chunk_index if chunk_index is not None else ""
        distance = item.get("distance")
        output[f"top{rank}_distance"] = distance if distance is not None else ""
    return ranked_document_ids


def _evaluate_case(
    case_index: int,
    row: dict[str, str],
    evaluated_at: str,
    allowed_document_ids: set[int],
    ids_to_filenames: dict[int, str],
    filenames_to_ids: dict[str, int],
) -> dict[str, Any]:
    output = _base_result(case_index, row, evaluated_at)
    expected_document_id, invalid_status = _resolve_expected_document(
        row,
        allowed_document_ids,
        ids_to_filenames,
        filenames_to_ids,
    )
    if invalid_status:
        output["status"] = invalid_status
        return output

    output["expected_document_id"] = expected_document_id
    if not output["expected_filename"]:
        output["expected_filename"] = ids_to_filenames[expected_document_id]

    try:
        # Delayed until data-source preflight has passed; this is the production retriever.
        from app.services.search_service import search_documents

        search_result = search_documents(
            row["question"],
            top_k=TOP_K,
            allowed_document_ids=allowed_document_ids,
        )
    except Exception as exc:
        output["status"] = "search_error"
        output["error_type"] = type(exc).__name__
        return output

    results = search_result.get("results") or []
    output["result_count"] = len(results)
    if not results:
        output["status"] = "no_result"
        return output

    ranked_document_ids = _record_ranked_results(output, results)
    output["top1_hit"] = ranked_document_ids[0] == expected_document_id
    output["top3_hit"] = expected_document_id in ranked_document_ids[:TOP_K]
    output["status"] = "ok"
    return output


def _write_results(output_path: Path, rows: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _print_summary(rows: list[dict[str, Any]], output_path: Path) -> None:
    valid_rows = [row for row in rows if row["status"] in {"ok", "no_result"}]
    invalid_rows = [
        row
        for row in rows
        if row["status"] in {"invalid_dataset", "invalid_expected_outside_scope"}
    ]
    search_error_count = sum(row["status"] == "search_error" for row in rows)
    no_result_count = sum(row["status"] == "no_result" for row in rows)
    top1_hits = sum(row["top1_hit"] is True for row in valid_rows)
    top3_hits = sum(row["top3_hit"] is True for row in valid_rows)
    denominator = len(valid_rows)
    top1_rate = top1_hits / denominator if denominator else 0.0
    top3_rate = top3_hits / denominator if denominator else 0.0

    print(f"测试问题总数：{len(rows)}")
    print(f"有效评测数量：{denominator}")
    print(f"无结果数量：{no_result_count}")
    print(f"无效数据数量：{len(invalid_rows)}")
    print(f"检索错误数量：{search_error_count}")
    print(f"Top1命中数量：{top1_hits}")
    print(f"Top1命中率：{top1_rate:.2%}")
    print(f"Top3命中数量：{top3_hits}")
    print(f"Top3命中率：{top3_rate:.2%}")
    print(f"结果CSV：{output_path.resolve()}")


def main() -> int:
    args = _parse_args()
    dataset_path = args.dataset.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    dataset_rows = _read_dataset(dataset_path)
    _validate_data_sources()
    allowed_document_ids, ids_to_filenames, filenames_to_ids = _load_document_scope()
    run_time = datetime.now().astimezone()
    evaluated_at = run_time.isoformat(timespec="seconds")
    results = [
        _evaluate_case(
            case_index,
            row,
            evaluated_at,
            allowed_document_ids,
            ids_to_filenames,
            filenames_to_ids,
        )
        for case_index, row in enumerate(dataset_rows, start=1)
    ]
    output_path = output_dir / f"rag_baseline_{run_time.strftime('%Y%m%d_%H%M%S')}.csv"
    _write_results(output_path, results)
    _print_summary(results, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
