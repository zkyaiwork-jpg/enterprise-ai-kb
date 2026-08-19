import json
import sqlite3


def test_legacy_chat_history_offsets_are_normalized_and_sorted_by_actual_instant(
    isolated_chat_db,
):
    from app.services import chat_history_service

    chat_history_service.init_chat_history_db()
    with sqlite3.connect(isolated_chat_db) as connection:
        connection.executemany(
            """
            INSERT INTO chat_history(session_id, question, answer, sources, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("mixed", "Earlier +08", "A", json.dumps([]), "2026-08-17T21:00:00+08:00"),
                ("mixed", "Later Z", "B", json.dumps([]), "2026-08-17T13:30:00Z"),
            ],
        )

    sessions = chat_history_service.list_chat_sessions()
    assert len(sessions) == 1
    assert [message["question"] for message in sessions[0]["messages"]] == [
        "Earlier +08",
        "Later Z",
    ]
    assert sessions[0]["created_at"] == "2026-08-17T13:00:00Z"
    assert sessions[0]["updated_at"] == "2026-08-17T13:30:00Z"
    assert [message["created_at"] for message in sessions[0]["messages"]] == [
        "2026-08-17T13:00:00Z",
        "2026-08-17T13:30:00Z",
    ]


def test_chroma_uploaded_at_history_is_normalized_without_rewriting_metadata(monkeypatch):
    from app.services import document_service
    from conftest import FakeCollection

    collection = FakeCollection()
    historical_metadata = {
        "document_id": "historical-document",
        "filename": "historical.docx",
        "uploaded_at": "2026-08-17T21:15:09+08:00",
    }
    collection.add(
        ids=["historical-document:0"],
        documents=["historical content"],
        metadatas=[historical_metadata.copy()],
    )
    monkeypatch.setattr(document_service, "collection", collection)

    documents = document_service.list_documents()
    assert documents[0]["uploaded_at"] == "2026-08-17T13:15:09Z"
    assert collection.records["historical-document:0"]["metadata"]["uploaded_at"] == historical_metadata["uploaded_at"]


def test_unknown_naive_chroma_timestamp_is_not_assumed_to_be_utc(monkeypatch):
    from app.services import document_service
    from conftest import FakeCollection

    collection = FakeCollection()
    collection.add(
        ids=["unknown-document:0"],
        documents=["unknown content"],
        metadatas=[{
            "document_id": "unknown-document",
            "filename": "unknown.docx",
            "uploaded_at": "2026-08-17T13:15:09",
        }],
    )
    monkeypatch.setattr(document_service, "collection", collection)

    documents = document_service.list_documents()
    assert documents[0]["uploaded_at"] is None
