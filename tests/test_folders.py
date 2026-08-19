from fastapi.testclient import TestClient
import sqlite3


def test_create_and_list_folders(client: TestClient, tmp_path, monkeypatch):
    from app.services import folder_service

    monkeypatch.setattr(folder_service, "CHAT_HISTORY_DB", tmp_path / "application.db")

    created = client.post("/folders", json={"name": "AI知识"})
    assert created.status_code == 201
    folder = created.json()
    assert folder["id"]
    assert folder["name"] == "AI知识"
    assert folder["created_at"]

    response = client.get("/folders")
    assert response.status_code == 200
    assert response.json() == [folder]


def test_folder_name_validation_and_duplicate(client: TestClient, tmp_path, monkeypatch):
    from app.services import folder_service

    monkeypatch.setattr(folder_service, "CHAT_HISTORY_DB", tmp_path / "application.db")

    assert client.post("/folders", json={"name": "   "}).status_code == 400
    assert client.post("/folders", json={"name": "产品资料"}).status_code == 201
    duplicate = client.post("/folders", json={"name": "产品资料"})
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "文件夹名称已存在"


def test_folder_history_offsets_are_normalized_and_sorted_by_actual_instant(tmp_path, monkeypatch):
    from app.services import folder_service

    database_path = tmp_path / "application.db"
    monkeypatch.setattr(folder_service, "CHAT_HISTORY_DB", database_path)
    folder_service.init_folders_db()
    with sqlite3.connect(database_path) as connection:
        connection.executemany(
            "INSERT INTO folders(name, created_at) VALUES (?, ?)",
            [
                ("Earlier +08", "2026-08-17T21:00:00+08:00"),
                ("Later Z", "2026-08-17T13:30:00Z"),
            ],
        )

    folders = folder_service.list_folders()
    assert [folder["name"] for folder in folders] == ["Earlier +08", "Later Z"]
    assert [folder["created_at"] for folder in folders] == [
        "2026-08-17T13:00:00Z",
        "2026-08-17T13:30:00Z",
    ]
