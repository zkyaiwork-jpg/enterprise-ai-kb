import os
from pathlib import Path
import subprocess
import sys


def test_backend_launcher_logs_missing_api_key_without_traceback(tmp_path):
    environment = os.environ.copy()
    environment.pop("DEEPSEEK_API_KEY", None)
    environment["APP_LOG_DIR"] = str(tmp_path / "logs")

    completed = subprocess.run(
        [sys.executable, "desktop/backend_launcher.py"],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )

    bootstrap_log = tmp_path / "logs" / "backend-bootstrap.log"
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr == ""
    assert bootstrap_log.is_file()
    assert bootstrap_log.read_text(encoding="utf-8").endswith(
        "Backend startup failed:\nmissing DEEPSEEK_API_KEY\n"
    )
