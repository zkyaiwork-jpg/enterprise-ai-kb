"""Offline CrossEncoder rerank experiment on confirmed Baseline V2 bad cases."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from sentence_transformers import CrossEncoder

from scripts.evaluate_rag_baseline_v2_50 import (
    load_sql_documents,
    read_dataset,
    resolve_expected_id,
    validate_target_data,
)
from scripts.evaluate_rag_thresholds import raw_query


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "evals" / "results" / "rag_rerank_bad_cases_v1.csv"
RERANK_MODEL = "BAAI/bge-reranker-base"
MAIN_CASE_IDS = {"12", "23", "32", "41", "49"}
AMBIGUOUS_CASE_IDS = {"31"}
ALL_CASE_IDS = MAIN_CASE_IDS | AMBIGUOUS_CASE_IDS
TOP_K = 3

RANK_FIELDS = tuple(
    field
    for prefix in ("original", "rerank")
    for rank in range(1, TOP_K + 1)
    for field in (
        f"{prefix}_rank_{rank}_document_id",
        f"{prefix}_rank_{rank}_filename",
        f"{prefix}_rank_{rank}_chunk_index",
        f"{prefix}_rank_{rank}_distance" if prefix == "original"
        else f"{prefix}_rank_{rank}_score",
        f"{prefix}_rank_{rank}_content",
    )
)
OUTPUT_FIELDS = (
    "question_id", "question", "expected_document_id", "expected_filename",
    *RANK_FIELDS,
    "original_top1_hit", "rerank_top1_hit", "result",
    "evaluation_status", "rerank_model", "rerank_score_direction", "evaluated_at",
)


def load_cases() -> list[dict[str, str]]:
    rows = [row for row in read_dataset() if row["question_id"] in ALL_CASE_IDS]
    found = {row["question_id"] for row in rows}
    if found != ALL_CASE_IDS:
        raise ValueError(f"实验题号不完整：expected={sorted(ALL_CASE_IDS)}, actual={sorted(found)}")
    return sorted(rows, key=lambda row: int(row["question_id"]))


def record_rank(
    output: dict[str, Any], prefix: str, rank: int, item: dict[str, Any]
) -> None:
    metadata = item["metadata"]
    output[f"{prefix}_rank_{rank}_document_id"] = metadata.get("document_id", "")
    output[f"{prefix}_rank_{rank}_filename"] = metadata.get("filename", "")
    output[f"{prefix}_rank_{rank}_chunk_index"] = metadata.get("chunk_index", "")
    if prefix == "original":
        output[f"{prefix}_rank_{rank}_distance"] = item["distance"]
    else:
        output[f"{prefix}_rank_{rank}_score"] = item["rerank_score"]
    output[f"{prefix}_rank_{rank}_content"] = item["content"]


def classify(original_hit: int, rerank_hit: int) -> str:
    if not original_hit and rerank_hit:
        return "improved"
    if original_hit and not rerank_hit:
        return "degraded"
    if not original_hit and not rerank_hit:
        return "no_improvement"
    return "unchanged_hit"


def evaluate() -> list[dict[str, Any]]:
    cases = load_cases()
    ids_to_filenames, filenames_to_ids = load_sql_documents()
    validate_target_data(filenames_to_ids)
    raw_batches = raw_query(
        [case["question"] for case in cases], set(ids_to_filenames)
    )
    model = CrossEncoder(RERANK_MODEL, max_length=512, device="cpu")
    evaluated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    outputs: list[dict[str, Any]] = []

    for case, original_results in zip(cases, raw_batches):
        expected_id = resolve_expected_id(case, filenames_to_ids)
        # The reranker sees only question and candidate text. Expected labels and
        # filenames are used strictly after prediction for evaluation/reporting.
        pairs = [(case["question"], item["content"]) for item in original_results]
        scores = model.predict(pairs, show_progress_bar=False)
        scored_results = []
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

        original_top1_id = int(original_results[0]["metadata"]["document_id"])
        rerank_top1_id = int(reranked[0]["metadata"]["document_id"])
        original_hit = int(original_top1_id == expected_id)
        rerank_hit = int(rerank_top1_id == expected_id)
        output: dict[str, Any] = {field: "" for field in OUTPUT_FIELDS}
        output.update({
            "question_id": case["question_id"], "question": case["question"],
            "evaluation_status": (
                "main" if case["question_id"] in MAIN_CASE_IDS else "ambiguous"
            ),
            "expected_document_id": expected_id,
            "expected_filename": case["expected_filename"],
            "original_top1_hit": original_hit,
            "rerank_top1_hit": rerank_hit,
            # Ambiguous case 31 retains the mechanical comparison result but is
            # excluded from the main aggregate by evaluation_status.
            "result": classify(original_hit, rerank_hit),
            "rerank_model": RERANK_MODEL,
            "rerank_score_direction": "higher_is_more_relevant",
            "evaluated_at": evaluated_at,
        })
        for rank, item in enumerate(original_results, start=1):
            record_rank(output, "original", rank, item)
        for rank, item in enumerate(reranked, start=1):
            record_rank(output, "rerank", rank, item)
        outputs.append(output)
    return outputs


def main() -> int:
    rows = evaluate()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    main_rows = [row for row in rows if row["evaluation_status"] == "main"]
    improved = sum(row["result"] == "improved" for row in main_rows)
    print(f"主实验：{len(main_rows)} 题")
    print(f"原始 Top1：{sum(int(row['original_top1_hit']) for row in main_rows)}/5")
    print(f"Rerank Top1：{sum(int(row['rerank_top1_hit']) for row in main_rows)}/5")
    print(f"改善：{improved}/5")
    for row in rows:
        print(
            f"question_id={row['question_id']} status={row['evaluation_status']} "
            f"original={row['original_rank_1_filename']} "
            f"rerank={row['rerank_rank_1_filename']} result={row['result']}"
        )
    print(f"结果：{OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
