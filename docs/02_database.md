# DB 定義書

**プロジェクト名**: X（Twitter）アフィリエイト特化型 SNS 管理ツール  
**バージョン**: 1.0.0  
**作成日**: 2026-03-31  
**RDBMS**: PostgreSQL 16  
**文字コード**: UTF-8  

---

## 1. ER 図（概念）

```
plans ──< users ──< social_accounts ──< tasks
                 ├──< posts ──< post_analytics
                 ├──< affiliate_links ──< link_clicks
                 └──< payments
```

---

## 2. テーブル一覧

| テーブル名 | 説明 |
|------------|------|
| `plans` | 料金プランマスタ |
| `users` | 会員情報・プラン・有効期限 |
| `social_accounts` | X アカウント情報（Twikit 認証情報） |
| `posts` | 投稿内容・予約日時・ステータス |
| `post_analytics` | 投稿のパフォーマンス指標 |
| `affiliate_links` | アフィリエイトリンク管理 |
| `link_clicks` | リンククリックログ |
| `tasks` | 自動いいね/フォローの設定・実行ログ |
| `task_logs` | タスク実行の詳細ログ |
| `payments` | 決済履歴 |

---

## 3. テーブル詳細定義

### 3.1 plans（料金プランマスタ）

```sql
CREATE TABLE plans (
    id              SERIAL          PRIMARY KEY,
    name            VARCHAR(50)     NOT NULL UNIQUE,          -- 'starter', 'pro', 'business'
    display_name    VARCHAR(100)    NOT NULL,                  -- 表示名
    price_jpy       INTEGER         NOT NULL,                  -- 月額（円）
    max_accounts    INTEGER         NOT NULL DEFAULT 1,        -- 管理可能 X アカウント数
    max_posts_month INTEGER,                                   -- 月間最大投稿数（NULL=無制限）
    can_automate    BOOLEAN         NOT NULL DEFAULT FALSE,    -- 自動化機能の利用可否
    stripe_price_id VARCHAR(100),                             -- Stripe Price ID
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
```

| カラム | 型 | 制約 | 説明 |
|--------|----|------|------|
| id | SERIAL | PK | プラン ID |
| name | VARCHAR(50) | UNIQUE, NOT NULL | プランコード |
| display_name | VARCHAR(100) | NOT NULL | UI 表示名 |
| price_jpy | INTEGER | NOT NULL | 月額（円） |
| max_accounts | INTEGER | NOT NULL, DEFAULT 1 | 最大 X アカウント数 |
| max_posts_month | INTEGER | NULL 可 | NULL = 無制限 |
| can_automate | BOOLEAN | NOT NULL | 自動化機能フラグ |
| stripe_price_id | VARCHAR(100) | NULL 可 | Stripe Price ID |
| created_at | TIMESTAMPTZ | NOT NULL | 作成日時 |
| updated_at | TIMESTAMPTZ | NOT NULL | 更新日時 |

---

### 3.2 users（会員情報）

```sql
CREATE TABLE users (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    email               VARCHAR(255)    NOT NULL UNIQUE,
    password_hash       VARCHAR(255)    NOT NULL,              -- bcrypt (cost=12)
    display_name        VARCHAR(100),
    plan_id             INTEGER         NOT NULL REFERENCES plans(id),
    plan_started_at     TIMESTAMPTZ,                           -- 現プランの開始日時
    plan_expires_at     TIMESTAMPTZ,                           -- プラン有効期限（NULL=無期限/解約済）
    trial_ends_at       TIMESTAMPTZ,                           -- 無料トライアル終了日時
    stripe_customer_id  VARCHAR(100)    UNIQUE,                -- Stripe Customer ID
    stripe_sub_id       VARCHAR(100)    UNIQUE,                -- Stripe Subscription ID
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    is_admin            BOOLEAN         NOT NULL DEFAULT FALSE,
    totp_secret         VARCHAR(100),                          -- 2FA シークレット（NULL=未設定）
    timezone            VARCHAR(50)     NOT NULL DEFAULT 'Asia/Tokyo',
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ                            -- 論理削除
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_stripe_customer_id ON users(stripe_customer_id);
```

| カラム | 型 | 制約 | 説明 |
|--------|----|------|------|
| id | UUID | PK | ユーザー ID（UUID v4） |
| email | VARCHAR(255) | UNIQUE, NOT NULL | メールアドレス |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt ハッシュ |
| display_name | VARCHAR(100) | NULL 可 | 表示名 |
| plan_id | INTEGER | FK → plans.id | 契約プラン |
| plan_started_at | TIMESTAMPTZ | NULL 可 | プラン開始日時 |
| plan_expires_at | TIMESTAMPTZ | NULL 可 | プラン有効期限 |
| trial_ends_at | TIMESTAMPTZ | NULL 可 | トライアル終了日時 |
| stripe_customer_id | VARCHAR(100) | UNIQUE | Stripe 顧客 ID |
| stripe_sub_id | VARCHAR(100) | UNIQUE | Stripe サブスク ID |
| is_active | BOOLEAN | NOT NULL | アカウント有効フラグ |
| is_admin | BOOLEAN | NOT NULL | 管理者フラグ |
| totp_secret | VARCHAR(100) | NULL 可 | TOTP シークレット（暗号化） |
| timezone | VARCHAR(50) | NOT NULL | タイムゾーン |
| created_at | TIMESTAMPTZ | NOT NULL | 作成日時 |
| updated_at | TIMESTAMPTZ | NOT NULL | 更新日時 |
| deleted_at | TIMESTAMPTZ | NULL 可 | 論理削除日時 |

---

### 3.3 social_accounts（X アカウント情報）

```sql
CREATE TABLE social_accounts (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform                VARCHAR(20)     NOT NULL DEFAULT 'x',   -- 将来の拡張用
    x_username              VARCHAR(50)     NOT NULL,               -- @ なし
    x_display_name          VARCHAR(100),
    -- Twikit 認証情報（AES-256-GCM 暗号化、Base64 エンコード保存）
    encrypted_password      TEXT            NOT NULL,               -- X パスワード（暗号化）
    encrypted_cookies       TEXT,                                   -- Twikit cookies.json（暗号化）
    encryption_key_id       VARCHAR(50)     NOT NULL,               -- 暗号化キーバージョン
    -- BAN 対策パラメータ
    daily_like_limit        INTEGER         NOT NULL DEFAULT 200,   -- 1日いいね上限
    daily_follow_limit      INTEGER         NOT NULL DEFAULT 100,   -- 1日フォロー上限
    action_min_interval_sec INTEGER         NOT NULL DEFAULT 30,    -- アクション最小間隔（秒）
    action_max_interval_sec INTEGER         NOT NULL DEFAULT 90,    -- アクション最大間隔（秒）
    active_hours_start      SMALLINT        NOT NULL DEFAULT 7,     -- 稼働開始時刻（JST 時）
    active_hours_end        SMALLINT        NOT NULL DEFAULT 23,    -- 稼働終了時刻（JST 時）
    burst_size              INTEGER         NOT NULL DEFAULT 10,    -- バースト実行数
    burst_rest_sec          INTEGER         NOT NULL DEFAULT 300,   -- バースト後休止（秒）
    -- ステータス
    is_active               BOOLEAN         NOT NULL DEFAULT TRUE,
    last_login_at           TIMESTAMPTZ,                            -- 最終 Twikit ログイン日時
    session_expires_at      TIMESTAMPTZ,                            -- セッション有効期限
    daily_likes_count       INTEGER         NOT NULL DEFAULT 0,     -- 本日のいいね数
    daily_follows_count     INTEGER         NOT NULL DEFAULT 0,     -- 本日のフォロー数
    daily_reset_at          TIMESTAMPTZ,                            -- 日次カウントリセット日時
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, x_username)
);

CREATE INDEX idx_social_accounts_user_id ON social_accounts(user_id);
```

| カラム | 型 | 制約 | 説明 |
|--------|----|------|------|
| id | UUID | PK | アカウント ID |
| user_id | UUID | FK → users.id | 所有ユーザー |
| platform | VARCHAR(20) | NOT NULL | SNS プラットフォーム |
| x_username | VARCHAR(50) | NOT NULL | X ユーザー名 |
| encrypted_password | TEXT | NOT NULL | AES-256-GCM 暗号化パスワード |
| encrypted_cookies | TEXT | NULL 可 | AES-256-GCM 暗号化 cookies.json |
| encryption_key_id | VARCHAR(50) | NOT NULL | 暗号化キーバージョン識別子 |
| daily_like_limit | INTEGER | NOT NULL | 1 日いいね上限（デフォルト 200） |
| daily_follow_limit | INTEGER | NOT NULL | 1 日フォロー上限（デフォルト 100） |
| action_min_interval_sec | INTEGER | NOT NULL | アクション最小間隔（秒） |
| action_max_interval_sec | INTEGER | NOT NULL | アクション最大間隔（秒） |
| active_hours_start | SMALLINT | NOT NULL | 稼働開始時刻（0-23） |
| active_hours_end | SMALLINT | NOT NULL | 稼働終了時刻（0-23） |
| burst_size | INTEGER | NOT NULL | バースト実行数 |
| burst_rest_sec | INTEGER | NOT NULL | バースト後休止秒数 |
| is_active | BOOLEAN | NOT NULL | アカウント有効フラグ |
| last_login_at | TIMESTAMPTZ | NULL 可 | 最終 Twikit ログイン |
| session_expires_at | TIMESTAMPTZ | NULL 可 | セッション有効期限 |
| daily_likes_count | INTEGER | NOT NULL | 本日のいいね累計 |
| daily_follows_count | INTEGER | NOT NULL | 本日のフォロー累計 |
| daily_reset_at | TIMESTAMPTZ | NULL 可 | 日次カウントリセット日時 |

---

### 3.4 posts（投稿管理）

```sql
CREATE TABLE posts (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    social_account_id   UUID            NOT NULL REFERENCES social_accounts(id),
    parent_post_id      UUID            REFERENCES posts(id),      -- スレッド親投稿
    thread_order        SMALLINT        NOT NULL DEFAULT 1,         -- スレッド内順序
    content             TEXT            NOT NULL,                   -- 投稿テキスト（最大 280 文字）
    media_urls          TEXT[],                                     -- S3 URL 配列（最大 4）
    scheduled_at        TIMESTAMPTZ,                               -- 予約投稿日時（NULL=即時）
    posted_at           TIMESTAMPTZ,                               -- 実際の投稿日時
    status              VARCHAR(20)     NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft','scheduled','posting','posted','failed','cancelled')),
    x_tweet_id          VARCHAR(50),                               -- X 上のツイート ID
    retry_count         SMALLINT        NOT NULL DEFAULT 0,
    last_error          TEXT,                                      -- 最終エラーメッセージ
    is_template         BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_status_scheduled_at ON posts(status, scheduled_at)
    WHERE status = 'scheduled';
CREATE INDEX idx_posts_social_account_id ON posts(social_account_id);
```

| カラム | 型 | 制約 | 説明 |
|--------|----|------|------|
| id | UUID | PK | 投稿 ID |
| user_id | UUID | FK → users.id | 投稿者 |
| social_account_id | UUID | FK → social_accounts.id | 投稿する X アカウント |
| parent_post_id | UUID | FK → posts.id, NULL 可 | スレッド親 ID |
| thread_order | SMALLINT | NOT NULL | スレッド内順序（1 始まり） |
| content | TEXT | NOT NULL | 投稿テキスト |
| media_urls | TEXT[] | NULL 可 | S3 オブジェクト URL 配列 |
| scheduled_at | TIMESTAMPTZ | NULL 可 | 予約日時（NULL=下書き） |
| posted_at | TIMESTAMPTZ | NULL 可 | 投稿完了日時 |
| status | VARCHAR(20) | CHECK | draft/scheduled/posting/posted/failed/cancelled |
| x_tweet_id | VARCHAR(50) | NULL 可 | X 上のツイート ID |
| retry_count | SMALLINT | NOT NULL | リトライ回数 |
| last_error | TEXT | NULL 可 | 最終エラー内容 |
| is_template | BOOLEAN | NOT NULL | テンプレートフラグ |

---

### 3.5 post_analytics（投稿分析）

```sql
CREATE TABLE post_analytics (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id         UUID            NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    fetched_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),      -- データ取得日時
    impressions     INTEGER         NOT NULL DEFAULT 0,
    likes           INTEGER         NOT NULL DEFAULT 0,
    retweets        INTEGER         NOT NULL DEFAULT 0,
    replies         INTEGER         NOT NULL DEFAULT 0,
    quotes          INTEGER         NOT NULL DEFAULT 0,
    bookmarks       INTEGER         NOT NULL DEFAULT 0,
    link_clicks     INTEGER         NOT NULL DEFAULT 0,          -- リンクのクリック数（X 計測）
    engagement_rate NUMERIC(5,2),                               -- (likes+RT+replies)/impressions * 100
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_post_analytics_post_id ON post_analytics(post_id);
CREATE INDEX idx_post_analytics_fetched_at ON post_analytics(fetched_at);
```

---

### 3.6 affiliate_links（アフィリエイトリンク）

```sql
CREATE TABLE affiliate_links (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(200)    NOT NULL,                   -- リンク名
    destination_url TEXT            NOT NULL,                   -- 転送先 URL
    slug            VARCHAR(20)     NOT NULL UNIQUE,            -- 短縮 URL スラッグ
    tags            TEXT[]          NOT NULL DEFAULT '{}',      -- タグ配列
    description     TEXT,
    total_clicks    INTEGER         NOT NULL DEFAULT 0,         -- 累計クリック数
    expires_at      TIMESTAMPTZ,                               -- 有効期限（NULL=無期限）
    redirect_on_expire TEXT,                                   -- 期限切れ時のリダイレクト先
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_affiliate_links_user_id ON affiliate_links(user_id);
CREATE INDEX idx_affiliate_links_slug ON affiliate_links(slug);
CREATE INDEX idx_affiliate_links_tags ON affiliate_links USING GIN(tags);
```

| カラム | 型 | 制約 | 説明 |
|--------|----|------|------|
| id | UUID | PK | リンク ID |
| user_id | UUID | FK → users.id | 所有ユーザー |
| name | VARCHAR(200) | NOT NULL | リンク名称 |
| destination_url | TEXT | NOT NULL | 転送先 URL |
| slug | VARCHAR(20) | UNIQUE, NOT NULL | 短縮 URL のスラッグ部分 |
| tags | TEXT[] | NOT NULL | タグ配列（GIN インデックス） |
| total_clicks | INTEGER | NOT NULL | 累計クリック数（非正規化） |
| expires_at | TIMESTAMPTZ | NULL 可 | 有効期限 |
| is_active | BOOLEAN | NOT NULL | 有効フラグ |

---

### 3.7 link_clicks（クリックログ）

```sql
CREATE TABLE link_clicks (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    affiliate_link_id   UUID            NOT NULL REFERENCES affiliate_links(id) ON DELETE CASCADE,
    post_id             UUID            REFERENCES posts(id) ON DELETE SET NULL,    -- クリック元投稿
    clicked_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    ip_hash             VARCHAR(64),                            -- SHA-256 ハッシュ（個人情報保護）
    user_agent_hash     VARCHAR(64),                            -- UA ハッシュ（重複判定用）
    referer             TEXT,
    country_code        CHAR(2)                                 -- GeoIP（任意）
);

CREATE INDEX idx_link_clicks_affiliate_link_id ON link_clicks(affiliate_link_id);
CREATE INDEX idx_link_clicks_clicked_at ON link_clicks(clicked_at);
CREATE INDEX idx_link_clicks_post_id ON link_clicks(post_id);
```

---

### 3.8 tasks（自動タスク設定）

```sql
CREATE TABLE tasks (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    social_account_id   UUID            NOT NULL REFERENCES social_accounts(id),
    task_type           VARCHAR(30)     NOT NULL
                        CHECK (task_type IN ('auto_like', 'auto_follow', 'auto_unfollow')),
    -- 実行条件
    search_keyword      VARCHAR(500),                           -- 検索キーワード（auto_like 用）
    target_username     VARCHAR(50),                            -- 対象ユーザー名（auto_follow 用）
    -- スケジュール
    is_enabled          BOOLEAN         NOT NULL DEFAULT FALSE,
    cron_expression     VARCHAR(100)    NOT NULL DEFAULT '*/30 * * * *',  -- Cron 式
    -- 統計
    total_executed      INTEGER         NOT NULL DEFAULT 0,
    total_success       INTEGER         NOT NULL DEFAULT 0,
    total_failed        INTEGER         NOT NULL DEFAULT 0,
    last_executed_at    TIMESTAMPTZ,
    next_execute_at     TIMESTAMPTZ,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_social_account_id ON tasks(social_account_id);
CREATE INDEX idx_tasks_enabled_next ON tasks(is_enabled, next_execute_at)
    WHERE is_enabled = TRUE;
```

| カラム | 型 | 制約 | 説明 |
|--------|----|------|------|
| id | UUID | PK | タスク ID |
| user_id | UUID | FK → users.id | 所有ユーザー |
| social_account_id | UUID | FK → social_accounts.id | 実行 X アカウント |
| task_type | VARCHAR(30) | CHECK | auto_like / auto_follow / auto_unfollow |
| search_keyword | VARCHAR(500) | NULL 可 | いいね対象の検索クエリ |
| target_username | VARCHAR(50) | NULL 可 | フォロー対象ユーザー名 |
| is_enabled | BOOLEAN | NOT NULL | 有効/無効フラグ |
| cron_expression | VARCHAR(100) | NOT NULL | Cron 実行スケジュール |
| total_executed | INTEGER | NOT NULL | 累計実行回数 |
| last_executed_at | TIMESTAMPTZ | NULL 可 | 最終実行日時 |

---

### 3.9 task_logs（タスク実行ログ）

```sql
CREATE TABLE task_logs (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID            NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    executed_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    target_x_user_id    VARCHAR(50),                           -- 対象 X ユーザー ID
    target_tweet_id     VARCHAR(50),                           -- 対象ツイート ID
    action          VARCHAR(30)     NOT NULL,                  -- 'liked', 'followed', 'skipped', 'error'
    error_message   TEXT,
    response_time_ms INTEGER                                   -- Twikit レスポンスタイム
);

CREATE INDEX idx_task_logs_task_id ON task_logs(task_id);
CREATE INDEX idx_task_logs_executed_at ON task_logs(executed_at);
-- 古いログのパーティション（将来対応）
-- PARTITION BY RANGE (executed_at)
```

---

### 3.10 payments（決済履歴）

```sql
CREATE TABLE payments (
    id                      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID            NOT NULL REFERENCES users(id),
    plan_id                 INTEGER         NOT NULL REFERENCES plans(id),
    stripe_payment_intent_id VARCHAR(100)   UNIQUE,
    stripe_invoice_id       VARCHAR(100)    UNIQUE,
    amount_jpy              INTEGER         NOT NULL,
    currency                CHAR(3)         NOT NULL DEFAULT 'JPY',
    status                  VARCHAR(20)     NOT NULL
                            CHECK (status IN ('pending','succeeded','failed','refunded')),
    paid_at                 TIMESTAMPTZ,
    period_start            TIMESTAMPTZ,
    period_end              TIMESTAMPTZ,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_payments_stripe_invoice_id ON payments(stripe_invoice_id);
```

---

## 4. インデックス設計方針

| 方針 | 詳細 |
|------|------|
| 主キー | UUID（`gen_random_uuid()`）を採用。分散環境に対応 |
| 外部キーインデックス | 全 FK カラムにインデックスを付与 |
| 複合インデックス | 頻出 WHERE 句の複合条件（例：`status + scheduled_at`）に適用 |
| 部分インデックス | `WHERE is_enabled = TRUE` 等、絞り込み条件が固定の場合に使用 |
| GIN インデックス | PostgreSQL 配列型（`TEXT[]`）の検索に使用（tags カラム） |

---

## 5. 暗号化設計

```
暗号化対象カラム:
  - social_accounts.encrypted_password
  - social_accounts.encrypted_cookies
  - users.totp_secret

アルゴリズム: AES-256-GCM
キー管理: AWS KMS または環境変数で管理（DB 外で保持）
形式: base64url(nonce || ciphertext || tag)
キーバージョニング: encryption_key_id カラムで追跡（キーローテーション対応）
```

---

## 6. マイグレーション方針

- ツール: **Alembic**（SQLAlchemy 連携）
- ファイル配置: `alembic/versions/`
- 命名規則: `YYYYMMDDHHMMSS_description.py`
- 破壊的変更: 本番では必ずバックアップ後に実行

---

## 7. 初期データ（seeds）

```sql
-- plans テーブルの初期データ
INSERT INTO plans (name, display_name, price_jpy, max_accounts, max_posts_month, can_automate) VALUES
  ('starter',  'Starter',  2980,  1,    100,  FALSE),
  ('pro',      'Pro',      7980,  5,    1000, TRUE),
  ('business', 'Business', 19800, 20,   NULL, TRUE);
```
