import json
import os
from pathlib import Path
import subprocess
import sys


def test_app_data_dir_controls_all_persistent_paths(tmp_path):
    app_data_dir = tmp_path / "electron-user-data" / "data"
    environment = os.environ.copy()
    environment["APP_DATA_DIR"] = str(app_data_dir)
    environment.pop("APP_LOG_DIR", None)

    script = """
import json
from app.core.paths import (
    APP_DATA_DIR, CHAT_HISTORY_DB, DOCUMENTS_DIR, LOG_DIR, VECTOR_DB_DIR
)
print(json.dumps({
    "app_data": str(APP_DATA_DIR),
    "vector_db": str(VECTOR_DB_DIR),
    "documents": str(DOCUMENTS_DIR),
    "chat_db": str(CHAT_HISTORY_DB),
    "logs": str(LOG_DIR),
    "directories_exist": all(path.is_dir() for path in (
        APP_DATA_DIR, VECTOR_DB_DIR, DOCUMENTS_DIR, LOG_DIR
    )),
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    paths = json.loads(completed.stdout)

    assert Path(paths["app_data"]) == app_data_dir.resolve()
    assert Path(paths["vector_db"]) == app_data_dir.resolve() / "vector_db"
    assert Path(paths["documents"]) == app_data_dir.resolve() / "documents"
    assert Path(paths["chat_db"]) == app_data_dir.resolve() / "chat_history.db"
    assert Path(paths["logs"]) == app_data_dir.resolve() / "logs"
    assert paths["directories_exist"] is True


def test_desktop_launcher_uses_environment_without_creating_links():
    main_source = (Path(__file__).parents[1] / "desktop" / "main.ts").read_text(encoding="utf-8")

    assert "APP_DATA_DIR: appDataDir" in main_source
    assert "symlinkSync" not in main_source
    assert "'junction'" not in main_source


def test_nsis_preserves_user_data_and_removes_only_legacy_junction():
    desktop_root = Path(__file__).parents[1] / "desktop"
    package = json.loads((desktop_root / "package.json").read_text(encoding="utf-8"))
    installer_script = (desktop_root / "build" / "installer.nsh").read_text(encoding="utf-8")

    assert package["build"]["nsis"]["deleteAppDataOnUninstall"] is False
    assert package["build"]["nsis"]["include"] == "build/installer.nsh"
    assert "!macro customInit" in installer_script
    assert "!macro customUnInit" in installer_script
    assert '/C rmdir "$INSTDIR\\resources\\backend\\_internal\\data"' in installer_script
    assert "RMDir /r" not in installer_script
    assert "AppData" not in installer_script
