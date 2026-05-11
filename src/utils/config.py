"""設定ファイル (YAML) ローダ.

環境変数で機微情報 (APIキー、SMTPパスワード等) を上書きできるように
``${ENV_VAR}`` 形式のプレースホルダ展開もサポートする。
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def load_config(path: str | os.PathLike[str]) -> dict[str, Any]:
    """YAML設定を読み込み、環境変数プレースホルダを解決して返す."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    return _expand_env(raw)


def _expand_env(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _expand_env(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_expand_env(v) for v in node]
    if isinstance(node, str):
        return _ENV_PATTERN.sub(lambda m: os.environ.get(m.group(1), ""), node)
    return node


def env_or_none(key_or_name: str | None) -> str | None:
    """設定中の ``*_env`` フィールド値を実際の環境変数に解決する."""
    if not key_or_name:
        return None
    return os.environ.get(key_or_name)
