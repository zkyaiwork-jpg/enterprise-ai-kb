"""Full offline regression of Baseline versus Top3 CrossEncoder reranking."""
from __future__ import annotations

import csv
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from sentence_transformers import CrossEncoder

from app.services.embedding_service import MODEL_NAME
from scripts.evaluate_rag_baseline_v2_50 import (
    load_sql_documents,
    read_dataset as read_positive_dataset,
    resolve_expected_id,
    validate_target_data,
)
from scripts.evaluate_rag_thresholds import read_negative_dataset, raw_query


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_OUTPUT = PROJECT_ROOT / "evals" / "results" / "rag_rerank_regression_summary_v2.csv"
DETAILS_OUTPUT = PROJECT_ROOT / "evals" / "results" / "rag_rerank_regression_details_v2.csv"
RERANK_MODEL = "BAAI/bge-reranker-base"
TOP_K = 3
DISTANCE_THRESHOLD = 0.8
AMBIGUOUS_IDS = {"31"}

SUMMARY_FIELDS = (
    "method", "dataset", "total_questions", "top1_hit", "top1_accuracy",
    "top3_hit", "top3_accuracy", "no_result_count", "correct_reject",
    "false_positive", "chroma_time", "rerank_time", "total_time",
    "average_time", "timing_scope", "evaluated_at",
)
DETAIL_FIELDS = (
    "question_id", "question", "question_type", "expected_filename",
    "expected_document_id", "expected_result",
    "baseline_top1_document_id", "baseline_top1_filename",
    "baseline_top1_chunk_index", "baseline_top1_distance",
    "baseline_top1_hit", "baseline_top3_hit", "baseline_result_count",
    "baseline_correct_reject", "baseline_false_positive",
    "rerank_top1_document_id", "rerank_top1_filename",
    "rerank_top1_chunk_index", "rerank_top1_distance",
    "rerank_top1_score", "rerank_top1_hit", "rerank_top3_hit",
    "rerank_result_count", "rerank_correct_reject", "rerank_false_positive",
    "status", "retrieval_time_seconds", "baseline_postprocess_time_seconds",
    "baseline_total_time_seconds", "rerank_time_seconds",
    "rerank_total_time_seconds", "rerank_model", "embedding_model",
    "top_k", "distance_threshold", "evaluated_at",
)


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _document_id(item: dict[str, Any]) -> int:
    return int(item["metadata"]["document_id"])


def _record_top1(output: dict[str, Any], prefix: str, results: list[dict[str, Any]]) -> None:
    if not results:
        return
    item = results[0]
    metadata = item["metadata"]
    output[f"{prefix}_top1_document_id"] = metadata.get("document_id", "")
    output[f"{prefix}_top1_filename"] = metadata.get("filename", "")
    output[f"{prefix}_top1_chunk_index"] = metadata.get("chunk_index", "")
    output[f"{prefix}_top1_distance"] = item["distance"]
    if prefix == "rerank":
        output["rerank_top1_score"] = item["rerank_score"]


def _positive_status(question_id: str, baseline_hit: int, rerank_hit: int) -> str:
    if question_id in AMBIGUOUS_IDS:
        return "ambiguous"
    if not baseline_hit and rerank_hit:
        return "improved"
    if baseline_hit and not rerank_hit:
        return "degraded"
    if baseline_hit and rerank_hit:
        return "same_correct"
    return "same_wrong"


def _negative_status(baseline_reject: int, rerank_reject: int) -> str:
    if not baseline_reject and rerank_reject:
        return "improved"
    if baseline_reject and not rerank_reject:
        return "degraded"
    if baseline_reject and rerank_reject:
        return "same_correct"
    return "same_wrong"


def _summary_row(
    method: str,
    dataset: str,
    rows: list[dict[str, Any]],
    evaluated_at: str,
) -> dict[str, Any]:
    prefix = method
    total = len(rows)
    is_positive = dataset == "positive"
    top1_hits = sum(int(row[f"{prefix}_top1_hit"]) for row in rows) if is_positive else ""
    top3_hits = sum(int(row[f"{prefix}_top3_hit"]) for row in rows) if is_positive else ""
    correct_reject = (
        sum(int(row[f"{prefix}_correct_reject"]) for row in rows)
        if not is_positive else ""
    )
    false_positive = (
        sum(int(row[f"{prefix}_false_positive"]) for row in rows)
        if not is_positive else ""
    )
    retrieval_time = sum(float(row["retrieval_time_seconds"]) for row in rows)
    if method == "baseline":
        extra_time = sum(float(row["baseline_postprocess_time_seconds"]) for row in rows)
        rerank_time: float | str = ""
    else:
        extra_time = sum(float(row["rerank_time_seconds"]) for row in rows)
        rerank_time = extra_time
    total_time = retrieval_time + extra_time
    return {
        "method": method,
        "dataset": dataset,
        "total_questions": total,
        "top1_hit": top1_hits,
        "top1_accuracy": f"{top1_hits / total:.2%}" if is_positive else "",
        "top3_hit": top3_hits,
        "top3_accuracy": f"{top3_hits / total:.2%}" if is_positive else "",
        "no_result_count": sum(int(row[f"{prefix}_result_count"]) == 0 for row in rows),
        "correct_reject": correct_reject,
        "false_positive": false_positive,
        "chroma_time": f"{retrieval_time:.6f}",
        "rerank_time": f"{rerank_time:.6f}" if isinstance(rerank_time, float) else "",
        "total_time": f"{total_time:.6f}",
        "average_time": f"{total_time / total:.6f}",
        "timing_scope": "warm_models_per_query_embedding_plus_chroma",
        "evaluated_at": evaluated_at,
    }


def evaluate() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    positive_rows = read_positive_dataset()
    negative_rows = read_negative_dataset()
    ids_to_filenames, filenames_to_ids = load_sql_documents()
    validate_target_data(filenames_to_ids)
    allowed_document_ids = set(ids_to_filenames)
    reranker = CrossEncoder(
        RERANK_MODEL,
        max_length=512,
        device="cpu",
        local_files_only=True,
    )

    # Exclude one-time model/collection initialization from per-query timings.
    warm_candidates = raw_query(["性能测试预热"], allowed_document_ids)[0]
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

    for index, row in enumerate(combined, start=1):
        retrieval_started = time.perf_counter()
        original_results = raw_query([row["question"]], allowed_document_ids)[0]
        retrieval_time = time.perf_counter() - retrieval_started

        baseline_started = time.perf_counter()
        baseline_results = [
            item for item in original_results if item["distance"] < DISTANCE_THRESHOLD
        ]
        baseline_postprocess_time = time.perf_counter() - baseline_started

        rerank_started = time.perf_counter()
        pairs = [(row["question"], item["content"]) for item in original_results]
        scores = reranker.predict(pairs, show_progress_bar=False)
        scored_results: list[dict[str, Any]] = []
        for original_rank, (item, score) in enumerate(
            zip(original_results, scores), start=1
        ):
            scored = dict(item)
            scored["rerank_score"] = float(score)
            scored["original_rank"] = original_rank
            scored_results.append(scored)
        reranked = sorted(
            scored_results,
            key=lambda item: (-item["rerank_score"], item["original_rank"]),
        )
        rerank_results = [
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
            "baseline_result_count": len(baseline_results),
            "rerank_result_count": len(rerank_results),
            "retrieval_time_seconds": f"{retrieval_time:.6f}",
            "baseline_postprocess_time_seconds": f"{baseline_postprocess_time:.6f}",
            "baseline_total_time_seconds": f"{retrieval_time + baseline_postprocess_time:.6f}",
            "rerank_time_seconds": f"{rerank_time:.6f}",
            "rerank_total_time_seconds": f"{retrieval_time + rerank_time:.6f}",
            "rerank_model": RERANK_MODEL,
            "embedding_model": MODEL_NAME,
            "top_k": TOP_K,
            "distance_threshold": DISTANCE_THRESHOLD,
            "evaluated_at": evaluated_at,
        })
        _record_top1(output, "baseline", baseline_results)
        _record_top1(output, "rerank", rerank_results)

        if row["dataset"] == "positive":
            expected_id = resolve_expected_id(row, filenames_to_ids)
            baseline_ids = [_document_id(item) for item in baseline_results]
            rerank_ids = [_document_id(item) for item in rerank_results]
            baseline_top1_hit = int(bool(baseline_ids) and baseline_ids[0] == expected_id)
            rerank_top1_hit = int(bool(rerank_ids) and rerank_ids[0] == expected_id)
            output.update({
                "expected_document_id": expected_id,
                "baseline_top1_hit": baseline_top1_hit,
                "baseline_top3_hit": int(expected_id in baseline_ids[:TOP_K]),
                "rerank_top1_hit": rerank_top1_hit,
                "rerank_top3_hit": int(expected_id in rerank_ids[:TOP_K]),
                "status": _positive_status(
                    row["question_id"], baseline_top1_hit, rerank_top1_hit
                ),
            })
        else:
            baseline_reject = int(not baseline_results)
            rerank_reject = int(not rerank_results)
            output.update({
                "baseline_correct_reject": baseline_reject,
                "baseline_false_positive": int(bool(baseline_results)),
                "rerank_correct_reject": rerank_reject,
                "rerank_false_positive": int(bool(rerank_results)),
                "status": _negative_status(baseline_reject, rerank_reject),
            })
        details.append(output)
        print(
            f"progress={index}/60 question_id={row['question_id']} "
            f"status={output['status']}",
            flush=True,
        )

    positive_details = details[:len(positive_rows)]
    negative_details = details[len(positive_rows):]
    summary = [
        _summary_row("baseline", "positive", positive_details, evaluated_at),
        _summary_row("rerank", "positive", positive_details, evaluated_at),
        _summary_row("baseline", "negative", negative_details, evaluated_at),
        _summary_row("rerank", "negative", negative_details, evaluated_at),
    ]
    return summary, details


def main() -> int:
    summary, details = evaluate()
    _write_csv(SUMMARY_OUTPUT, SUMMARY_FIELDS, summary)
    _write_csv(DETAILS_OUTPUT, DETAIL_FIELDS, details)
    for row in summary:
        print(
            f"{row['method']} {row['dataset']} top1={row['top1_hit']} "
            f"top3={row['top3_hit']} reject={row['correct_reject']} "
            f"false_positive={row['false_positive']} avg={row['average_time']}s",
            flush=True,
        )
    print(f"总体结果：{SUMMARY_OUTPUT}", flush=True)
    print(f"详细结果：{DETAILS_OUTPUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
