"""設定ローダの環境変数展開テスト."""

from __future__ import annotations

from pathlib import Path

from src.utils.config import load_config


def test_env_expansion(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MY_KEY", "secret123")
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(
        "chika:\n  api_key: ${MY_KEY}\n  endpoint: http://example\n",
        encoding="utf-8",
    )
    cfg = load_config(cfg_file)
    assert cfg["chika"]["api_key"] == "secret123"
    assert cfg["chika"]["endpoint"] == "http://example"


def test_missing_file_raises(tmp_path: Path) -> None:
    try:
        load_config(tmp_path / "nope.yaml")
    except FileNotFoundError:
        return
    raise AssertionError("FileNotFoundError 期待")
