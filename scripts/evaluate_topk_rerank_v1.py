"""Offline comparison of Top3, Top5, and Top10 Chroma candidates plus rerank."""
from __future__ import annotations

import csv
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from sentence_transformers import CrossEncoder

from app.services.embedding_service import MODEL_NAME, encode_texts
from app.services.vector_store import collection
from scripts.evaluate_rag_baseline_v2_50 import (
    load_sql_documents,
    read_dataset as read_positive_dataset,
    resolve_expected_id,
    validate_target_data,
)
from scripts.evaluate_rag_thresholds import read_negative_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASELINE_RESULTS = PROJECT_ROOT / "evals" / "results" / "rag_baseline_results_v2_50.csv"
THRESHOLD_RESULTS = PROJECT_ROOT / "evals" / "results" / "rag_threshold_comparison_v1.csv"
SUMMARY_OUTPUT = PROJECT_ROOT / "evals" / "results" / "rag_topk_rerank_comparison_v1.csv"
DETAILS_OUTPUT = PROJECT_ROOT / "evals" / "results" / "rag_topk_rerank_details_v1.csv"
TOP_K_VALUES = (3, 5, 10)
DISTANCE_THRESHOLD = 0.8
RERANK_MODEL = "BAAI/bge-reranker-base"

SUMMARY_FIELDS = (
    "method", "top_k", "dataset", "total_questions", "top1_hit",
    "top1_accuracy", "top3_hit", "top3_accuracy", "no_result_count",
    "correct_reject", "correct_reject_rate", "false_positive",
    "false_positive_rate", "chroma_time", "rerank_time", "total_time",
    "average_time", "timing_scope", "evaluated_at",
)
DETAIL_FIELDS = (
    "question_id", "question", "question_type", "expected_filename",
    "expected_document_id", "expected_result", "top_k",
    "original_candidates_count", "original_top1_document_id",
    "original_top1_filename", "original_top1_chunk_index",
    "original_top1_distance", "rerank_top1_document_id",
    "rerank_top1_filename", "rerank_top1_chunk_index",
    "rerank_top1_distance", "rerank_top1_score", "top1_hit", "top3_hit",
    "result_count", "correct_reject", "false_positive", "baseline_top1_hit",
    "status", "chroma_time_seconds", "rerank_time_seconds",
    "total_time_seconds", "rerank_model", "embedding_model",
    "distance_threshold", "evaluated_at",
)


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _raw_query(
    question: str, allowed_document_ids: set[int], top_k: int
) -> list[dict[str, Any]]:
    vector = encode_texts([question])
    raw = collection.query(
        query_embeddings=vector.tolist(),
        n_results=top_k,
        where={"document_id": {"$in": sorted(allowed_document_ids)}},
        include=["documents", "distances", "metadatas"],
    )
    return [
        {"content": content, "distance": distance, "metadata": metadata}
        for content, distance, metadata in zip(
            raw["documents"][0], raw["distances"][0], raw["metadatas"][0]
        )
    ]


def _read_baseline_top1() -> dict[str, int]:
    with BASELINE_RESULTS.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    if len(rows) != 50:
        raise ValueError(f"Baseline 结果必须为 50 题，实际为 {len(rows)}")
    return {row["question_id"]: int(row["top1_hit"]) for row in rows}


def _validate_negative_baseline() -> None:
    with THRESHOLD_RESULTS.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    row = next((item for item in rows if item["threshold"] == "0.80"), None)
    if row is None or row["negative_reject_count"] != "10":
        raise ValueError("Threshold V1 没有确认 0.80 下负向题 10/10 拒绝")


def _document_id(item: dict[str, Any]) -> int:
    return int(item["metadata"]["document_id"])


def _record_candidate(
    output: dict[str, Any], prefix: str, item: dict[str, Any] | None
) -> None:
    if item is None:
        return
    metadata = item["metadata"]
    output[f"{prefix}_top1_document_id"] = metadata.get("document_id", "")
    output[f"{prefix}_top1_filename"] = metadata.get("filename", "")
    output[f"{prefix}_top1_chunk_index"] = metadata.get("chunk_index", "")
    output[f"{prefix}_top1_distance"] = item["distance"]
    if prefix == "rerank":
        output["rerank_top1_score"] = item["rerank_score"]


def _status(baseline_correct: int, current_correct: int) -> str:
    if not baseline_correct and current_correct:
        return "improved"
    if baseline_correct and not current_correct:
        return "degraded"
    if baseline_correct and current_correct:
        return "same_correct"
    return "same_wrong"


def _summary(
    top_k: int, dataset: str, rows: list[dict[str, Any]], evaluated_at: str
) -> dict[str, Any]:
    total = len(rows)
    positive = dataset == "positive"
    top1_hits = sum(int(row["top1_hit"]) for row in rows) if positive else ""
    top3_hits = sum(int(row["top3_hit"]) for row in rows) if positive else ""
    rejects = sum(int(row["correct_reject"]) for row in rows) if not positive else ""
    false_positives = (
        sum(int(row["false_positive"]) for row in rows) if not positive else ""
    )
    chroma_time = sum(float(row["chroma_time_seconds"]) for row in rows)
    rerank_time = sum(float(row["rerank_time_seconds"]) for row in rows)
    total_time = chroma_time + rerank_time
    return {
        "method": "rerank",
        "top_k": top_k,
        "dataset": dataset,
        "total_questions": total,
        "top1_hit": top1_hits,
        "top1_accuracy": f"{top1_hits / total:.2%}" if positive else "",
        "top3_hit": top3_hits,
        "top3_accuracy": f"{top3_hits / total:.2%}" if positive else "",
        "no_result_count": sum(int(row["result_count"]) == 0 for row in rows),
        "correct_reject": rejects,
        "correct_reject_rate": f"{rejects / total:.2%}" if not positive else "",
        "false_positive": false_positives,
        "false_positive_rate": (
            f"{false_positives / total:.2%}" if not positive else ""
        ),
        "chroma_time": f"{chroma_time:.6f}",
        "rerank_time": f"{rerank_time:.6f}",
        "total_time": f"{total_time:.6f}",
        "average_time": f"{total_time / total:.6f}",
        "timing_scope": "warm_models_per_query_embedding_plus_chroma",
        "evaluated_at": evaluated_at,
    }


def evaluate() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    positive_rows = read_positive_dataset()
    negative_rows = read_negative_dataset()
    baseline_top1 = _read_baseline_top1()
    _validate_negative_baseline()
    ids_to_filenames, filenames_to_ids = load_sql_documents()
    validate_target_data(filenames_to_ids)
    allowed_document_ids = set(ids_to_filenames)
    reranker = CrossEncoder(
        RERANK_MODEL,
        max_length=512,
        device="cpu",
        local_files_only=True,
    )

    warm_candidates = _raw_query("性能测试预热", allowed_document_ids, 10)
    reranker.predict(
        [("性能测试预热", warm_candidates[0]["content"])],
        show_progress_bar=False,
    )

    combined = [
        {**row, "dataset": "positive"} for row in positive_rows
    ] + [
        {**row, "dataset": "negative"} for row in negative_rows
    ]
    evaluated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    details: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []

    for top_k in TOP_K_VALUES:
        scheme_rows: list[dict[str, Any]] = []
        for index, row in enumerate(combined, start=1):
            chroma_started = time.perf_counter()
            original = _raw_query(row["question"], allowed_document_ids, top_k)
            chroma_time = time.perf_counter() - chroma_started

            rerank_started = time.perf_counter()
            pairs = [(row["question"], item["content"]) for item in original]
            scores = reranker.predict(pairs, show_progress_bar=False)
            scored: list[dict[str, Any]] = []
            for original_rank, (item, score) in enumerate(
                zip(original, scores), start=1
            ):
                candidate = dict(item)
                candidate["rerank_score"] = float(score)
                candidate["original_rank"] = original_rank
                scored.append(candidate)
            reranked = sorted(
                scored,
                key=lambda item: (-item["rerank_score"], item["original_rank"]),
            )
            passed = [
                item for item in reranked if item["distance"] < DISTANCE_THRESHOLD
            ]
            rerank_time = time.perf_counter() - rerank_started

            output: dict[str, Any] = {field: "" for field in DETAIL_FIELDS}
            output.update({
                "question_id": row["question_id"],
                "question": row["question"],
                "question_type": row["question_type"],
                "expected_filename": row.get("expected_filename", ""),
                "expected_result": row.get("expected_result", ""),
                "top_k": top_k,
                "original_candidates_count": len(original),
                "result_count": len(passed),
                "chroma_time_seconds": f"{chroma_time:.6f}",
                "rerank_time_seconds": f"{rerank_time:.6f}",
                "total_time_seconds": f"{chroma_time + rerank_time:.6f}",
                "rerank_model": RERANK_MODEL,
                "embedding_model": MODEL_NAME,
                "distance_threshold": DISTANCE_THRESHOLD,
                "evaluated_at": evaluated_at,
            })
            _record_candidate(output, "original", original[0] if original else None)
            _record_candidate(output, "rerank", passed[0] if passed else None)

            if row["dataset"] == "positive":
                expected_id = resolve_expected_id(row, filenames_to_ids)
                passed_ids = [_document_id(item) for item in passed]
                top1_hit = int(bool(passed_ids) and passed_ids[0] == expected_id)
                output.update({
                    "expected_document_id": expected_id,
                    "top1_hit": top1_hit,
                    "top3_hit": int(expected_id in passed_ids[:3]),
                    "baseline_top1_hit": baseline_top1[row["question_id"]],
                    "status": _status(
                        baseline_top1[row["question_id"]], top1_hit
                    ),
                })
            else:
                reject = int(not passed)
                output.update({
                    "correct_reject": reject,
                    "false_positive": int(bool(passed)),
                    # Threshold V1 established that the current Baseline rejects
                    # all ten negative questions at distance < 0.8.
                    "baseline_top1_hit": 1,
                    "status": _status(1, reject),
                })
            details.append(output)
            scheme_rows.append(output)
            if index % 10 == 0:
                print(
                    f"progress top_k={top_k} {index}/60",
                    flush=True,
                )

        positive_details = scheme_rows[:len(positive_rows)]
        negative_details = scheme_rows[len(positive_rows):]
        summary.extend([
            _summary(top_k, "positive", positive_details, evaluated_at),
            _summary(top_k, "negative", negative_details, evaluated_at),
        ])
    return summary, details


def main() -> int:
    summary, details = evaluate()
    _write_csv(SUMMARY_OUTPUT, SUMMARY_FIELDS, summary)
    _write_csv(DETAILS_OUTPUT, DETAIL_FIELDS, details)
    for row in summary:
        print(
            f"TopK={row['top_k']} {row['dataset']} "
            f"Top1={row['top1_hit']} Top3={row['top3_hit']} "
            f"reject={row['correct_reject']} false_positive={row['false_positive']} "
            f"avg={row['average_time']}s",
            flush=True,
        )
    print(f"总体结果：{SUMMARY_OUTPUT}", flush=True)
    print(f"详细结果：{DETAILS_OUTPUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
