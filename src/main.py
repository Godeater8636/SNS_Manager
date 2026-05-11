"""エントリポイント.

タスクスケジューラ (Windows) / cron (Mac/Linux) から呼ばれる想定。

使い方:
    python -m src.main --config ./config/config.yaml

正常終了で exit code 0, 1件以上の失敗で 1 を返す。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.pipeline import Pipeline
from src.utils.config import load_config
from src.utils.logger import setup_logger


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Google Earth 不動産・リスク情報 自動マッピングシステム"
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent.parent / "config" / "config.yaml"),
        help="設定ファイル (YAML) のパス",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(args.config)

    log_cfg = config.get("logging") or {}
    logger = setup_logger(
        name="sns_manager",
        log_dir=log_cfg.get("directory", "./logs"),
        level=log_cfg.get("level", "INFO"),
        retention_days=int(log_cfg.get("retention_days", 30)),
    )

    logger.info("=" * 60)
    logger.info("自動マッピングシステム 開始")
    logger.info("=" * 60)

    try:
        result = Pipeline(config, logger).run()
    except Exception:  # noqa: BLE001
        logger.exception("パイプライン全体で予期せぬエラー")
        return 2

    if result.chika_output:
        logger.info("地価KML出力: %s", result.chika_output)
    if result.hazard_output:
        logger.info("ハザードKML出力: %s", result.hazard_output)

    return 0 if result.succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
