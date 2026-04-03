#!/usr/bin/env bash
# =============================================================================
# SNS Manager — ローカル開発環境セットアップスクリプト
# 実行: bash setup_local.sh
# =============================================================================
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "$0")/backend" && pwd)"
ENV_FILE="$BACKEND_DIR/.env"

echo "=========================================="
echo "  SNS Manager ローカルセットアップ"
echo "=========================================="

# ── 既存 .env があればバックアップ ──────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
  echo "[!] 既存の .env を .env.bak にバックアップします"
  cp "$ENV_FILE" "$ENV_FILE.bak"
fi

# ── Python で鍵を生成 ─────────────────────────────────────────────────────────
echo "[1/4] 鍵を生成中..."

python3 - <<'PYEOF'
import base64, os, sys

# AES-256 キー（32バイト）
aes_key = base64.b64encode(os.urandom(32)).decode()

# RSA鍵ペアは OpenSSL で生成するため Python からはスキップ
print(f"AES_KEY={aes_key}")
PYEOF

AES_KEY=$(python3 -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())")

# RSA 鍵ペア生成（openssl使用）
PRIVATE_KEY=""
PUBLIC_KEY=""
if command -v openssl &>/dev/null; then
  TMP_DIR=$(mktemp -d)
  openssl genrsa -out "$TMP_DIR/private.pem" 2048 2>/dev/null
  openssl rsa -in "$TMP_DIR/private.pem" -pubout -out "$TMP_DIR/public.pem" 2>/dev/null
  # 改行を \n に変換してシングルライン化
  PRIVATE_KEY=$(awk 'NF{printf "%s\\n",$0}' "$TMP_DIR/private.pem")
  PUBLIC_KEY=$(awk 'NF{printf "%s\\n",$0}' "$TMP_DIR/public.pem")
  rm -rf "$TMP_DIR"
  echo "    RSA鍵ペアを生成しました"
else
  echo "[!] openssl が見つかりません。JWT_PRIVATE_KEY / JWT_PUBLIC_KEY は手動で設定してください"
fi

# ── .env ファイルを生成 ────────────────────────────────────────────────────────
echo "[2/4] .env ファイルを生成中..."

cat > "$ENV_FILE" <<ENVEOF
# =============================================================================
# SNS Manager — ローカル開発設定
# 生成日時: $(date '+%Y-%m-%d %H:%M:%S')
# =============================================================================

# Application
APP_NAME=SNS Manager
APP_VERSION=1.0.0
DEBUG=true
ALLOWED_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
APP_BASE_URL=http://localhost:8000

# Database (Docker で起動)
DATABASE_URL=postgresql+asyncpg://sns_user:sns_pass@localhost:5432/sns_manager

# Redis (Docker で起動)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# JWT (RS256)
JWT_PRIVATE_KEY="${PRIVATE_KEY}"
JWT_PUBLIC_KEY="${PUBLIC_KEY}"
JWT_ALGORITHM=RS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# AES-256-GCM 暗号化キー
AES_ENCRYPTION_KEY=${AES_KEY}
AES_KEY_ID=v1

# ── 有料サービス（ローカルでは空でOK） ──────────────────────────────────────
# Stripe（未設定時はモック動作）
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# AWS S3（未設定時はローカルファイルストレージ使用）
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=
AWS_REGION=ap-northeast-1

# SendGrid（未設定時はコンソール出力）
SENDGRID_API_KEY=
FROM_EMAIL=noreply@localhost

# ローカルファイルストレージパス
LOCAL_STORAGE_PATH=./media
ENVEOF

echo "    .env を生成しました: $ENV_FILE"

# ── media ディレクトリ作成 ────────────────────────────────────────────────────
echo "[3/4] メディアディレクトリを作成中..."
mkdir -p "$BACKEND_DIR/media"
echo "    $BACKEND_DIR/media を作成しました"

# ── Docker で DB + Redis 起動 ──────────────────────────────────────────────────
echo "[4/4] PostgreSQL・Redis を起動中..."
cd "$(dirname "$0")"
docker compose -f docker-compose.dev.yml up -d db redis
echo "    DB・Redis を起動しました"

# ── 完了メッセージ ────────────────────────────────────────────────────────────
echo ""
echo "=========================================="
echo "  セットアップ完了！"
echo "=========================================="
echo ""
echo "次のコマンドで起動してください:"
echo ""
echo "  # バックエンド（別ターミナル①）"
echo "  cd backend"
echo "  pip install -r requirements.txt"
echo "  alembic upgrade head"
echo "  uvicorn app.main:app --reload --port 8000"
echo ""
echo "  # Celery Worker（別ターミナル②）"
echo "  cd backend"
echo "  celery -A app.worker.celery_app worker --loglevel=info"
echo ""
echo "  # Celery Beat（別ターミナル③）"
echo "  cd backend"
echo "  celery -A app.worker.celery_app beat --loglevel=info"
echo ""
echo "  # フロントエンド（別ターミナル④）"
echo "  cd frontend"
echo "  npm install"
echo "  npm run dev"
echo ""
echo "  または Docker で一括起動:"
echo "  docker compose -f docker-compose.dev.yml up"
echo ""
echo "  ブラウザ: http://localhost:3000"
echo "  API Docs: http://localhost:8000/api/docs"
echo ""
