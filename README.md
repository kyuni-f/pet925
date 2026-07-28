# pet925 | Premium Pet Nutrition Guide

科学的な根拠に基づいたプレミアムペットフードの選定ガイドシステムです。
10万件規模のデータをブラウザ上で快適に検索できる、Web Worker + Pythonビルドによる高性能な静的サイトアーキテクチャを採用しています。

## 🚀 プロジェクトの目的 (Objective)
- **データ管理の効率化**: 複雑なペットフードのデータをミスなく、楽に管理する。
- **高速な検索体験**: 大規模データ（10万件〜）でもフリーズしない爆速な検索体験の実現。
- **検索精度の追求**: 商品名・ブランド・説明文の重要度に応じた「重み付けスコアリング」による並び替え。
- **パーソナライズ**: ユーザーが気になる商品を保存できる「お気に入り」機能の提供。
- **ショップ横断検索ナビ**: URL未入力でも各モールの検索結果へ自動誘導。
- **運用自動化**: AI APIを活用した商品データの自動収集・登録パイプラインの構築。
- AI（Gemini）を開発パートナーとして、爆速でコンテンツを拡充する。

## 📂 構成ファイル (Context)
### 📂 Directory Structure
- **`data/`** : `pet925_master.ods` (5シート構成のマスター), 各種CSV (products, categories, tags, brands, rules)
- **`index.html`** : サイト本体（ルート配置により公開を簡素化）
- **`csv_to_json.py`** : Pythonによる統合ビルド・バリデーションスクリプト（画像フィルター含む）
- **`search_worker.js`** : Web Workerによる非同期検索エンジン
- **`csv_helper.html`** : CSV用の1行を簡単に作成するための入力補助ツール
- **`product_data.json`** : 検索エンジンが読み込む商品データベース（メタ情報）
- **`product_data_*.json`** : 商品データの分割チャンク（ビルド時に生成）
- **`auto_data_collector.py`** : URLから商品データを自動生成・追記する自動化スクリプト
- **`auto_collect_all.py`** : JANコードリスト（`jan_list.csv`）から楽天/Yahoo!/Gemini APIを使い全自動で `products.csv` を生成するスクリプト
- **`jan_data_collector.py`** : JANコードから画像・商品名・リンクのみを簡易取得するスクリプト（`auto_collect_all.py` の簡易版）
- **`jan_list.csv`** : `auto_collect_all.py` / `jan_data_collector.py` に読み込ませるJANコードの入力リスト（1行1コード、使い切り）
- **`data_master.js`** : フィルターやブランド設定を管理するマスタースクリプト
- **`test_image_filter.py`** : 画像フィルター（年齢・URLスコアリング）の単体テスト
- **`package.json`** : プロジェクトの設定と依存関係を管理する「身分証明書」
- **`package-lock.json`** : インストールされたライブラリのバージョンを完全に固定する「検品名簿」
- **`docs/`** : `MANUAL.md` (運用手順書), `PROJECT_SUMMARY.md` (開発記録), `AI_INSTRUCTIONS.md` (AI用指示書)
- **`README.md`** : プロジェクトの全体概要（このファイル）

## 🛠 開発者コマンド
```bash
# 1. 依存関係のインストール
npm install

# 2. Pythonライブラリのインストール
sudo apt install python3-requests

# 3. データのビルド（CSV -> JSON 変換）
npm run build
# または
python3 csv_to_json.py

# 4. 画像フィルター更新後の再ビルド（既存 img URL を破棄して取り直す）
python3 csv_to_json.py --force-refresh

# 5. ファイル変更を監視しながらビルド（開発中）
npm start

# 6. 画像フィルターの単体テスト
python3 -m unittest test_image_filter.py -v

# 7. データの公開（デプロイ）
npm run deploy  # 検品、ビルド、コミット、プッシュを一括実行

# 8. 強制同期（競合等でプッシュできない場合）
git push origin main --force

# 9. VS Code 本体の更新 (Linux環境)
sudo apt update && sudo apt install code

# 10. APIで商品データを自動生成
python3 auto_data_collector.py ""

# 11. JANコードリストから商品データを全自動生成（楽天/Yahoo!/Gemini API使用）
npm run collect:all   # データ収集 + JSONビルドまで一括実行
# または
npm run collect jan_list.csv   # データ収集のみ（別途 npm run build が必要）
```

> **JANコードからのCSV自動生成手順の詳細**（`jan_list.csv` の書き方、追加方式の仕組みなど）は `docs/MANUAL.md` の「A-2. JANコードからのCSV自動生成」を参照してください。

> **画像フィルターを変更した場合**は、必ず `python3 csv_to_json.py --force-refresh` を実行してからデプロイしてください。通常の `npm run build` だけでは、CSVに既に保存された古い `img` URL は更新されません。

## 🖼 画像自動取得パイプライン（csv_to_json.py）

JANコードが入力された商品は、ビルド時に以下の優先順位で画像を自動取得します。

| 優先度 | 取得元 | 特徴 |
|---|---|---|
| **①** | **楽天Product Search API(v2)** （商品価格ナビAPIのマイクロサービス版） | 透かし・ロゴなしの公式カタログ画像（`r.r10s.jp`）。**最優先** |
| ② | Yahoo!ショッピングAPI | 一部ショップロゴが入る場合あり |
| ③ | 楽天商品検索API(IchibaItem) | スコアリングフィルター適用 |
| ④ | 推測ショップリスト | `DEFAULT_RAKUTEN_IMAGE_SHOPS` で設定 |
| ⑤ | Google CSE | ローカルキャッシュにダウンロード保存 |

**多層フィルター**:
- **商品名・サブ文字**: APIの `itemName` に加え `itemCaption` 等も照合。年齢（1歳/11歳）・容量（kg）・箱セット表記を検証
- **年齢の厳密判定**: `(?<!\d)(\d+)歳` で部分一致を防止（「1歳」が「11歳」に誤マッチしない）
- **キーワード一致**: 1語だけの部分一致では通さず、複数キーワードの過半数一致を要求
- **URLスコアリング**: ショップロゴ入りURL、非JAN画像を大減点。`r.r10s.jp` を高スコア化
- **JAN優先**: `/cabinet/jan/{JAN}.jpg` 形式の画像を最優先採用

> **画像の「参考画像」バッジや出典注釈は表示されません**（楽天公式カタログ画像のため不要と判断）。
> 誤画像が残る場合は `img` 列に正しいURLを手動設定するか、ブックマークレットで取得してください（詳細は `docs/MANUAL.md`）。

## 🌐 カスタムドメインの導入手順
将来的に独自ドメイン（例：www.pet925.com）を運用する際の手順です。

1. **ドメインの取得**: お名前.comやGoogle Domainsなどでドメインを購入。
2. **DNSの設定**: ドメイン管理画面で、GitHub Pagesのサーバーを指定します。
    - A レコード: GitHubのIPアドレス（185.199.108.153 等）を設定。
    - CNAME レコード: `kyuni-f.github.io` を設定。
3. **GitHubの設定**: リポジトリの [Settings] > [Pages] > [Custom domain] に購入したドメインを入力。
4. **プロジェクトファイルの更新**:
    - `index.html`: `<link rel="canonical">` のURLを新しいドメインへ書き換え。
    - `main.js`: `authorizedDomains` 配列に新しいドメインを追加。
5. **反映の確認**:
    - `npm run deploy` で変更を反映。
    - 数分〜数時間後に新しいドメインでサイトにアクセスできるか確認。

> **注意**: ドメイン変更直後は、お気に入りデータ（localStorage）がリセットされます。

## 📖 AI・開発リファレンス
AI（Gemini等）を使用してデータ作成やコード修正を行う際は、以下の専用ドキュメントを参照してください。
- **商品データの作成依頼**: CSVデータの生成ルールとプロンプトは `docs/AI_INSTRUCTIONS.md` を参照。
- **開発コンテキストの共有**: プロジェクトの技術スタックや設計思想をAIに伝えるためのサマリーは `docs/PROJECT_SUMMARY.md` を参照。
- **運用マニュアル**: 日々の管理手順やトラブルシューティングは `docs/MANUAL.md` を参照。

## ✅ プロジェクトの進捗 (Status)
システムの全機能実装状況や詳細な改善履歴については、PROJECT_SUMMARY.md を参照してください。

### 主要なマイルストーン
- **基盤**: 10万件対応 Web Worker 検索エンジン & Pythonビルドパイプラインの確立
- **収益化**: もしもアフィリエイト統合 (Amazon/楽天/Yahoo!)
- **UX**: モバイル最適化、お気に入り機能、GA4による検索分析
- **画像品質**: 楽天Product Search API(v2)による透かし・ロゴなしの高画質カタログ画像自動取得

## 💡 便利な小技 (Tips)
- **AIの差分適用（Apply）が失敗する場合**:
    1. ターミナルで `git checkout .` を実行して、中途半端な変更をリセットします。
    2. AIが出力したコードブロックを丸ごとコピーし、対象ファイルの内容を全選択して上書き貼り付けします。
    3. 保存後、`python3 csv_to_json.py --force-refresh` を実行してバリデーションと画像再取得を確認します。
- **`package-lock.json` は手動で編集しない**: `npm install` 時に自動更新されます。常に Git に含めておくことで、どの環境でも全く同じように動作することを保証します。
- **GitHubで全ファイルを見る**: リポジトリ画面で `.` (ピリオド) を押すとWebエディタが起動します。
- **Linuxで隠しファイルを表示**: 
    - ターミナル: `ls -a`
    - フォルダ画面: `Ctrl + H`
- **強制リロード**: ブラウザで反映されない時は `Ctrl + F5`。
## ⚖️ 免責事項 (Disclaimer)
- **専門的助言の不提供**: 当サイト（pet925）に掲載されている情報は、科学的根拠に基づいた一般的なガイドラインであり、獣医学的な診断や個別のアドバイスを目的としたものではありません。フードの切り替えや健康管理については、必ずかかりつけの獣医師にご相談ください。
- **情報の正確性**: データの正確性には万全を期していますが、メーカーによる原材料・成分・価格の変更がリアルタイムに反映されない場合があります。購入の際は、必ず各ショップの販売ページをご確認ください。
- **損害への責任**: 当サイトの利用によって生じた直接的・間接的ないかなる損失や損害（健康被害、経済的損失等）についても、当サイトおよび運営者は一切の責任を負いかねます。

## 📄 ライセンス (License)
Copyright (c) 2024-2026 pet925. All Rights Reserved.  
当サイトのプログラム、テキスト、画像、および商品データの無断転載・複製・二次利用を固く禁じます。  
商用・非商用問わず、許可なくスクレイピングやミラーサイトを構築することを禁止します。
