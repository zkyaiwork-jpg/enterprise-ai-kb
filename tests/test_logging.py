import logging

from app.core.logging import configure_logging


def _flush_managed_handlers():
    for handler in logging.getLogger().handlers:
        if getattr(handler, "_enterprise_ai_handler", False):
            handler.flush()


def test_logging_configuration_creates_log_files(tmp_path):
    configured_dir = configure_logging(tmp_path)
    _flush_managed_handlers()

    assert configured_dir == tmp_path
    assert (tmp_path / "app.log").is_file()
    assert (tmp_path / "error.log").is_file()


def test_error_log_only_receives_errors(tmp_path):
    configure_logging(tmp_path)
    logger = logging.getLogger("tests.logging")
    logger.info("safe info event")
    logger.error("safe error event")
    _flush_managed_handlers()

    app_content = (tmp_path / "app.log").read_text(encoding="utf-8")
    error_content = (tmp_path / "error.log").read_text(encoding="utf-8")

    assert "INFO tests.logging safe info event" in app_content
    assert "ERROR tests.logging safe error event" in app_content
    assert "safe error event" in error_content
    assert "safe info event" not in error_content
