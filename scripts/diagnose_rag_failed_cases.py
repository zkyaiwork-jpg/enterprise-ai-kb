"""Inspect raw Chroma Top3 for Baseline V2 cases filtered by production threshold.

This diagnostic intentionally bypasses ``search_documents()``'s ``distance < 0.8``
post-filter. It does not alter the collection, production retrieval, or evaluation data.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.database.database import SessionLocal
from app.models.document import Document
from app.services.embedding_service import encode_texts
from app.services.vector_store import collection


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = PROJECT_ROOT / "evals" / "rag_baseline_questions_v2_50.csv"
OUTPUT = PROJECT_ROOT / "evals" / "results" / "rag_failed_cases_raw_top3_v2.csv"
CASE_IDS = {"23", "36", "49"}
TOP_K = 3

OUTPUT_FIELDS = (
    "question_id", "question", "expected_document_id", "expected_filename",
    *(field for rank in range(1, TOP_K + 1) for field in (
        f"raw_top{rank}_document_id", f"raw_top{rank}_filename",
        f"raw_top{rank}_chunk_index", f"raw_top{rank}_distance",
        f"raw_top{rank}_content",
    )),
    "diagnosed_at",
)


def load_cases() -> list[dict[str, str]]:
    with DATASET.open("r", encoding="utf-8-sig", newline="") as source:
        cases = [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(source)
            if (row.get("question_id") or "").strip() in CASE_IDS
        ]
    found_ids = {row["question_id"] for row in cases}
    if found_ids != CASE_IDS:
        raise ValueError(f"诊断题号不完整：expected={sorted(CASE_IDS)}, actual={sorted(found_ids)}")
    return sorted(cases, key=lambda row: int(row["question_id"]))


def load_document_maps() -> tuple[set[int], dict[str, int]]:
    with SessionLocal() as database:
        documents = database.execute(select(Document.id, Document.filename)).all()
    return {document_id for document_id, _ in documents}, {
        filename: document_id for document_id, filename in documents
    }


def diagnose() -> list[dict[str, Any]]:
    cases = load_cases()
    allowed_document_ids, filenames_to_ids = load_document_maps()
    diagnosed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    outputs: list[dict[str, Any]] = []
    for case in cases:
        expected_id = filenames_to_ids.get(case["expected_filename"])
        if expected_id is None:
            raise ValueError(f"SQL 中不存在正确文档：{case['expected_filename']}")
        query_vector = encode_texts([case["question"]])
        raw = collection.query(
            query_embeddings=query_vector.tolist(),
            n_results=TOP_K,
            where={"document_id": {"$in": sorted(allowed_document_ids)}},
            include=["documents", "distances", "metadatas"],
        )
        output: dict[str, Any] = {field: "" for field in OUTPUT_FIELDS}
        output.update({
            "question_id": case["question_id"],
            "question": case["question"],
            "expected_document_id": expected_id,
            "expected_filename": case["expected_filename"],
            "diagnosed_at": diagnosed_at,
        })
        documents = raw["documents"][0]
        distances = raw["distances"][0]
        metadatas = raw["metadatas"][0]
        for rank, (content, distance, metadata) in enumerate(
            zip(documents, distances, metadatas), start=1
        ):
            output[f"raw_top{rank}_document_id"] = metadata.get("document_id", "")
            output[f"raw_top{rank}_filename"] = metadata.get("filename", "")
            output[f"raw_top{rank}_chunk_index"] = metadata.get("chunk_index", "")
            output[f"raw_top{rank}_distance"] = distance
            output[f"raw_top{rank}_content"] = content
        outputs.append(output)
    return outputs


def main() -> int:
    rows = diagnose()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(f"question_id={row['question_id']}")
        for rank in range(1, TOP_K + 1):
            print(
                f"  Top{rank}: {row[f'raw_top{rank}_filename']} "
                f"chunk={row[f'raw_top{rank}_chunk_index']} "
                f"distance={row[f'raw_top{rank}_distance']}"
            )
    print(f"诊断结果：{OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
