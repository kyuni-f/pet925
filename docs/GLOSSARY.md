# pet925 語録集

このファイルは、開発中によく出る言葉の辞書です。

- **前半**: このサイト固有の言葉（ファイル名、データの列、コマンド）
- **後半**: プログラミング一般の言葉（言語、関数、型、エラーなど）

手順の詳細は `docs/MANUAL.md`、なぜそう作ったかは `docs/PROJECT_SUMMARY.md` を見てください。

---

# 前半：このプロジェクトの言葉

このサイトは、ペットフードを条件で探せる静的サイトです。人間が CSV を編集し、Python が検品して JSON にし、ブラウザが Web Worker で検索します。

## 毎日出てくる言葉

| 用語 | このプロジェクトでの意味 |
|---|---|
| **ビルド** | `npm run build`（中身は `python3 csv_to_json.py`）。CSV を検品して、サイトが読む JSON / `data_master.js` を作る作業。 |
| **デプロイ** | `npm run deploy`。ビルド → Git にコミット → GitHub へ push → GitHub Pages で公開、まで一気にやる。 |
| **バリデーション** | ビルド時の検品。未登録タグ、列不足、商品名重複などがあると公開を止める。 |
| **キャッシュ** | ブラウザが古いファイルを覚えてしまうこと。直したのに画面が変わらないときは **Ctrl + F5**。 |
| **キャッシュバスティング** | `style.css?v=日付` のように URL にバージョンを付けて、古いキャッシュを使わせない仕組み。`siteVersion` がそれ。 |
| **マスターデータ** | 人間が編集する原本。`pet925_master.ods` と、そこから出した `data/*.csv`。 |
| **配信データ** | サイトが実際に読むファイル。`product_data.json`、`product_data_0.json`、`data_master.js`。手で直さない（ビルドが上書きする）。**Git には含める。** GitHub Pages がリポジトリをそのまま配信するため。 |
| **生成物** | プログラムが作るファイル。手編集しない。このサイトでは配信データがそれ。一般論では Git に入れないことも多いが、**今の公開方法では入れる。** |
| **パイプライン** | 「集める → 検品する → JSONにする → 公開する」という流れ全体。 |

よく使うコマンド:

```bash
npm start              # CSVの変更を監視して自動ビルド
npm run build          # 1回だけビルド
npm test               # テスト実行
npm run collect:all    # JANコードから商品データを自動収集してビルドまで
npm run desc:helper    # 既存商品の説明文だけを作り直す（ブラウザで商品名を貼る）
npm run deploy         # 検品・ビルド・公開
```

## ファイルと役割

| ファイル | 一言でいうと |
|---|---|
| `index.html` | サイトの骨格。検索画面・結果画面・モーダルの HTML。 |
| `style.css` | 見た目。 |
| `main.js` | 画面の頭脳。ボタン、お気に入り、描画、GA4。 |
| `search_worker.js` | 裏方の検索エンジン。件数多くても画面を固まらせない。 |
| `common.js` | `normalize()` だけ。`main.js` と Worker の両方から読む共通処理。 |
| `comment_logic.js` | 「店員コメント」をどれにするか決めるロジック。 |
| `data_master.js` | タグ・カテゴリ・ブランド・店員コメントの設定と、問い合わせ用の `FORMSPREE_FORM_ID`。**ビルドが生成する。手編集しない。** |
| `csv_to_json.py` | ビルド本体。CSV → JSON、検品。画像は取らない。 |
| `auto_collect_all.py` | JANコードから商品名・画像・説明を API で集める。 |
| `desc_helper.py` | 既存商品の説明文だけを Gemini で作り直すローカルサーバー。CSV は書かない。 |
| `desc_helper.html` | その画面。`csv_helper.html` の見た目を流用した説明専用フォーム。 |
| `docs/AI_INSTRUCTIONS.md` | Gemini 用の品質ルール。16列 CSV 用と、§9 の説明専用ルールがある。 |
| `pet_utils.py` | Python 側の共通道具（正規化、`.env` 読み込み）。`common.js` の Python 版。 |
| `jan_list.csv` | 「今回集めたい JAN」の入力リスト。実行後は空にならない。既存 JAN の再実行は名前・画像・説明などを上書きする。 |
| `.env` | APIキーなど秘密情報。Git に上げない。 |
| `package.json` | プロジェクトの身分証明書。`npm run ○○` の定義もここ。Git に含める。 |
| `package-lock.json` | 入れたライブラリの版を固定する名簿。手編集しない。Git に含める。 |
| `product_data.json` | 商品データの目次（件数・チャンク数・版）。Worker が最初に読む。ビルドが生成する。 |
| `product_data_*.json` | 商品データの分割ファイル。ビルドが生成する。`.gitignore` に入れない。 |
| `jsconfig.json` | エディタが JS の型を検査するための設定。サイト本体には含まれない。 |

データの流れ:

```
pet925_master.ods / CSV
        ↓  npm run build
product_data.json + data_master.js
        ↓  ブラウザが読む
検索画面（index.html + main.js + search_worker.js）
```

## データの言葉

| 用語 | 意味 |
|---|---|
| **CSV** | 表計算ソフトで開けるテキスト。1行が1商品。編集用。 |
| **JSON** | プログラムが読みやすい形。配信用。 |
| **ODS** | LibreOffice の表。`pet925_master.ods` が原本。 |
| **16列** | 商品1行の必須列。`name, brand, tags, desc, size, jan, img, amz, rak, yah, a8, label, promo, amz_p, rak_p, yah_p` |
| **`#`** | 「空・不明」の印。URL が無いときなどに入れる。 |
| **JANコード** | バーコードの数字。商品の一意な ID。お気に入りのキーにも使う。 |
| **チャンク** | 巨大 JSON を `product_data_0.json` のように分割した塊。1ファイル最大 5000件。 |
| **名寄せ** | 「nutro」でも「ニュートロ」でも検索できるようにする。画面の表示名は `products.csv` の `brand` 列そのもの。 |
| **エイリアス** | 別名。「グレインフリー」と書いたら `gf` タグを付ける、など。`rules.csv`。 |
| **exclude_tags** | 自動タグ付けしてほしくないタグを、その商品だけ止める列。 |
| **フォールバック** | 本命が失敗したときの予備。画像は 楽天v2 → 楽天Item → Yahoo の順。 |
| **説明の取り直し** | `collect:all` の `desc` がいまいちなとき、`npm run desc:helper` で説明だけ作り、CSV に手で貼る作業。再収集は名前や画像も上書きするので使わない。 |

タグのグループ（`tags.csv`）:

- **animal** … 犬 / 猫（1つだけ選べる）
- **age** … 子犬、成犬、シニアなど（1つだけ）
- **cond** … 涙やけ、穀物不使用など（複数選べる）

CSV の列の意味:

- `name` 商品名 / `brand` ブランド / `tags` 絞り込み用英単語 / `desc` 説明文
- `img` 画像URL / `amz` `rak` `yah` 各モールへのリンク
- `amz_p` `rak_p` `yah_p` 価格（今は画面に出していないがデータとして残している）

## 画面・フロントエンド

| 用語 | このサイトでの意味 |
|---|---|
| **静的サイト** | サーバー側にデータベースがない。ファイルを置くだけ。公開先は **GitHub Pages**。 |
| **Vanilla JS** | React などを使わず、素の JavaScript。`main.js` がそれ。 |
| **DOM** | HTML の部品ひとつひとつ。`render()` が商品カードを DOM として作る。 |
| **View** | 画面の種類。`#view-search`（条件）と `#view-results`（一覧）。 |
| **ステート** | 今の状態。結果画面では `body` に `state-results` が付く。 |
| **フィルター** | 犬・シニア・涙やけなどの絞り込み。状態は `activeFilters`。 |
| **チップ** | 結果画面上部に出る「今選んでいる条件」の小さなラベル。 |
| **モーダル** | 画面の上に被さる確認窓。お気に入り解除・画像拡大・利用規約（中に問い合わせフォーム）。 |
| **問い合わせフォーム** | 利用規約モーダル内の入力欄。掲載停止依頼などを Formspree 経由で送る。運営者のメールアドレスは画面に出ない。 |
| **デバウンス** | 入力のたびに検索せず、打ち終わって約 0.8秒待ってから動く。 |
| **ページネーション / Incremental Loading** | 最初は 20件だけ出し、「さらに表示」で足す。全部一気に描画しない。 |
| **CLS** | 操作した瞬間にボタンがガタつく現象。幅を固定して防いでいる。 |
| **lazy loading** | 画面外の画像は後から読む。`loading="lazy"`。 |
| **プレースホルダー** | 画像が無いときの「No Image」。外部サイトに頼らず SVG で出している。 |
| **SPAっぽい動き** | ページ全体を再読み込みせず、検索 ↔ 結果を切り替える。URL の `?q=` も更新する。 |

## 検索の仕組み

| 用語 | 意味 |
|---|---|
| **Web Worker** | 別スレッドで重い計算をする仕組み。検索は `search_worker.js`、画面は `main.js`。 |
| **メインスレッド** | 画面描画担当。ここが忙しいとフリーズする。だから検索を Worker に逃がしている。 |
| **正規化 (`normalize`)** | 「ネコ」と「ねこ」、「ＮＵＴＲＯ」と「nutro」を同じとみなす前処理。`common.js`。 |
| **インデックス** | 検索用に事前につくった文字列。`_searchFullText`（全文）、`_weightedFields`（場所別）。 |
| **重み付けスコア** | ヒットした場所で点数を変える。商品名 100点、完全一致 +500、ブランド 50、タグ 20、説明文 5。高い順に並ぶ。 |
| **AND検索** | 入力した単語がすべて含まれる商品だけ残す。 |
| **IndexedDB** | ブラウザ内の大きめ倉庫。商品データを保存し、2回目以降は通信を減らす。 |
| **localStorage** | 小さめ倉庫。お気に入り（`pet925_favs`）を保存。ドメインが変わると消える。 |

店員コメント:

- `pickStoreComments()` … 選んだ cond / animal タグに応じた一言
- `pickKeywordComments()` … 検索欄の言葉（「心臓」「納豆菌」など）に応じた追加の一言

## Git・公開・秘密情報

| 用語 | 意味 |
|---|---|
| **Git** | 変更履歴。いつ何を直したか残す。 |
| **リポジトリ** | このプロジェクト一式。今は GitHub の `kyuni-f/pet925`。 |
| **commit** | 「この時点のスナップショット」を記録すること。 |
| **push** | 手元の commit を GitHub に送る。これが公開につながる。 |
| **GitHub Pages** | GitHub 上のファイルをウェブサイトとして出すサービス。**このリポジトリでは中身をそのまま出す。** サーバー側で CSV からビルドし直す工程（GitHub Actions）は無い。 |
| **GitHub Actions / CI** | push のたびにサーバーでテストやビルドを走らせる仕組み。このリポジトリには無い。それが無いのに生成 JSON を Git から外すと、公開サイトに商品データが届かない。 |
| **`.gitignore`** | Git に入れないファイルのリスト。今は `.env` と `node_modules` など。`*.json` や `product_data.json` は入れない（公開に必要。`package.json` まで消える）。 |
| **APIキー** | 楽天・Gemini などを使うためのパスワード相当。`.env` に置く。サイトの JS には出さない。`desc_helper` も HTML からは呼ばず、ローカル Python だけが読む。 |
| **ブックマークレット** | ブックマークバーに置く短い JavaScript。旧来の「楽天ページから CSV 1行／画像取得」用はリポジトリに無い。現行は `desc_helper` 用。**先に `npm run desc:helper` を起動**し、公式ページ上で押す。サーバーが止まっていると「接続が拒否されました」になる。手順は `docs/MANUAL.md` §2。 |
| **Formspree** | 静的サイトから問い合わせを受け、指定メールへ転送する外部サービス。宛先アドレスはサイトに出ない。無料枠は月50件程度。 |
| **`FORMSPREE_FORM_ID`** | Formspree の公開フォームID。`.env` に書き、ビルドで `data_master.js` に出る。メールアドレスそのものではない。 |
| **`mailto:`** | クリックするとメールソフトが開くリンク。宛先がブラウザに渡るので、隠したまま送る用途には使えない。このサイトでは廃止。 |
| **ハニーポット** | 人間には見えない入力欄。ボットが埋めたら送信を捨てる。このサイトでは `_gotcha`。 |
| **`_gotcha`** | Formspree 向けハニーポット欄の名前。画面外に置いてあり、人が普通に送ると空のまま。 |

## SEO・計測・収益まわり

| 用語 | 意味 |
|---|---|
| **SEO** | 検索エンジン向けの最適化。タイトル、description、canonical など。 |
| **canonical** | 「本物のURLはこちら」と検索エンジンに伝えるタグ。コピーサイト対策。 |
| **OGP** | SNS でシェアしたときのタイトル・画像。 |
| **JSON-LD** | 検索結果にサイト情報を出すための構造化データ。 |
| **GA4 / gtag** | Google アナリティクス。何が検索されたか、0件ヒットは何か、を見る。 |
| **Cookie** | 計測用の小さな記録。ローカルでは `cookie_domain: none` にして警告を抑えている。 |
| **アフィリエイト** | ショップへ送客して報酬を得る仕組み。**現在は全提携停止中。** ID は空。 |
| **もしもアフィリエイト** | 複数モールをまとめるゲートウェイ。コード上は `getMoshimoUrl()` が残っている。 |
| **PR表記** | 広告であることの明示。ヘッダーの `(PR)` と利用規約モーダル。 |

## 品質・開発の作法

| 用語 | 意味 |
|---|---|
| **DRY** | Don't Repeat Yourself。同じ処理を2箇所に書かない。`common.js` / `pet_utils.py` が典型。 |
| **リファクタリング** | 動きは変えず、読みやすく直すこと。 |
| **ユニットテスト** | 小さな関数単体のテスト。`tests/`、`npm test`（Jest）。今は `common.js` と `comment_logic.js` だけ。全ファイルには書かない。 |
| **テストスイート** | テストファイル1つ分。`npm test` の `Test Suites: 2` はファイルが2つ、という意味。 |
| **テストケース** | 個々の確認項目。今は19件。スイート数よりこちらが「何を守っているか」。 |
| **モック** | 本物の代わりに用意する偽物（画面、API、Worker）。増やすとテスト自体が壊れやすいので、このサイトでは DOM や外部 API までモックしない。 |
| **JSDoc** | 関数の上に書くコメント。`@param` は引数、`@returns` は戻り値、`@type` は変数の型。プログラムは無視し、エディタだけが読む。 |
| **`@ts-check`** | ファイル先頭に書くと、そのファイルだけ型を検査する。今は `common.js` と `comment_logic.js`。`jsconfig.json` の `checkJs` は `false`（全体オフ、個別にオン）。 |
| **`@ts-ignore`** | 次の1行の型警告を無視する。実行は変わらない。ブラウザでは見えるが型上は見えない名前（`normalize`）に使う。 |
| **問題パネル** | Cursor 下部の「問題」タブ。型の警告が並ぶ。**ブラウザの赤いエラーではない**ので、件数があってもサイトは動くことがある。 |
| **ガードレール** | 壊れたデータを公開しない仕組み。バリデーション失敗で `sys.exit(1)`。 |
| **難読化** | 中身を読みにくくすること。#66 の文字コード配列がそれ。ボット避けにはなるが、人の目や `mailto:` では隠せない。 |
| **ReferenceError** | 「その関数/変数はまだ存在しない」エラー。読み込み順が原因になりやすい。 |
| **DX** | 開発者自身の作業しやすさ。自動ビルド、テスト、型チェックなど。 |

## 「詰まったとき」の地図

| やりたいこと | 見る場所 |
|---|---|
| タグやフィルターの名前を変えたい | `data/tags.csv` → ビルド → `data_master.js` が更新される |
| 検索の当たり方を変えたい | `search_worker.js` のスコア、`common.js` の `normalize` |
| 画面の動きを変えたい | `main.js` |
| 見た目を変えたい | `style.css` / `index.html` |
| 商品を増やしたい | `jan_list.csv` → `npm run collect:all`、または ODS を手編集 |
| 説明文だけ作り直したい | `npm run desc:helper` → `desc` 列に貼る → ビルド |
| 公開したい | `npm run deploy` |
| 問い合わせを有効にしたい / 届き先を変えたい | `.env` の `FORMSPREE_FORM_ID` と Formspree 管理画面。手順は `docs/MANUAL.md` §7 |
| エディタの「問題」がたくさん出る | 実行エラーとは限らない。`jsconfig.json` と、ファイル先頭の `// @ts-check`。用語は後半の「型チェック」 |
| JSON を `.gitignore` した方がよいか迷う | 今はしない。Pages がリポジトリをそのまま出す。`product_data.json` が無いと検索が読めない |
| 運用の手順 | `docs/MANUAL.md` |
| 「なぜこう作ったか」 | `docs/PROJECT_SUMMARY.md` |

---

# 後半：プログラミングそのものの言葉

前半が「このサイトの部品名」なら、後半は「どのプログラムでも出てくる文法・道具の名前」です。できるだけ pet925 の実例で説明します。

## コンピュータと開発の基本

| 用語 | 意味 | このプロジェクトでの例 |
|---|---|---|
| **ソースコード** | 人間が書いたプログラムの本文。 | `main.js` や `csv_to_json.py` |
| **実行する** | 書いた命令をコンピュータにやらせること。 | ブラウザが JS を動かす / ターミナルで `python3` を動かす |
| **フロントエンド** | ユーザーのブラウザ側。画面・操作。 | `index.html`, `style.css`, `main.js` |
| **バックエンド** | サーバー側。このサイトは本格的なサーバーを持たず、ビルド用の Python がその役割に近い。 | `csv_to_json.py`, `auto_collect_all.py`, 説明取り直し時の `desc_helper.py` |
| **クライアント** | データを「使う側」。ここではブラウザ。 | 訪問者の Chrome など |
| **サーバー** | データを「出す側」。 | GitHub Pages、楽天 API、Gemini API |
| **ライブラリ** | 他人が作った便利な部品。自分のサイト本体には混ぜないことも多い。 | Python の `requests`、テスト用の Jest |
| **フレームワーク** | アプリの骨格まで決める大きな枠。 | **このサイトは使っていない**（Vanilla JS） |
| **依存関係** | 「動かすために必要な他の部品」。 | `package.json` の `jest`、`python3-requests` |
| **ランタイム** | コードを実際に動かす環境。 | ブラウザ（JS） / Python 3 / Node.js（テスト時） |
| **エンコーディング** | 文字の保存形式。日本語は **UTF-8** が基本。 | CSV を `encoding="utf-8-sig"` で読む |
| **パス（path）** | ファイルの住所。 | `data/tags.csv`、`/home/kyuni/ドキュメント/pet925` |
| **相対パス / 絶対パス** | 今いる場所からの道筋 / ルートからの完全な住所。 | `data/tags.csv` が相対、`/home/.../pet925` が絶対 |
| **コメント** | プログラムに無視されるメモ。 | JS は `//`、Python は `#`、HTML は `<!-- -->` |
| **シンタックス（構文）** | その言語の書き方ルール。1文字違うと動かない。 | 閉じ括弧 `}` の忘れ |
| **セマンティクス** | 「書いてあることの意味」。文法は合っていても意図と違う動きをすることがある。 | |
| **バグ** | 意図しない動き。 | 検索してもヒットしない、ボタンが反応しない |
| **デバッグ** | バグの原因を探して直すこと。 | ブラウザの開発者ツール、ターミナルのエラー文 |

## このプロジェクトで使っている言語

| 言語 | 役割 | 主なファイル |
|---|---|---|
| **HTML** | ページの構造（見出し、ボタン、入力欄）。中身の骨組み。 | `index.html` |
| **CSS** | 見た目（色、余白、並び方、スマホ対応）。 | `style.css` |
| **JavaScript (JS)** | 動き（検索、お気に入り、画面切り替え）。 | `main.js`, `search_worker.js` など |
| **Python** | データの検品・変換・API収集。ブラウザでは動かない。 | `csv_to_json.py`, `auto_collect_all.py` |
| **JSON** | データの保存形式（言語というよりフォーマット）。 | `product_data.json` |
| **CSV** | 表形式のテキスト。人間が編集する。 | `data/products.csv` |
| **Bash** | ターミナルで打つ命令の言語。 | `npm run build` などの裏側 |
| **Markdown** | ドキュメント用の軽いマークアップ。 | このファイル、`README.md` |

拡張子と役割の対応:

- `.html` 構造 / `.css` 見た目 / `.js` 動き
- `.py` Python / `.json` データ / `.csv` 表 / `.md` 説明文
- `.ods` 表計算の原本

## データの種類（型）

プログラムは「どんな種類の値か」を区別します。

| 型 | 意味 | 例 |
|---|---|---|
| **文字列 (string)** | 文字の列。引用符で囲む。 | `"ニュートロ"`、`'pet925'` |
| **数値 (number)** | 計算できる数。 | `20`（PAGE_SIZE）、`100`（スコア） |
| **真偽値 (boolean)** | はい / いいえ。 | `true` / `false`。`showFavoritesOnly` |
| **配列 (array / list)** | 順番のあるリスト。 | `favorites = ['123', '456']`、Python の `tags = []` |
| **オブジェクト / 辞書 (object / dict)** | 「名前 → 値」の対応表。 | JS の `activeFilters`、Python の `config = {}` |
| **null / None** | 「値がない」。 | JS は `null`、Python は `None` |
| **undefined** | JS 特有。「まだ入っていない」。 | 変数を宣言した直後など |
| **関数 (function)** | 「後で実行できる処理のかたまり」も値として扱える。 | `normalize`、`render` |

エディタが見る型（サイトの配信ファイルには含まれない）:

| 用語 | 意味 | このプロジェクトでの例 |
|---|---|---|
| **型チェック** | 実行する前に「種類が合っているか」をエディタが見ること。動きは変わらない。 | `// @ts-check` 付きの `comment_logic.js` |
| **型注釈** | 「これは文字列の配列です」とコメントで教えること。 | `/** @type {Record<string, string[]>} */` |
| **Record** | 「キーの型 → 値の型」の対応表。 | `"cond:tear"` → `['コメントA', 'コメントB']` |
| **any** | 「何でもあり」。型検査が効かない。空の `{}` に `lookup[key]` するとこれに落ちやすい。 | |
| **チェック対象外（オプトイン）** | 全体はオフにして、検査したいファイルだけ `@ts-check` を付けるやり方。 | `jsconfig.json` の `checkJs: false` |

配列とオブジェクトの違い（超重要）:

- 配列は **順番** で取り出す → `favorites[0]`
- オブジェクトは **名前** で取り出す → `item.name`、`row["jan"]`

## 変数・関数・制御（どの言語でも同じ考え方）

| 用語 | 意味 | 実例 |
|---|---|---|
| **変数** | 値につける名札。 | `let visibleCount = 20;` |
| **定数** | 途中で入れ替えないつもりで置く変数。 | JS の `const PAGE_SIZE = 20;` |
| **代入** | `=` で右の値を左に入れる。数学の「等しい」ではない。 | `favorites = []` |
| **比較** | `===`（JS）や `==`（Python）で「同じか？」を見る。 | `filterVal === 'all'` |
| **関数** | 名前を付けた手順書。何度でも呼べる。 | `function toggleFavorite(...) { ... }` |
| **引数（パラメータ）** | 関数に渡す材料。 | `toggleFavorite(id, nameForLog, btnElement)` の3つ |
| **戻り値（return）** | 関数が出す答え。 | `normalize(str)` は整えた文字列を返す |
| **呼び出し** | 関数を実際に動かすこと。末尾の `()`。 | `render(false)` |
| **スコープ** | その変数が使える範囲。関数の中で作った変数は外から見えないことが多い。 | |
| **グローバル変数** | どこからでも見える変数。ブラウザの `<script>` 順で共有する。 | `data_master.js` の `tagMaster`、`comments`。`common.js` の `normalize` も実行時はグローバルだが、末尾の `module.exports` があると型チェックからは見えにくい |
| **条件分岐** | 「もし〜なら」。 | `if (showFavoritesOnly) { ... } else { ... }` |
| **ループ（繰り返し）** | 同じ処理を何回も。 | `for (const item of allProducts)`、Python の `for line in f:` |
| **早期リターン** | 条件を満たさなければすぐ抜ける。 | `if (!str) return "";` |
| **例外（エラー）** | 想定外が起きたときの飛び方。 | Python の `try/except`、JS の `try/catch` |

JS の変数宣言の使い分け:

- `const` … 入れ替えない（関数、設定値、配列そのものを別物にしない）
- `let` … 後から変わる（件数、タイマー、フィルター状態）
- `var` … 古い書き方。このプロジェクトでは使わない

関数の書き方（同じ意味の別表記）:

```javascript
function normalize(str) { ... }     // 普通の関数宣言
const isMulti = (cat) => ...;       // アロー関数（短い処理向き）
```

Python:

```python
def normalize_text(s):
    return ""
```

## HTML でよく見るもの

| 用語 | 意味 | 例 |
|---|---|---|
| **タグ** | `<名前>` と `</名前>` で囲む部品。 | `<header>`、`<button>`、`<input>` |
| **要素（element）** | タグとその中身ひとまとまり。 | 検索ボタン1つ |
| **属性（attribute）** | タグにつける追加情報。 | `id="search-input"`、`onclick="showResults()"` |
| **id** | ページ内で一意な名前。JS から探しやすい。 | `getElementById('product-list')` |
| **class** | 見た目やグループ分け用の名前。同じ class を何個つけてもよい。 | `class="btn-primary-action"` |
| **`<head>` / `<body>`** | 設定（タイトル、CSS、解析タグ） / 実際に見える中身。 | |
| **`<script>`** | JavaScript を読み込む。 | `main.js` の読み込み |
| **`<link>`** | CSS などをつなぐ。 | `style.css`、canonical |
| **セマンティック** | 「見た目」より「意味」が分かるタグを使うこと。 | `<header>`、`<footer>` を div の代わりに使う |

## CSS でよく見るもの

| 用語 | 意味 | 例 |
|---|---|---|
| **セレクタ** | 「どの要素にスタイルを当てるか」の指定。 | `#search-input`（id）、`.modal-overlay`（class） |
| **プロパティ** | 何を変えるか。 | `color`、`margin`、`display` |
| **値** | どれくらいか。 | `#c5a059`、`16px`、`flex` |
| **Flexbox** | 横並び・縦並びを柔軟に決めるレイアウト。 | ヘッダーやボタン列 |
| **Grid** | タイル状の格子レイアウト。 | 商品カードの並び |
| **余白: margin / padding** | 外側の空き / 内側の空き。 | |
| **メディアクエリ** | 画面幅などで見た目を切り替える。 | スマホ向け `@media` |
| **擬似クラス** | 「その要素の特定の状態」。 | `:hover`（マウスを乗せたとき）、`.active` |
| **レスポンシブ** | スマホでも PC でも使えるようにすること。 | |
| **px / rem / %** | 長さの単位。px は固定、rem は文字サイズ基準、% は親要素基準。 | |
| **z-index** | 重なりの前後。モーダルを前面に出すときに使う。 | |
| **transition / animation** | 変化を滑らかにする / 動きをつける。 | ヘッダーの伸縮、リストの fadeIn |

## JavaScript でよく見る関数・書き方

ここが画面側の「頻出フレーズ集」です。

### 探す・書き換える（DOM）

| 書き方 | 意味 |
|---|---|
| `document.getElementById('search-input')` | id で要素を1つ取る |
| `document.querySelector('.short-desc')` | CSS と同じ書き方で最初の1つを取る |
| `document.querySelectorAll('.filter-btn')` | 条件に合う要素を全部取る |
| `element.innerHTML = '...'` | 要素の中身の HTML を入れ替える |
| `element.textContent` | 文字だけ（タグは解釈しない） |
| `element.classList.add('active')` | class を付ける |
| `element.classList.remove('active')` | class を外す |
| `element.classList.toggle('active')` | あれば外し、なければ付ける |
| `element.setAttribute('aria-label', '...')` | 属性を書く（読み上げ用など） |
| `element.addEventListener('click', fn)` | クリックされたら関数を実行（このサイトは `onclick=` も多用） |

### 配列・オブジェクト

| 書き方 | 意味 |
|---|---|
| `array.push(x)` | 末尾に追加。お気に入り追加。 |
| `array.splice(index, 1)` | 指定位置を削除。お気に入り解除。 |
| `array.indexOf(x)` | 何番目か。無ければ `-1`。 |
| `array.includes(x)` | 入っているか。 |
| `array.forEach(fn)` | 1件ずつ処理。 |
| `array.map(fn)` | 1件ずつ変換して新しい配列を作る。 |
| `array.filter(fn)` | 条件に合うものだけ残す。 |
| `array.every(fn)` | 全部が条件を満たすか（AND の判定に使う）。 |
| `array.slice(0, n)` | 先頭 n 件を切り出す。「さらに表示」の件数制限。 |
| `array.sort(fn)` | 並び替え。スコア順。 |
| `Object.keys(obj)` | オブジェクトのキー名一覧。 |
| `Object.entries(obj)` | `[キー, 値]` のペア一覧。 |
| `JSON.parse(文字)` | JSON 文字列 → オブジェクト。お気に入り読み込み。 |
| `JSON.stringify(obj)` | オブジェクト → JSON 文字列。お気に入り保存。 |

### 文字

| 書き方 | 意味 |
|---|---|
| `str.trim()` | 前後の空白を消す |
| `str.toLowerCase()` | 小文字にする |
| `str.includes(word)` | その単語を含むか |
| `str.indexOf(word)` | 何文字目か。無ければ `-1` |
| `str.replace(a, b)` | 置き換え |
| `str.split(' ')` | 空白で分割して配列にする |
| `` `件数は ${n} 件` `` | テンプレートリテラル。変数を文字に埋め込める |

### 時間・非同期

| 書き方 | 意味 |
|---|---|
| `setTimeout(fn, 800)` | 800ミリ秒後に実行。デバウンスの本体。 |
| `clearTimeout(timer)` | 予約をキャンセル。打ち込み中は前の予約を消す。 |
| `Promise` | 「あとで結果が出る作業」の約束。IndexedDB や fetch で使う。 |
| `async / await` | Promise を「順番に待つ」書き方。 |
| `fetch(url)` | ネットからファイルを取る／送る。Worker が JSON を読むほか、問い合わせは Formspree へ `POST` する。 |
| `JSON.parse` と対で使う | `fetch` した本文をオブジェクトにする |

### 保存・ワーカー

| 書き方 | 意味 |
|---|---|
| `localStorage.getItem('pet925_favs')` | お気に入りを読む |
| `localStorage.setItem(キー, 値)` | お気に入りを書く |
| `new Worker('search_worker.js?v=...')` | 裏方スレッドを起動 |
| `worker.postMessage(data)` | メイン → Worker へ仕事を渡す |
| `self.postMessage(result)` | Worker → メインへ結果を返す |
| `importScripts('common.js')` | Worker 内で別 JS を読み込む |

### ブラウザとテスト（Node）の両用

同じ JS を、サイトでは `<script>`、テストでは `require` するときの定番です。

| 書き方 | 意味 |
|---|---|
| `typeof x !== 'undefined' ? x : []` | その名前がまだ無いか確認してから使う。テスト環境にグローバルが無くても落ちない |
| `typeof module !== 'undefined' && module.exports` | Node / Jest のときだけ書き出す。ブラウザでは `module` が無いので、この中は実行されない |
| `module.exports = { normalize }` | テストから `require('../common.js')` できるようにする。**副作用**: TypeScript はそのファイルをモジュールとみなし、中の `const` が他ファイルの型から見えなくなることがある |

### よく見る演算子

| 記号 | 意味 |
|---|---|
| `===` / `!==` | 型まで含めて同じ / 違う（JS では `==` よりこちらを使う） |
| `&&` | かつ（両方 true） |
| `\|\|` | または |
| `!` | 否定。`!isWorkerReady` は「まだ準備できていない」 |
| `?.` | オプショナルチェーン。無ければそこで止めてエラーにしない |
| `\|\| []` | 「無ければ空配列」の定番 |
| `...` | スプレッド。配列やオブジェクトを展開してコピー・結合 |
| `? :` | 三項演算子。`isFav ? '❤' : '♡'` |

## Python でよく見る関数・書き方

データ収集とビルド側の頻出フレーズです。

| 書き方 | 意味 |
|---|---|
| `import csv` | 部品を読み込む |
| `def 名前():` | 関数を定義 |
| `if __name__ == "__main__":` | 「このファイルを直接実行したときだけ」動く入口 |
| `open(path, encoding="utf-8")` | ファイルを開く |
| `with open(...) as f:` | 使い終わったら自動で閉じる。推奨の書き方 |
| `f.read()` / `f.write()` | 全部読む / 書く |
| `print("...")` | ターミナルに表示 |
| `sys.exit(1)` | 異常終了。ビルド失敗でデプロイを止める |
| `os.path.exists(path)` | ファイルがあるか |
| `os.getenv("GEMINI_API_KEY")` | 環境変数（秘密情報）を読む |
| `len(x)` | 個数・文字数 |
| `str.strip()` | 前後空白を消す |
| `str.split()` | 分割 |
| `dict.get("jan", "#")` | キーが無ければデフォルト値 |
| `list.append(x)` | 配列に追加 |
| `for k, v in dict.items():` | 辞書を1件ずつ |
| `try / except` | 失敗しても落とさず扱う |
| `requests.get(url)` / `requests.post(url)` | HTTP でデータを取る / 送る |
| `response.json()` | 応答を辞書にする |
| `time.sleep(5)` | 5秒待つ（API の再試行） |
| `re.sub(パターン, 置換, 文字)` | 正規表現で置換 |

Python と JS の対応（同じことをするとき）:

| やりたいこと | JavaScript | Python |
|---|---|---|
| 変数 | `const` / `let` | 宣言キーワードなし。`name = "a"` |
| 関数 | `function f()` / `() =>` | `def f():` |
| 辞書アクセス | `obj.key` または `obj["key"]` | `obj["key"]` または `obj.get("key")` |
| 長さ | `arr.length` | `len(arr)` |
| 何もない | `null` / `undefined` | `None` |
| 真偽 | `true` / `false` | `True` / `False`（大文字） |
| 正規化関数 | `normalize()` in `common.js` | `normalize_text()` in `pet_utils.py` |

## ブラウザと通信

| 用語 | 意味 |
|---|---|
| **URL** | ページや API の住所。`https://kyuni-f.github.io/pet925/` |
| **HTTP** | ネットでデータをやり取りする約束。 |
| **GET** | 「ください」。検索やファイル取得。 |
| **POST** | 「受け取って処理してください」。問い合わせの Formspree 送信、Gemini への文章生成依頼。 |
| **`mailto:`** | `mailto:someone@example.com` のように書くと、メールソフトが開く。宛先は必ず見える。 |
| **ステータスコード** | 結果の番号。`200` 成功、`404` 見つからない、`503` 混雑。 |
| **ヘッダー** | リクエストに添えるメモ。`User-Agent`、`Content-Type`、`Origin` など。 |
| **クエリパラメータ** | URL の `?` 以降。`?q=涙やけ` のように検索条件を載せる。 |
| **API** | プログラム同士の窓口。「この形式で聞けば、この形式で返す」。楽天 API、Gemini API。 |
| **JSON API** | やり取りの中身が JSON のもの。今どきの主流。 |
| **エンドポイント** | API の具体的な URL。 |
| **タイムアウト** | 待ち時間の上限。応答が来なければ失敗にする。 |
| **リトライ** | 失敗したら間を置いて再挑戦。503 のときにやっている。 |
| **CORS** | ブラウザが「別ドメインのデータを勝手に取らない」制限。 |
| **User-Agent** | 「自分はどんなソフトか」を名乗る文字列。 |
| **localhost** | 自分のパソコン自身。`127.0.0.1` と同じ。公開前の確認で使う。 |
| **`file://`** | ファイルを直接ブラウザで開いた状態。一部機能（Worker、GA）が制限されることがある。 |

## Git と npm の基本語

| 用語 | 意味 |
|---|---|
| **ワーキングツリー** | 今編集中のファイルたち。 |
| **ステージング** | 「次の commit に入れる」と印を付けた状態。`git add`。 |
| **差分（diff）** | 何が変わったか。 |
| **ブランチ** | 作業の枝。このリポジトリは主に `main`。 |
| **origin** | GitHub 側の別名。 |
| **コンフリクト** | 同じ場所を別々に直して衝突すること。 |
| **npm** | Node.js 用のパッケージ管理。`package.json` を読む。 |
| **`npm install`** | 依存関係を入れる。`node_modules/` ができる。 |
| **`npm test` / `npm start` / `npm run ○○`** | `package.json` の `scripts` を実行する。 |
| **Node.js** | ブラウザ以外で JS を動かす実行環境。Jest のテストで使う。 |
| **Jest** | テストを自動で走らせる道具。サイト本体には含まれない。 |

よく使う Git の意味:

- `git status` … 今なにが変わっているか
- `git diff` … 具体的な差分
- `git log` … これまでの commit
- `git add` / `git commit` / `git push` … 記録して送る

## よく見るエラーの読み方

エラー文は「落ちた場所」と「理由」が書いてあります。全部読まなくてよいので、最後の数行とファイル名を見る。

| エラー | だいたいの意味 | よくある原因 |
|---|---|---|
| **ReferenceError: xxx is not defined** | その名前がまだ無い | 読み込み順、タイプミス、ビルド前の `data_master.js` |
| **TypeError: Cannot read properties of null** | 無いものに `.` で触った | `getElementById` が失敗（id のスペルミス） |
| **SyntaxError** | 書き方が壊れている | 括弧の閉じ忘れ、カンマ不足 |
| **404** | ファイルが無い | パス間違い、まだビルドしていない |
| **403** | 権限がない | API キーやドメイン制限 |
| **503** | 相手が混んでいる | Gemini / 楽天。少し待ってリトライ |
| **CORS error** | ブラウザが通信を止めた | ローカルの開き方、API 側の許可設定 |
| **ENOENT** | ファイルが見つからない（Python/Node） | パスや作業ディレクトリが違う |
| **Module not found** | 部品が無い | `npm install` 忘れ |
| **バリデーションエラー（ビルド）** | CSV の中身がルール違反 | 未登録タグ、列不足、重複 |
| **問題パネルの TS〜（型警告）** | エディタの型チェック。**ブラウザは落ちない** | `@ts-check` 付きファイル。空の `{}`、見えないグローバルなど |
| **Cannot find name 'xxx'** | 型の世界にその名前が無い | `normalize`（`common.js` に `module.exports` があるため） |
| **Property 'cond' does not exist on type '{}'** | 空オブジェクトにプロパティを読んだ | `let activeFilters = {}` のままだと型が空 |
| **Element implicitly has an 'any' type** | `obj[key]` のとき、`obj` に「文字列キーで触ってよい」と書いていない | `const lookup = {}` に JSDoc の `Record` が無いとき |

## 設計でよく出る言葉

コードレビューやドキュメントに出てきたら、この表を見る。

| 用語 | 意味 | このサイトでの実例 |
|---|---|---|
| **状態管理** | 「今どういう状況か」を変数で持つこと。 | `activeFilters`、`favorites`、`visibleCount` |
| **イベント** | 「クリックされた」「入力された」などのきっかけ。 | `onclick`、`oninput`、GA4 の `trackEvent` |
| **コールバック** | 「終わったら呼んでほしい関数」を渡すこと。 | `setTimeout` に渡す関数、`forEach` の中身 |
| **副作用** | 戻り値以外に、画面やファイルを変えること。 | `localStorage.setItem`、`innerHTML =` |
| **純関数** | 同じ入力なら同じ出力。外の世界を変えない。 | `normalize()` はこれに近い |
| **モジュール** | 役割ごとに分けたファイル。ブラウザではグローバル、Jest では `module.exports`、という二面がある。 | `common.js`、`comment_logic.js`、`pet_utils.py` |
| **インターフェース** | 「こう渡せばこう返る」という約束。 | Worker の `postMessage` の中身 |
| **ハードコード** | 値をコードに直書きすること。設定ファイルに出した方が変えやすい場合がある。 | |
| **マジックナンバー** | 意味の分からない数字。名前付き定数にする。 | `PAGE_SIZE = 20`、`MAX_STORE_COMMENTS = 2` |
| **オフバイワン** | 1個ずれるバグ。配列の 0 始まりが原因になりやすい。 | |
| **正規表現 (Regex)** | 文字のパターン指定。 | JAN の数字だけ残す、画像 URL の `?_ex=` を消す |
| **ハッシュ** | データを短い指紋にする。ID 生成などに使う。 | お気に入り ID（JAN が無いときの代替） |
| **キャッシュ** | 一度計算・取得した結果を再利用。 | IndexedDB、ブラウザキャッシュ |
| **スレッド** | 同時に進む作業の列。 | メインスレッドと Web Worker |
| **ブロッキング** | 重い処理で他が止まること。検索を Worker に逃がす理由。 | |
| **UX** | 使う人の気持ちよさ。 | デバウンス、モーダル、フリーズしない検索 |
| **アクセシビリティ (a11y)** | 読み上げやキーボードでも使えること。 | `aria-label` |
| **コンソール** | 開発者ツールの黒い画面。`console.log` の出力先。コピー抑制の警告もここ。 | |

## 読み方のコツ

コードを読むときは、次の順が分かりやすいです。

1. **ファイル名**で役割を当てる（画面なら `main.js`、データの検品なら `.py`）
2. **関数名**を先に眺める（`toggleFavorite` なら「お気に入りのオンオフ」）
3. **引数と return** を見る（何を受け取って何を返すか）
4. 中の `if` とループを追う
5. 分からない単語はこの語録集で引く

「全部理解してから動かす」必要はありません。動いているコードを、上の順で少しずつ読めるようになれば十分です。
