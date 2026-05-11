"""自動処理パイプライン (設計図 ③ の本体).

実行フロー:
  1. 地価データ ① を MLIT から取得
  2. ハザードデータ ② を取得
  3. それぞれを KML/KMZ に変換
  4. ④ 出力フォルダに保存 (chika_latest.kml / hazard_latest.kml)
  5. エラーは notifier に集約

「⑤ Google Earth Pro のネットワークリンク」がこの出力フォルダを
参照する前提なので、ファイル名は固定 (上書き保存) する。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.converters.kml_builder import KmlBuilder
from src.fetchers.base import FetchResult
from src.fetchers.chika_fetcher import ChikaFetcher
from src.fetchers.hazard_fetcher import HazardFetcher
from src.notifier import Notifier
from src.utils.config import env_or_none
from src.utils.http_client import HttpClient


@dataclass
class PipelineResult:
    chika_output: Path | None = None
    hazard_output: Path | None = None
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

    @property
    def succeeded(self) -> bool:
        return not self.errors


class Pipeline:
    def __init__(self, config: dict[str, Any], logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger
        self.notifier = Notifier(config.get("notify") or {}, logger=logger)
        http_cfg = config.get("http") or {}
        self.http = HttpClient(
            timeout=int(http_cfg.get("timeout_seconds", 60)),
            retry_count=int(http_cfg.get("retry_count", 4)),
            backoff_seconds=float(http_cfg.get("retry_backoff_seconds", 2)),
            user_agent=str(
                http_cfg.get("user_agent", "SNS-Manager-AutoMapper/1.0")
            ),
            logger=logger,
        )

    def run(self) -> PipelineResult:
        result = PipelineResult()
        output_cfg = self.config.get("output") or {}
        out_dir = Path(output_cfg.get("directory", "./output"))
        fmt = str(output_cfg.get("format", "kml"))

        # 1. 地価
        chika_cfg = self.config.get("chika") or {}
        if chika_cfg.get("enabled", True):
            try:
                fetch = self._run_chika(chika_cfg)
                out = self._write_kml(
                    fetch,
                    out_dir / chika_cfg.get("output_filename", "chika_latest.kml"),
                    fmt,
                    document_name="地価公示",
                )
                result.chika_output = out
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("地価データ処理で失敗")
                msg = f"地価データ処理失敗: {exc}"
                result.errors.append(msg)
                self.notifier.notify_error("[自動マッピング] 地価データ失敗", msg)

        # 2. ハザード
        hazard_cfg = self.config.get("hazard") or {}
        if hazard_cfg.get("enabled", True):
            try:
                fetch = self._run_hazard(hazard_cfg)
                out = self._write_kml(
                    fetch,
                    out_dir / hazard_cfg.get("output_filename", "hazard_latest.kml"),
                    fmt,
                    document_name="ハザードマップ",
                )
                result.hazard_output = out
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("ハザードデータ処理で失敗")
                msg = f"ハザードデータ処理失敗: {exc}"
                result.errors.append(msg)
                self.notifier.notify_error("[自動マッピング] ハザード失敗", msg)

        if result.succeeded:
            self.logger.info("パイプライン完了: 全て成功")
        else:
            self.logger.error("パイプライン完了: %d 件のエラー", len(result.errors))
        return result

    # -- 各ステップ実装 --------------------------------------------------------

    def _run_chika(self, chika_cfg: dict[str, Any]) -> FetchResult:
        api_key = env_or_none(chika_cfg.get("api_key_env"))
        fetcher = ChikaFetcher(chika_cfg, self.http, api_key=api_key, logger=self.logger)
        return fetcher.fetch()

    def _run_hazard(self, hazard_cfg: dict[str, Any]) -> FetchResult:
        fetcher = HazardFetcher(hazard_cfg, self.http, logger=self.logger)
        return fetcher.fetch()

    def _write_kml(
        self,
        fetch: FetchResult,
        output_path: Path,
        fmt: str,
        document_name: str,
    ) -> Path:
        builder = KmlBuilder(document_name=document_name, logger=self.logger)
        builder.add_result(fetch)
        return builder.save(output_path, fmt=fmt)
