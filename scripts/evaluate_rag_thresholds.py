"""Compare retrieval thresholds offline without changing production RAG."""
from __future__ import annotations

import csv
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.embedding_service import encode_texts
from app.services.vector_store import collection
from scripts.evaluate_rag_baseline_v2_50 import (
    load_sql_documents,
    read_dataset as read_positive_dataset,
    resolve_expected_id,
    validate_target_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NEGATIVE_DATASET = PROJECT_ROOT / "evals" / "rag_negative_questions_v1_10.csv"
RESULTS_DIR = PROJECT_ROOT / "evals" / "results"
COMPARISON_OUTPUT = RESULTS_DIR / "rag_threshold_comparison_v1.csv"
NEGATIVE_OUTPUT = RESULTS_DIR / "rag_negative_results_v1.csv"
POSITIVE_DETAILS_OUTPUT = RESULTS_DIR / "rag_threshold_positive_details_v1.csv"
THRESHOLDS = (0.80, 0.85, 0.90, 0.95, 1.00, 1.05)
TOP_K = 3

RAW_RANK_FIELDS = tuple(
    field
    for rank in range(1, TOP_K + 1)
    for field in (
        f"raw_top{rank}_document_id", f"raw_top{rank}_filename",
        f"raw_top{rank}_chunk_index", f"raw_top{rank}_distance",
    )
)
NEGATIVE_FIELDS = (
    "question_id", "question", "question_type", "expected_result",
    *RAW_RANK_FIELDS, "evaluated_at",
)
POSITIVE_DETAIL_FIELDS = (
    "threshold", "question_id", "question", "question_type",
    "expected_document_id", "expected_filename",
    *(field for rank in range(1, TOP_K + 1) for field in (
        f"top{rank}_document_id", f"top{rank}_filename",
        f"top{rank}_chunk_index", f"top{rank}_distance",
    )),
    "result_count", "top1_hit", "top3_hit", "evaluated_at",
)
COMPARISON_FIELDS = (
    "threshold", "positive_count", "positive_top1_hits", "positive_top1_rate_pct",
    "positive_top3_hits", "positive_top3_rate_pct", "positive_no_result_count",
    "negative_count", "negative_reject_count", "negative_reject_rate_pct",
    "negative_false_retrieval_count", "negative_false_retrieval_rate_pct",
)


def read_negative_dataset() -> list[dict[str, str]]:
    with NEGATIVE_DATASET.open("r", encoding="utf-8-sig", newline="") as source:
        rows = [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(source)
        ]
    required_ids = {str(item) for item in range(51, 61)}
    if len(rows) != 10 or {row["question_id"] for row in rows} != required_ids:
        raise ValueError("负向题必须恰好为 question_id 51-60 的 10 题")
    if any(
        row["question_type"] != "negative"
        or row["expected_result"] != "no_relevant_document"
        for row in rows
    ):
        raise ValueError("负向题的 question_type/expected_result 不合法")
    return sorted(rows, key=lambda row: int(row["question_id"]))


def raw_query(
    questions: list[str], allowed_document_ids: set[int]
) -> list[list[dict[str, Any]]]:
    vectors = encode_texts(questions)
    raw = collection.query(
        query_embeddings=vectors.tolist(),
        n_results=TOP_K,
        where={"document_id": {"$in": sorted(allowed_document_ids)}},
        include=["documents", "distances", "metadatas"],
    )
    batches: list[list[dict[str, Any]]] = []
    for documents, distances, metadatas in zip(
        raw["documents"], raw["distances"], raw["metadatas"]
    ):
        batches.append([
            {"content": content, "distance": distance, "metadata": metadata}
            for content, distance, metadata in zip(documents, distances, metadatas)
        ])
    return batches


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def ranked_fields(output: dict[str, Any], prefix: str, results: list[dict[str, Any]]) -> None:
    for rank, item in enumerate(results[:TOP_K], start=1):
        metadata = item["metadata"]
        output[f"{prefix}_top{rank}_document_id"] = metadata.get("document_id", "")
        output[f"{prefix}_top{rank}_filename"] = metadata.get("filename", "")
        output[f"{prefix}_top{rank}_chunk_index"] = metadata.get("chunk_index", "")
        output[f"{prefix}_top{rank}_distance"] = item["distance"]


def evaluate() -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]
]:
    positive_rows = read_positive_dataset()
    negative_rows = read_negative_dataset()
    ids_to_filenames, filenames_to_ids = load_sql_documents()
    validate_target_data(filenames_to_ids)
    allowed_document_ids = set(ids_to_filenames)
    evaluated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    positive_raw = raw_query(
        [row["question"] for row in positive_rows], allowed_document_ids
    )
    negative_raw = raw_query(
        [row["question"] for row in negative_rows], allowed_document_ids
    )

    negative_outputs: list[dict[str, Any]] = []
    for row, results in zip(negative_rows, negative_raw):
        output = {field: "" for field in NEGATIVE_FIELDS}
        output.update(row)
        output["evaluated_at"] = evaluated_at
        ranked_fields(output, "raw", results)
        negative_outputs.append(output)

    positive_details: list[dict[str, Any]] = []
    comparison: list[dict[str, Any]] = []
    for threshold in THRESHOLDS:
        top1_hits = 0
        top3_hits = 0
        positive_no_result_count = 0
        for row, raw_results in zip(positive_rows, positive_raw):
            expected_id = resolve_expected_id(row, filenames_to_ids)
            passed = [item for item in raw_results if item["distance"] < threshold]
            ranked_ids = [int(item["metadata"]["document_id"]) for item in passed]
            top1_hit = int(bool(ranked_ids) and ranked_ids[0] == expected_id)
            top3_hit = int(expected_id in ranked_ids[:TOP_K])
            top1_hits += top1_hit
            top3_hits += top3_hit
            positive_no_result_count += int(not passed)
            detail = {field: "" for field in POSITIVE_DETAIL_FIELDS}
            detail.update({
                "threshold": f"{threshold:.2f}",
                "question_id": row["question_id"], "question": row["question"],
                "question_type": row["question_type"],
                "expected_document_id": expected_id,
                "expected_filename": row["expected_filename"],
                "result_count": len(passed), "top1_hit": top1_hit,
                "top3_hit": top3_hit, "evaluated_at": evaluated_at,
            })
            ranked_fields(detail, "", passed)
            # ranked_fields uses a leading underscore when prefix is empty.
            for rank in range(1, TOP_K + 1):
                for suffix in ("document_id", "filename", "chunk_index", "distance"):
                    detail[f"top{rank}_{suffix}"] = detail.pop(f"_top{rank}_{suffix}", "")
            positive_details.append(detail)

        negative_reject_count = sum(
            not any(item["distance"] < threshold for item in results)
            for results in negative_raw
        )
        negative_false_retrieval_count = len(negative_rows) - negative_reject_count
        comparison.append({
            "threshold": f"{threshold:.2f}",
            "positive_count": len(positive_rows),
            "positive_top1_hits": top1_hits,
            "positive_top1_rate_pct": f"{top1_hits / len(positive_rows) * 100:.2f}",
            "positive_top3_hits": top3_hits,
            "positive_top3_rate_pct": f"{top3_hits / len(positive_rows) * 100:.2f}",
            "positive_no_result_count": positive_no_result_count,
            "negative_count": len(negative_rows),
            "negative_reject_count": negative_reject_count,
            "negative_reject_rate_pct": f"{negative_reject_count / len(negative_rows) * 100:.2f}",
            "negative_false_retrieval_count": negative_false_retrieval_count,
            "negative_false_retrieval_rate_pct": f"{negative_false_retrieval_count / len(negative_rows) * 100:.2f}",
        })

    correct_distances: list[float] = []
    correct_missing = 0
    for row, results in zip(positive_rows, positive_raw):
        expected_id = resolve_expected_id(row, filenames_to_ids)
        matching = [
            item["distance"] for item in results
            if int(item["metadata"]["document_id"]) == expected_id
        ]
        if matching:
            correct_distances.append(min(matching))
        else:
            correct_missing += 1
    negative_top1_distances = [results[0]["distance"] for results in negative_raw]

    def stats(values: list[float]) -> dict[str, float]:
        return {
            "count": len(values), "min": min(values),
            "median": statistics.median(values),
            "mean": statistics.fmean(values), "max": max(values),
        }

    distribution = {
        "positive_nearest_expected_in_raw_top3": stats(correct_distances),
        "positive_expected_missing_from_raw_top3": correct_missing,
        "negative_raw_top1": stats(negative_top1_distances),
    }
    return comparison, negative_outputs, positive_details, distribution


def main() -> int:
    comparison, negatives, positive_details, distribution = evaluate()
    write_csv(COMPARISON_OUTPUT, COMPARISON_FIELDS, comparison)
    write_csv(NEGATIVE_OUTPUT, NEGATIVE_FIELDS, negatives)
    write_csv(POSITIVE_DETAILS_OUTPUT, POSITIVE_DETAIL_FIELDS, positive_details)
    for row in comparison:
        print(
            f"threshold={row['threshold']} "
            f"Top1={row['positive_top1_hits']}/50 "
            f"Top3={row['positive_top3_hits']}/50 "
            f"positive_no_result={row['positive_no_result_count']} "
            f"negative_reject={row['negative_reject_count']}/10 "
            f"negative_false_retrieval={row['negative_false_retrieval_count']}/10"
        )
    print(f"distance_distribution={distribution}")
    print(f"总体结果：{COMPARISON_OUTPUT}")
    print(f"负向详细：{NEGATIVE_OUTPUT}")
    print(f"正向详细：{POSITIVE_DETAILS_OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
