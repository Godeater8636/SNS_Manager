# SNS_Manager — Google Earth 不動産・リスク情報 自動マッピングシステム

A3設計図 (`Google Earth 不動産・リスク情報 自動マッピングシステム`) の
③ 自動処理プログラムを Python で実装したもの。

宅地建物の取引評価・施設管理における災害リスク把握を3Dで行うため、
国土交通省・自治体公開データから KML/KMZ を生成し、Google Earth Pro に
ネットワークリンク経由で常時最新を反映させる。**手動更新ゼロ** がゴール。

---

## データパイプライン

```
[① MLIT 地価公示データ ]  --+
                            |--> ③ 自動処理 (本リポジトリ) --> ④ output/*.kml --> ⑤ Google Earth Pro
[② ハザードマップデータ]  --+              (Python)                                   (NetworkLink)
```

- **① 地価公示** (`src/fetchers/chika_fetcher.py`): 不動産情報ライブラリ API (XIT001) を叩いて緯度経度付きポイント取得
- **② ハザードマップ** (`src/fetchers/hazard_fetcher.py`): 国土数値情報の GeoJSON (洪水浸水想定区域、土砂災害警戒区域など)
- **③ 変換** (`src/converters/kml_builder.py`): KML 2.2 (Google Earth Pro 互換) で出力。住所/価格/想定浸水深などを吹き出しに表示
- **④ 出力**: `output/chika_latest.kml` / `output/hazard_latest.kml` を **常に上書き保存** (Google Earth Pro が同名を参照)
- **⑤ Google Earth Pro**: `scripts/network_link_template.kml` を一度開けば以後自動更新

---

## セットアップ

```bash
# 依存ライブラリ
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 設定確認 (取得対象都道府県、ハザードレイヤーURL、出力先など)
$EDITOR config/config.yaml

# 必要に応じて環境変数 (API キー、SMTP)
export REINFOLIB_API_KEY=...
```

### 手動実行

```bash
python -m src.main --config config/config.yaml
```

正常終了で `exit 0`、失敗 1件以上で `exit 1` を返す。
ログは `logs/sns_manager.log` (日次ローテーション、保持30日)。

### 定期実行 (③ 数ヶ月ごとの特定日に自動起動)

**Windows (タスクスケジューラ):**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows_task.ps1
```

**Mac / Linux (cron):**

```bash
bash scripts/setup_mac_cron.sh
# 既定: 1,4,7,10 月の毎月1日 03:00 (四半期)
# 変更: CRON_SCHEDULE="0 3 1 * *" bash scripts/setup_mac_cron.sh
```

### Google Earth Pro 側 (⑤ 一度だけ手動設定)

1. `scripts/network_link_template.kml` を編集し、`<href>` を出力フォルダの
   絶対パスに書き換える (例: `file:///C:/SNS_Manager/output/chika_latest.kml`)
2. ダブルクリックで Google Earth Pro が開く
3. 「お気に入り」にドラッグして保存 → 以後 Google Earth Pro 起動時に
   自動で最新版を読み込む

---

## ディレクトリ構成

```
SNS_Manager/
├── config/
│   └── config.yaml          # ★ サイト仕様変更時はここを更新
├── src/
│   ├── main.py              # エントリポイント
│   ├── pipeline.py          # ③ 全体オーケストレーション
│   ├── fetchers/
│   │   ├── chika_fetcher.py # ① 地価
│   │   └── hazard_fetcher.py # ② ハザード
│   ├── converters/
│   │   └── kml_builder.py   # KML/KMZ 生成
│   ├── notifier.py          # エラー通知 (メール)
│   └── utils/               # logger / http / config / geo
├── scripts/
│   ├── setup_windows_task.ps1   # タスクスケジューラ登録
│   ├── setup_mac_cron.sh        # cron 登録
│   └── network_link_template.kml # ⑤ Google Earth Pro 用
├── output/                  # ④ chika_latest.kml / hazard_latest.kml
├── logs/                    # 日次ローテーション
└── tests/                   # pytest
```

---

## メンテナンス (タスクリスト 4. サイト仕様変更対応)

| シナリオ | 対応箇所 |
|---|---|
| MLIT API の URL / クエリ変更 | `config/config.yaml > chika.endpoint` を更新 |
| MLIT API の応答 JSON 構造変更 | `src/fetchers/chika_fetcher.py::_parse_response` を更新 |
| ハザードレイヤー追加・URL変更 | `config/config.yaml > hazard.layers` に追記 |
| 新フォーマット (Shape など) 対応 | `src/fetchers/hazard_fetcher.py::_fetch_layer` に分岐追加 |
| エラー通知先変更 | `config/config.yaml > notify`、SMTP系は環境変数 |

エラーは `logs/sns_manager.log` に集約。`notify.enabled: true` で SMTP メール送信。

---

## テスト

```bash
pytest tests/ -v
```

全ユニットテストはネットワークアクセスなしで実行可能。

---

## ライセンス / 注意

- 国土交通省・国土数値情報・自治体オープンデータの **利用規約遵守は利用者責任**
- 不動産情報ライブラリ API はキー必須 (`REINFOLIB_API_KEY` 環境変数)
- 一般公開時の再配布可否は各データソースのライセンスを確認すること
