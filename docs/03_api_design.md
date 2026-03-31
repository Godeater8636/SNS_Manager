# API 設計書

**プロジェクト名**: X（Twitter）アフィリエイト特化型 SNS 管理ツール  
**バージョン**: 1.0.0  
**作成日**: 2026-03-31  
**ベース URL**: `https://api.sns-mgr.app/api/v1`  
**フレームワーク**: FastAPI (Python)  
**認証方式**: JWT Bearer Token（RS256）

---

## 1. 共通仕様

### 1.1 認証ヘッダー

```
Authorization: Bearer <access_token>
```

- アクセストークン有効期限: **15 分**
- リフレッシュトークン有効期限: **7 日**（HTTP-Only Cookie）

### 1.2 共通レスポンス形式

```json
// 成功
{
  "success": true,
  "data": { ... }
}

// エラー
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "入力値が不正です",
    "details": [ { "field": "email", "message": "有効なメールアドレスを入力してください" } ]
  }
}
```

### 1.3 エラーコード一覧

| HTTP Status | code | 説明 |
|-------------|------|------|
| 400 | `VALIDATION_ERROR` | バリデーションエラー |
| 401 | `UNAUTHORIZED` | 認証トークン不正・期限切れ |
| 403 | `FORBIDDEN` | 権限不足（プラン制限含む） |
| 404 | `NOT_FOUND` | リソース不存在 |
| 409 | `CONFLICT` | 重複エラー |
| 422 | `UNPROCESSABLE` | 処理不能（外部 API エラー等） |
| 429 | `RATE_LIMITED` | レートリミット超過 |
| 500 | `INTERNAL_ERROR` | サーバー内部エラー |

### 1.4 ページネーション

クエリパラメータ: `?page=1&per_page=20`  
レスポンス:

```json
{
  "success": true,
  "data": { "items": [...], "total": 100, "page": 1, "per_page": 20, "pages": 5 }
}
```

---

## 2. エンドポイント一覧

### 2.1 認証（Auth）

---

#### `POST /auth/register` — ユーザー登録

**リクエスト**
```json
{
  "email": "user@example.com",
  "password": "P@ssw0rd!",
  "display_name": "田中 太郎"
}
```

**レスポンス** `201 Created`
```json
{
  "success": true,
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "access_token": "<JWT>",
    "token_type": "bearer"
  }
}
```

---

#### `POST /auth/login` — ログイン

**リクエスト**
```json
{
  "email": "user@example.com",
  "password": "P@ssw0rd!",
  "totp_code": "123456"   // 2FA 有効時のみ必須
}
```

**レスポンス** `200 OK`  
`Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Strict; Max-Age=604800`

```json
{
  "success": true,
  "data": {
    "access_token": "<JWT>",
    "token_type": "bearer",
    "expires_in": 900
  }
}
```

---

#### `POST /auth/refresh` — トークンリフレッシュ

Cookie の `refresh_token` を使用して新しいアクセストークンを発行。

**レスポンス** `200 OK`
```json
{
  "success": true,
  "data": { "access_token": "<JWT>", "expires_in": 900 }
}
```

---

#### `POST /auth/logout` — ログアウト

リフレッシュトークンを無効化し Cookie を削除。

**レスポンス** `204 No Content`

---

#### `POST /auth/password-reset/request` — パスワードリセット要求

```json
{ "email": "user@example.com" }
```
**レスポンス** `200 OK`（メール送信済みメッセージ。存在有無は返さない）

---

#### `POST /auth/password-reset/confirm` — パスワードリセット確定

```json
{ "token": "<OTP>", "new_password": "NewP@ss1!" }
```
**レスポンス** `200 OK`

---

### 2.2 ユーザー（Users）

---

#### `GET /users/me` — プロフィール取得

**レスポンス** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "550e8400-...",
    "email": "user@example.com",
    "display_name": "田中 太郎",
    "plan": { "name": "pro", "display_name": "Pro", "expires_at": "2026-04-30T00:00:00Z" },
    "timezone": "Asia/Tokyo",
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

---

#### `PATCH /users/me` — プロフィール更新

```json
{ "display_name": "新しい名前", "timezone": "America/New_York" }
```
**レスポンス** `200 OK`（更新後のユーザーオブジェクト）

---

#### `POST /users/me/totp/enable` — 2FA 有効化

**レスポンス**
```json
{
  "success": true,
  "data": {
    "secret": "JBSWY3DPEHPK3PXP",
    "qr_url": "otpauth://totp/SNSManager%3Auser%40example.com?secret=..."
  }
}
```

---

### 2.3 X アカウント管理（Social Accounts）

---

#### `GET /social-accounts` — アカウント一覧

**レスポンス** `200 OK`
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "x_username": "myhandle",
        "x_display_name": "My Handle",
        "is_active": true,
        "last_login_at": "2026-03-30T10:00:00Z",
        "daily_likes_count": 45,
        "daily_follows_count": 12,
        "daily_like_limit": 200,
        "daily_follow_limit": 100
      }
    ],
    "total": 1
  }
}
```

---

#### `POST /social-accounts` — X アカウント追加

```json
{
  "x_username": "myhandle",
  "password": "xpassword123",
  "daily_like_limit": 150,
  "daily_follow_limit": 80,
  "action_min_interval_sec": 45,
  "action_max_interval_sec": 120,
  "active_hours_start": 8,
  "active_hours_end": 22
}
```

**レスポンス** `201 Created`（Twikit でログイン確認後に保存）

---

#### `GET /social-accounts/{account_id}` — アカウント詳細

**レスポンス** `200 OK`（上記と同形式、BAN 対策パラメータ含む）

---

#### `PATCH /social-accounts/{account_id}` — BAN 対策パラメータ更新

```json
{
  "daily_like_limit": 100,
  "action_min_interval_sec": 60,
  "burst_size": 8,
  "burst_rest_sec": 600
}
```

---

#### `DELETE /social-accounts/{account_id}` — アカウント削除

**レスポンス** `204 No Content`

---

#### `POST /social-accounts/{account_id}/refresh-session` — セッション更新

Twikit で再ログインし cookies.json を更新。

**レスポンス** `200 OK`
```json
{
  "success": true,
  "data": { "session_expires_at": "2026-04-07T10:00:00Z" }
}
```

---

### 2.4 投稿管理（Posts）

---

#### `GET /posts` — 投稿一覧

**クエリパラメータ**
- `status`: draft / scheduled / posted / failed
- `social_account_id`: UUID
- `from`: ISO8601 日時
- `to`: ISO8601 日時
- `page`, `per_page`

**レスポンス** `200 OK`（ページネーション形式）

---

#### `POST /posts` — 投稿作成（単体/スレッド）

```json
{
  "social_account_id": "uuid",
  "scheduled_at": "2026-04-01T09:00:00+09:00",
  "thread": [
    {
      "content": "アフィリエイト商品のご紹介 🎯 詳細はこちら → https://sns-mgr.app/l/abc123",
      "media_urls": ["https://s3.../image1.jpg"]
    },
    {
      "content": "続き：この商品の特徴は..."
    }
  ]
}
```

**レスポンス** `201 Created`
```json
{
  "success": true,
  "data": {
    "posts": [
      { "id": "uuid1", "thread_order": 1, "status": "scheduled", "scheduled_at": "2026-04-01T00:00:00Z" },
      { "id": "uuid2", "thread_order": 2, "status": "scheduled", "parent_post_id": "uuid1" }
    ]
  }
}
```

---

#### `GET /posts/{post_id}` — 投稿詳細

**レスポンス** `200 OK`（投稿情報 + analytics があれば含む）

---

#### `PATCH /posts/{post_id}` — 投稿編集

`status = 'draft'` または `'scheduled'` の投稿のみ編集可。

```json
{
  "content": "更新されたテキスト",
  "scheduled_at": "2026-04-02T10:00:00+09:00"
}
```

---

#### `DELETE /posts/{post_id}` — 投稿削除（キャンセル）

`status = 'posted'` の場合は `cancelled` に変更のみ（X 上の削除は別途）。  
**レスポンス** `204 No Content`

---

#### `POST /posts/import-csv` — CSV 一括インポート

**Content-Type**: `multipart/form-data`

```
social_account_id: UUID
file: schedule.csv
```

CSV フォーマット:
```csv
content,scheduled_at,media_url_1,media_url_2
"投稿テキスト1",2026-04-01T09:00:00+09:00,,
"投稿テキスト2",2026-04-02T12:00:00+09:00,https://...,
```

**レスポンス** `200 OK`
```json
{
  "success": true,
  "data": { "created": 10, "failed": 1, "errors": [{ "row": 5, "message": "日時フォーマット不正" }] }
}
```

---

#### `GET /posts/export-csv` — CSV エクスポート（分析）

**クエリパラメータ**: `from`, `to`, `social_account_id`  
**レスポンス**: `text/csv` ファイルダウンロード

CSV カラム:
```
post_id, content, scheduled_at, posted_at, status, impressions, likes, retweets, replies, link_clicks, engagement_rate
```

---

### 2.5 アフィリエイトリンク（Affiliate Links）

---

#### `GET /affiliate-links` — リンク一覧

**クエリパラメータ**: `tags[]`, `search`, `page`, `per_page`

**レスポンス** `200 OK`
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "name": "おすすめ商品A",
        "destination_url": "https://affiliate.example.com/product/123?ref=myid",
        "short_url": "https://sns-mgr.app/l/abc123",
        "slug": "abc123",
        "tags": ["物販", "美容"],
        "total_clicks": 342,
        "is_active": true,
        "created_at": "2026-01-15T00:00:00Z"
      }
    ],
    "total": 25
  }
}
```

---

#### `POST /affiliate-links` — リンク作成

```json
{
  "name": "おすすめ商品A",
  "destination_url": "https://affiliate.example.com/product/123?ref=myid",
  "tags": ["物販", "美容"],
  "description": "人気の美容商品",
  "expires_at": null
}
```

**レスポンス** `201 Created`（`slug` はサーバー側で自動生成）

---

#### `GET /affiliate-links/{link_id}` — リンク詳細＋クリック統計

```json
{
  "success": true,
  "data": {
    "link": { ... },
    "stats": {
      "total_clicks": 342,
      "clicks_today": 15,
      "clicks_this_week": 87,
      "clicks_this_month": 210,
      "daily_series": [
        { "date": "2026-03-25", "clicks": 28 },
        ...
      ]
    }
  }
}
```

---

#### `PATCH /affiliate-links/{link_id}` — リンク更新

```json
{ "name": "更新名", "tags": ["物販"], "is_active": false }
```

---

#### `DELETE /affiliate-links/{link_id}` — リンク削除

**レスポンス** `204 No Content`

---

#### `GET /l/{slug}` — 短縮 URL リダイレクト（公開エンドポイント）

認証不要。クリックを `link_clicks` に記録後、`destination_url` へ `302 Redirect`。

**ヘッダー**
```
Location: https://affiliate.example.com/product/123?ref=myid
```

---

### 2.6 自動タスク（Tasks）

---

#### `GET /tasks` — タスク一覧

**レスポンス** `200 OK`
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "task_type": "auto_like",
        "search_keyword": "#おすすめ商品",
        "is_enabled": true,
        "cron_expression": "*/30 * * * *",
        "total_success": 1230,
        "total_failed": 5,
        "last_executed_at": "2026-03-31T12:00:00Z",
        "next_execute_at": "2026-03-31T12:30:00Z"
      }
    ]
  }
}
```

---

#### `POST /tasks` — タスク作成

```json
{
  "social_account_id": "uuid",
  "task_type": "auto_like",
  "search_keyword": "#おすすめ商品 -is:retweet lang:ja",
  "is_enabled": false,
  "cron_expression": "0 */2 * * *"
}
```

---

#### `PATCH /tasks/{task_id}` — タスク設定変更（有効/無効含む）

```json
{ "is_enabled": true, "search_keyword": "#新しいキーワード" }
```

---

#### `DELETE /tasks/{task_id}` — タスク削除

---

#### `GET /tasks/{task_id}/logs` — タスク実行ログ

**クエリパラメータ**: `from`, `to`, `action`, `page`, `per_page`

**レスポンス** `200 OK`
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "uuid",
        "executed_at": "2026-03-31T12:00:05Z",
        "target_tweet_id": "1234567890",
        "action": "liked",
        "response_time_ms": 412
      }
    ],
    "total": 500
  }
}
```

---

#### `GET /tasks/logs/export-csv` — タスクログ CSV エクスポート

**クエリパラメータ**: `task_id`, `from`, `to`  
**レスポンス**: `text/csv`

---

### 2.7 分析（Analytics）

---

#### `GET /analytics/dashboard` — ダッシュボード集計

**クエリパラメータ**: `social_account_id`, `period` (7d / 30d / 90d)

**レスポンス** `200 OK`
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_impressions": 125000,
      "total_likes": 3200,
      "total_retweets": 450,
      "total_link_clicks": 780,
      "avg_engagement_rate": 2.84
    },
    "top_posts": [ { "post_id": "uuid", "impressions": 8500, "engagement_rate": 4.2 } ],
    "top_links": [ { "link_id": "uuid", "name": "商品A", "clicks": 342 } ],
    "daily_series": [
      { "date": "2026-03-25", "impressions": 4200, "link_clicks": 28 }
    ]
  }
}
```

---

### 2.8 決済（Payments）

---

#### `GET /payments/plans` — 料金プラン一覧（認証不要）

```json
{
  "success": true,
  "data": [
    { "name": "starter", "display_name": "Starter", "price_jpy": 2980, "features": [...] },
    { "name": "pro", "display_name": "Pro", "price_jpy": 7980, "features": [...] },
    { "name": "business", "display_name": "Business", "price_jpy": 19800, "features": [...] }
  ]
}
```

---

#### `POST /payments/subscribe` — サブスクリプション開始

```json
{ "plan_name": "pro", "payment_method_id": "pm_xxxx" }
```

**レスポンス** `200 OK`
```json
{
  "success": true,
  "data": {
    "subscription_id": "sub_xxxx",
    "status": "active",
    "current_period_end": "2026-04-30T00:00:00Z",
    "client_secret": "pi_xxx_secret_xxx"  // 3Dセキュア必要時のみ
  }
}
```

---

#### `POST /payments/change-plan` — プラン変更

```json
{ "new_plan_name": "business" }
```

---

#### `POST /payments/cancel` — 解約

**レスポンス** `200 OK`
```json
{
  "success": true,
  "data": { "cancel_at": "2026-04-30T00:00:00Z", "message": "期間終了まで利用可能です" }
}
```

---

#### `GET /payments/history` — 決済履歴

**レスポンス** `200 OK`（ページネーション形式）

---

#### `POST /payments/webhook` — Stripe Webhook（公開、署名検証必須）

Stripe からの Event を処理。`Stripe-Signature` ヘッダーで署名検証。

```json
{
  "type": "invoice.payment_succeeded",
  "data": { "object": { "id": "in_xxxx", "customer": "cus_xxxx", ... } }
}
```

処理するイベント:
| Event | 処理内容 |
|-------|----------|
| `customer.subscription.created` | users.plan_expires_at を更新 |
| `invoice.payment_succeeded` | payments テーブルに記録、is_active = true |
| `invoice.payment_failed` | 失敗記録、ユーザーへ通知メール |
| `customer.subscription.deleted` | plan を starter に戻す |

---

### 2.9 システム（System）

---

#### `GET /healthz` — ヘルスチェック（認証不要）

```json
{
  "status": "ok",
  "version": "1.0.0",
  "db": "ok",
  "redis": "ok",
  "timestamp": "2026-03-31T12:00:00Z"
}
```

---

## 3. Twikit 連携フロー

### 3.1 初回認証フロー（アカウント追加時）

```
[ユーザー] POST /social-accounts
     │  { x_username, password }
     ▼
[FastAPI Backend]
     │
     ├─ Twikit Client.login(username, password) ──────────────────► [X サーバー]
     │                                                                     │
     │                                            ◄─── cookies.json ───────┘
     │
     ├─ AES-256-GCM で password を暗号化
     ├─ AES-256-GCM で cookies.json を暗号化
     ├─ social_accounts テーブルに保存
     └─ 201 Created レスポンス
```

### 3.2 予約投稿実行フロー

```
[Celery Beat] ─── 1分ごとにスキャン ──►
                    │
                    ├─ SELECT posts WHERE status='scheduled' AND scheduled_at <= NOW()
                    │
                    ▼
[Celery Worker - post_task]
     │
     ├─ posts.status = 'posting' に更新（楽観的ロック: SELECT FOR UPDATE）
     │
     ├─ social_accounts から encrypted_cookies 取得 → 復号
     │
     ├─ Twikit Client（cookies で認証）
     │
     ├─ スレッド投稿の場合はループで tweet() を順次実行
     │   └─ 各ツイート間に random.gauss(3, 0.5) 秒の遅延
     │
     ├─ 成功: posts.status = 'posted', x_tweet_id を保存
     │         post_analytics の初期レコードを生成
     │
     └─ 失敗: retry_count + 1
              retry_count < 3 → countdown=2^retry_count * 60 秒後に再スケジュール
              retry_count >= 3 → status = 'failed', last_error を保存、メール通知
```

### 3.3 自動いいねフロー

```
[Celery Beat] ─── Cron 式に基づいてトリガー ──►
                    │
                    ▼
[Celery Worker - auto_like_task]
     │
     ├─ social_accounts から BAN 対策パラメータを取得
     │
     ├─ 日次上限チェック: daily_likes_count >= daily_like_limit → SKIP
     │
     ├─ 稼働時間チェック: 現在時刻が [active_hours_start, active_hours_end] 外 → SKIP
     │
     ├─ Twikit Client.search_tweet(keyword, product='Latest') で検索
     │
     ├─ バースト処理（burst_size 件ずつ）:
     │   └─ for each tweet:
     │       ├─ tweet.favorite()  ──────────────────► [X サーバー]
     │       ├─ task_logs に記録
     │       ├─ daily_likes_count + 1
     │       ├─ RateLimitError → 15分待機後リトライ
     │       └─ sleep(gauss(min_interval, (max_interval-min_interval)/6))
     │
     └─ burst_size 件完了 → sleep(burst_rest_sec) → 次バースト or 終了
```

### 3.4 セッション管理フロー

```
[Celery Worker]
     │
     ├─ social_accounts.session_expires_at を確認
     │   └─ 有効期限 < NOW() + 1h の場合 → 再ログイン
     │       ├─ encrypted_password を復号
     │       ├─ Twikit Client.login(username, password)
     │       ├─ 新しい cookies.json を取得・暗号化・保存
     │       └─ session_expires_at を更新（+7日）
     │
     └─ セッション有効 → encrypted_cookies を復号して Twikit Client 初期化
```

---

## 4. レートリミット設計

### 4.1 アプリ内 API レートリミット（slowapi）

| エンドポイント | 制限 |
|--------------|------|
| `POST /auth/login` | 10 req / min / IP |
| `POST /auth/register` | 5 req / min / IP |
| `POST /posts/import-csv` | 3 req / min / User |
| その他認証済みエンドポイント | 120 req / min / User |

### 4.2 Twikit 操作レートリミット（推定・保守的設定）

| 操作 | 推奨上限 | 実装上限 |
|------|--------|--------|
| ツイート投稿 | 300/3h | 50/h |
| いいね | 1000/24h | 200/24h |
| フォロー | 400/24h | 100/24h |
| 検索 | 180/15min | 30/15min |

---

## 5. メディアアップロードフロー

```
[フロントエンド]
     │
     ├─ POST /media/upload-url でプリサインド URL 取得
     │   ┌─────────────────────────────────┐
     │   │ { "file_name": "image.jpg",      │
     │   │   "content_type": "image/jpeg" } │
     │   └─────────────────────────────────┘
     │
     ◄── { "upload_url": "https://s3.../presigned", "file_url": "https://cdn.../uuid.jpg" }
     │
     ├─ PUT {upload_url} に画像データを直接アップロード（S3）
     │
     └─ POST /posts 時に media_urls に file_url を含める
```

---

## 6. 環境変数定義

```env
# Application
SECRET_KEY=<RS256秘密鍵>
ALLOWED_ORIGINS=https://app.sns-mgr.app

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/sns_manager

# Redis
REDIS_URL=redis://redis:6379/0

# Encryption
AES_ENCRYPTION_KEY=<32バイトBase64>
AES_KEY_ID=v1

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# AWS
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=sns-manager-media
AWS_REGION=ap-northeast-1

# Email
SENDGRID_API_KEY=SG....
FROM_EMAIL=noreply@sns-mgr.app
```
