from __future__ import annotations

import logging
import sys
from pathlib import Path
from types import FrameType
from typing import Final

from loguru import logger

_LOGGERS_QUIET: Final[tuple[str, ...]] = (
    "httpx",
    "httpcore",
    "aiohttp",
    "asyncio",
    "httpcore.connection",
    "httpcore.http11",
    "uvicorn.access",
)

_DEV_ENVS: Final[frozenset[str]] = frozenset({"development", "dev", "local"})


class InterceptHandler(logging.Handler):
    """Пересылает записи stdlib `logging` в loguru (один формат в stderr)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame: FrameType | None = logging.currentframe()
        depth = 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _is_development(app_env: str | None) -> bool:
    return (app_env or "").strip().lower() in _DEV_ENVS


def configure_loguru(
    *,
    level: str = "INFO",
    app_env: str | None = None,
    colorize: bool | None = None,
    log_dir: str | None = "logs",
) -> None:
    """Настроить loguru и перехватить logging для библиотек с классическим API.

    В TTY — цвета и разделители; в pipe/Docker — плоский текст без ANSI.
    В development для исключений включается diagnose (переменные в стеке).
    Файл ``{log_dir}/app.log`` с ротацией при достижении 100 МБ (если ``log_dir`` не пустой).
    """
    log_level = level.upper()
    numeric = getattr(logging, log_level, logging.INFO)
    use_color = sys.stderr.isatty() if colorize is None else colorize
    dev = _is_development(app_env)

    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(numeric)

    for name in list(logging.root.manager.loggerDict.keys()):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True

    logger.remove()

    if use_color:
        fmt = (
            "<dim>{time:YYYY-MM-DD HH:mm:ss.SSS}</dim> "
            "<level>{level.name: <7}</level> "
            "<dim>│</dim> "
            "<magenta>{process.name}</magenta> "
            "<dim>│</dim> "
            "<cyan>{file.name}</cyan><dim>:</dim><yellow>{line}</yellow> "
            "<dim>│</dim> "
            "<level>{message}</level>\n{exception}"
        )
    else:
        fmt = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level.name: <7} | "
            "{process.name} | "
            "{file.name}:{line} | "
            "{message}\n{exception}"
        )

    logger.add(
        sys.stderr,
        level=log_level,
        format=fmt,
        colorize=use_color,
        backtrace=True,
        diagnose=dev,
        enqueue=False,
    )

    log_root = (log_dir or "").strip()
    if log_root:
        path = Path(log_root)
        path.mkdir(parents=True, exist_ok=True)
        log_file = path / "app.log"
        try:
            logger.add(
                str(log_file),
                level=log_level,
                format=fmt,
                colorize=False,
                backtrace=True,
                diagnose=dev,
                rotation="100 MB",
                encoding="utf-8",
                enqueue=True,
            )
        except OSError as exc:
            logger.warning(
                "Log file not writable ({}): {} — stderr only",
                log_file,
                exc,
            )

    for name in _LOGGERS_QUIET:
        logging.getLogger(name).setLevel(logging.WARNING)

    # Без echo в engine SQL всё равно может сыпаться на INFO — тише для читаемых логов.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
