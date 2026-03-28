from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

from src.infrastructure.logging_config import InterceptHandler, configure_loguru


def test_intercept_handler_unknown_level_falls_back_to_levelno() -> None:
    handler = InterceptHandler()
    record = logging.LogRecord(
        name="t",
        level=37,
        pathname="x",
        lineno=1,
        msg="m",
        args=(),
        exc_info=None,
    )
    record.levelname = "LEVEL37"
    with patch("src.infrastructure.logging_config.logger"):
        handler.emit(record)


def test_configure_loguru_file_sink_oserror(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    calls: list[object] = []

    def add_side_effect(*_a: object, **kwargs: object) -> int:
        calls.append(kwargs.get("enqueue"))
        if kwargs.get("enqueue") is True:
            msg = "disk full"
            raise OSError(msg)
        return 0

    with (
        patch("src.infrastructure.logging_config.logger.remove"),
        patch("src.infrastructure.logging_config.logger.add", side_effect=add_side_effect),
        patch("src.infrastructure.logging_config.logger.warning") as warn,
    ):
        configure_loguru(level="INFO", app_env="test", log_dir=str(log_dir))
    assert True in calls
    warn.assert_called()
