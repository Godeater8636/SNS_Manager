#!/usr/bin/env bash
# =============================================================================
# Mac / Linux cron 登録スクリプト
# =============================================================================
# 設計図 ③「数ヶ月ごとの特定日に自動で起動する」を cron で実現する。
# 既定: 1,4,7,10 月の毎月1日 03:00 (四半期)
#
# 使い方:
#   bash scripts/setup_mac_cron.sh
# =============================================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CONFIG_PATH="${CONFIG_PATH:-$PROJECT_ROOT/config/config.yaml}"
LOG_FILE="${LOG_FILE:-$PROJECT_ROOT/logs/cron.log}"
# 分 時 日 月 曜日   (四半期初日 03:00)
CRON_SCHEDULE="${CRON_SCHEDULE:-0 3 1 1,4,7,10 *}"
TAG="# SNS_Manager_AutoMapping"

mkdir -p "$PROJECT_ROOT/logs"

ENTRY="$CRON_SCHEDULE cd $PROJECT_ROOT && $PYTHON_BIN -m src.main --config $CONFIG_PATH >> $LOG_FILE 2>&1 $TAG"

# 既存の同タグエントリを除去してから新規追加 (再実行を冪等に)
TMP_CRON="$(mktemp)"
crontab -l 2>/dev/null | grep -v "$TAG" > "$TMP_CRON" || true
echo "$ENTRY" >> "$TMP_CRON"
crontab "$TMP_CRON"
rm -f "$TMP_CRON"

echo "cron 登録完了: $ENTRY"
echo "確認:  crontab -l"
