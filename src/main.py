"""エントリポイント.

タスクスケジューラ (Windows) / cron (Mac/Linux) から呼ばれる想定。

使い方:
    python -m src.main --config ./config/config.yaml
    python -m src.main --demo                    # APIキー不要のサンプル生成

正常終了で exit code 0, 1件以上の失敗で 1 を返す。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.converters.kml_builder import KmlBuilder
from src.demo_data import make_demo_chika, make_demo_hazard
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
    parser.add_argument(
        "--demo",
        action="store_true",
        help="外部APIを呼ばずに同梱サンプルから KML を生成 (動作確認用)",
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
    logger.info("自動マッピングシステム 開始 %s", "(DEMO MODE)" if args.demo else "")
    logger.info("=" * 60)

    if args.demo:
        return _run_demo(config, logger)

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


def _run_demo(config: dict, logger) -> int:
    """サンプルデータから KML を生成. 出力先・ファイル名は config を尊重."""
    output_cfg = config.get("output") or {}
    out_dir = Path(output_cfg.get("directory", "./output"))
    fmt = str(output_cfg.get("format", "kml"))

    chika_name = (config.get("chika") or {}).get("output_filename", "chika_latest.kml")
    hazard_name = (config.get("hazard") or {}).get(
        "output_filename", "hazard_latest.kml"
    )

    chika_builder = KmlBuilder(document_name="地価公示 (DEMO)", logger=logger)
    chika_builder.add_result(make_demo_chika())
    chika_out = chika_builder.save(out_dir / chika_name, fmt=fmt)
    logger.info("地価KML出力: %s", chika_out)

    hazard_builder = KmlBuilder(document_name="ハザードマップ (DEMO)", logger=logger)
    hazard_builder.add_result(make_demo_hazard())
    hazard_out = hazard_builder.save(out_dir / hazard_name, fmt=fmt)
    logger.info("ハザードKML出力: %s", hazard_out)

    logger.info("DEMO 完了: %s で Google Earth Pro から確認してください", out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
