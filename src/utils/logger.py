"""ロギングユーティリティ.

日次ローテーションを行いつつ、コンソールにも出力する。
保持期間 (retention_days) を超えたログは自動削除する。
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import time
from pathlib import Path


def setup_logger(
    name: str = "sns_manager",
    log_dir: str | os.PathLike[str] = "./logs",
    level: str = "INFO",
    retention_days: int = 30,
) -> logging.Logger:
    """名前付きロガーを構築して返す.

    すでに設定済みなら同じインスタンスを返すので、複数回呼んでも安全。
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / f"{name}.log"

    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=max(retention_days, 1),
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    _purge_old_logs(log_path, retention_days)
    return logger


def _purge_old_logs(log_dir: Path, retention_days: int) -> None:
    cutoff = time.time() - retention_days * 86400
    for entry in log_dir.glob("*.log*"):
        try:
            if entry.stat().st_mtime < cutoff:
                entry.unlink(missing_ok=True)
        except OSError:
            continue
