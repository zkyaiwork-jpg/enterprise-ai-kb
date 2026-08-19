import os
from pathlib import Path
import sys
import traceback

import uvicorn


def write_bootstrap_log(message: str) -> None:
    configured_log_dir = os.getenv("APP_LOG_DIR")
    configured_app_data_dir = os.getenv("APP_DATA_DIR")
    if configured_log_dir:
        log_dir = Path(configured_log_dir)
    elif configured_app_data_dir:
        log_dir = Path(configured_app_data_dir) / "logs"
    else:
        log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "backend-bootstrap.log").open("a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")


def main() -> int:
    if not os.getenv("DEEPSEEK_API_KEY"):
        write_bootstrap_log("Backend startup failed:\nmissing DEEPSEEK_API_KEY")
        return 1

    try:
        write_bootstrap_log("backend bootstrap started")
        from app.main import app
        write_bootstrap_log("FastAPI application imported")
        # The windowed PyInstaller executable has no stderr stream. The app's
        # standard logging configuration already owns file output.
        uvicorn.run(app, host="127.0.0.1", port=8000, log_config=None)
        return 0
    except Exception:
        write_bootstrap_log(f"Backend startup failed:\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    # Returning an exit code through SystemExit is handled normally by
    # PyInstaller and does not open its unhandled-exception dialog.
    sys.exit(main())
