# pet925 管理マニュアル

## 1. 運用ワークフロー（黄金のサイクル）
データの更新は、すべての情報を一つのマスターファイルで管理し、一括で書き出すのが効率的です。

1.  **Geminiに依頼**: 商品情報を依頼する。
2.  **マスターへ貼り付け**: `data/pet925_master.ods` 内の該当シート（products/tags/brands）を更新。
3.  **一括CSV出力**: Calcのマクロを使用して、各CSV（products/tags/brands.csv）を一気に書き出す。
4.  **自動変換**: ターミナルで `npm start` を実行（監視モード）。
5.  **確認**: `public/index.html` をブラウザで開き、**Ctrl + F5**。

> **💡 プログラム修正時の注意**: `convert.js` 内のタグ定義（TAG_MASTER）などを書き換えた場合は、一度ターミナルで **Ctrl + C** を押して監視モードを終了し、再度 `npm start` を実行してください。その後、`products.csv` を一度「上書き保存」すると確実に反映されます。
> **💡 新しいタグの追加**: `data/tags.csv` を編集することで、プログラムを触らずにフィルターボタンを増やせます。編集後は `products.csv` を上書き保存して反映させてください。

---

## 2. タグマスターの管理方法 (tags.csv)
フィルターボタンの種類や表示名は、`data/tags.csv` で一括管理しています。マスター（.ods）の「タグ一覧」シートを更新し、CSVとして書き出すことでサイトに反映されます。

### tags.csv の列構成
| 列名 | 説明 | 例 |
| :--- | :--- | :--- |
| **category** | フィルターの表示グループ | `animal`, `age`, `pref`, `cond` |
| **key** | `products.csv` の `tags` 列に記入する英単語 | `lamb`, `tear`, `gf` |
| **name** | サイトのボタンに表示される名前 | `ラム肉 (LAMB)` |

### 魚種エイリアス（自動タグ付け）
`products.csv` の `tags` 列に以下の単語を入力すると、自動的に「魚 (FISH)」タグが付与されます。
`salmon`, `tuna`, `bonito`, `mackerel`, `whitefish`, `cod`, `sardine`

### カテゴリの役割
- **animal**: 種類（犬・猫など。単一選択）
- **age**: 年齢（成犬・シニアなど。単一選択）
- **pref**: 製法・原材料（ウェット、ラム肉、魚など。**複数選択可**）
- **cond**: お悩み（健康ケア。**複数選択可**）

---

## 3. ブランドエイリアスの管理 (brands.csv)
「Nutro」を「ニュートロ」で検索できるようにする設定は `data/brands.csv` で行います。

### brands.csv の列構成
- **key**: CSVの `brand` 列に記入している英語名（小文字で判定されます）
- **name**: 日本語での読み方

---

## 4. 注意事項（ここだけは気をつけて！）

### ① ファイル名と場所
- フォルダ内に `products.csv` という名前で存在する必要があります。
- `products (1).csv` などの余計なファイルがあれば削除してください。
- **ファイル名の末尾に半角スペースが入らないよう注意してください。**（例：`products.csv ` はNG。プログラムが変更を検知できなくなる原因になります）

### ② Linux（LibreOffice）の挙動
- `.~lock.products.csv#` というファイルは、編集ソフトが開いている間だけ出る「鍵」です。**無視して大丈夫**です。ソフトを閉じれば消えます。
- CSV保存時に「テキスト形式で保存しますか？」と聞かれたら **[はい]** を選んでください。

### ③ A8.netなどの広告コード
- `img` 列には「画像のURL」のみ、`a8` 列には「リンク先のURL」のみを貼り付けてください。
- コードを丸ごと貼り付けると表示が崩れる原因になります。
- **価格列 (amz_p, rak_p, yah_p)**:
    - **半角数字のみ**（カンマ不要）で入力してください。
    - 入力すると、システムが自動で比較し、最も安いショップに「最安値」バッジを表示します。

### ④ ブラウザのキャッシュ
- `node convert.js` を実行しても画面が変わらない場合、ほとんどがブラウザの記憶（キャッシュ）のせいです。迷わず **Ctrl + F5** を押しましょう。

### ⑤ products.csv が上書きできない場合
1. **LibreOfficeを閉じる**: 保存時に「エラー」が出る場合、Calcがロックファイルを生成しています。Calcを閉じ、フォルダ内の `.~lock.products.csv#` を削除してください。
2. **npm start を止める**: 監視プログラムがファイルを読み込もうとして競合している場合があります。ターミナルで **Ctrl + C** を押して停止してから保存を試してください。
3. **権限の確認**: Linuxの権限エラーが出る場合は、ターミナルで `sudo chown $USER:$USER data/products.csv` を実行してください。

---

## 4. Google スプレッドシートでの運用方法
マスターデータを Google スプレッドシートで管理している場合の手順です。

### PC から操作する場合
1.  スプレッドシートを開く。
2.  **[ファイル]** > **[ダウンロード]** > **[カンマ区切り形式 (.csv)]** を選択。
3.  ダウンロードしたファイルを `data/products.csv` に上書きする。

### スマホ（Google スプレッドシートアプリ）から操作する場合
1.  アプリでシートを開く。
2.  画面右上の **[︙] (メニュー)** をタップ。
3.  **[共有と書き出し]** > **[名前を付けて保存]** をタップ。
4.  **[CSV (カンマ区切り)]** を選択して [OK] を押す。
5.  保存（または送信）されたファイルを、プロジェクトの `data/` フォルダへ配置してください。
    - ※スマホで編集してそのままサイトを更新するには、GitHub 等のクラウド経由でファイルを PC に同期させる必要があります。

### Gemini（AI）からデータを貼り付ける場合
1.  Gemini が出力した CSV コードブロックをコピーする。
2.  スプレッドシートの新しい行（A列のセル）を選択して貼り付ける (`Ctrl + V`)。
3.  貼り付け直後に右下に表示される小さなアイコン（貼り付けオプション）をクリックし、**「テキストを列に分割」** を選択。
4.  区切り文字が「カンマ」として認識され、各列に正しく振り分けられたことを確認してください。

---

## 5. マスターファイルの一元管理（LibreOffice Calc）
- **マルチシート運用**: `pet925_master.ods` 内に `products`, `tags`, `brands` の3シートを作成してください。
- **一括出力・バリデーションマクロ**: 
    1. [ツール] > [マクロ] > [マクロを管理] > [LibreOffice Basic] を開く。
    2. 以下の `ExportAllSheetsToCSV` と `CheckMandatoryFields` マクロを登録する。

```basic
Sub ExportAllSheetsToCSV
    Dim oDoc As Object, oSheets As Object, oSheet As Object
    Dim sURL As String, sPath As String
    Dim args(1) As New com.sun.star.beans.PropertyValue
    
    oDoc = ThisComponent

    ' ファイルが保存されているか（URLがあるか）チェック
    If (oDoc.URL = "") Then
        MsgBox "エラー: ファイルが保存されていません。" & Chr(13) & _
               "先に一度ファイルを保存してから実行してください。", 16, "実行失敗"
        Exit Sub
    End If

    ' ディレクトリパスを取得（末尾の / を含む）
    sPath = Left(oDoc.URL, InStrRev(oDoc.URL, "/"))
    oSheets = oDoc.Sheets
    
    ' CSV出力の設定
    args(0).Name = "FilterName"
    args(0).Value = "Text - txt - csv (StarCalc)"
    args(1).Name = "FilterOptions"
    args(1).Value = "44,34,76,1,,0,false,true,true" ' カンマ区切り, UTF-8
    
    Dim sheetNames As Variant
    sheetNames = Array("products", "tags", "brands")
    
    For Each sName In sheetNames
        If oSheets.hasByName(sName) Then
            oSheet = oSheets.getByName(sName)
            
            ' 書き出し前に必須項目の空欄チェックを実行
            If Not CheckMandatoryFields(oSheet, sName) Then
                MsgBox sName & " シートに不備があるため、書き出しを中断しました。", 48, "エラー"
                Exit Sub
            End If
            
            oDoc.CurrentController.setActiveSheet(oSheet)
            sURL = sPath & sName & ".csv"
            oDoc.storeToURL(sURL, args())
        End If
    Next sName
    
    MsgBox "全てのバリデーションをクリアし、CSVの一括出力が完了しました！", 64, "完了"
End Sub

Function CheckMandatoryFields(oSheet As Object, sName As String) As Boolean
    Dim i As Long, col As Integer
    Dim mandatoryCols As Variant
    
    ' シートごとの必須列（A=0, B=1, C=2...）
    If sName = "products" Then mandatoryCols = Array(0, 1, 2) ' name, brand, tags
    If sName = "tags"     Then mandatoryCols = Array(0, 1, 2) ' category, key, name
    If sName = "brands"   Then mandatoryCols = Array(0, 1)    ' key, name

    i = 1 ' 2行目からチェック開始
    Do
        ' A列が空ならデータの終わりとみなす
        If oSheet.getCellByPosition(0, i).String = "" Then Exit Do
        
        For Each col In mandatoryCols
            If oSheet.getCellByPosition(col, i).String = "" Then
                MsgBox "[" & sName & "] シートの " & (i + 1) & " 行目、" & _
                       Chr(65 + col) & " 列目が空欄です。入力してください。", 16, "入力エラー"
                CheckMandatoryFields = False
                Exit Function
            End If
        Next col
        i = i + 1
        If i > 10000 Then Exit Do ' 無限ループ防止
    Loop
    CheckMandatoryFields = True
End Function
```

    3. **ボタンの配置**:
        - [ツール] > [カスタマイズ] > [ツールバー] タブを開く。
        - カテゴリから [LibreOffice マクロ] > [マイマクロ] > [Standard] > [Module1] を選択。
        - `ExportAllSheetsToCSV` を「割り当てられたコマンド」に追加。
        - 追加した項目を選択し、**右側の「歯車アイコン」または「修正」ボタン**をクリックして「名前の変更」や「アイコンの変更」を行う。（右クリックでも変更可能です）
        - ツールバーの使いやすい位置に配置する。
    4. 1クリックで全てのCSVが `data/` フォルダへ書き出されます。
    4. `npm start` がそれらを検知し、即座にサイトが更新されます。

- **Geminiを使わずに自力で入力する場合**:
    1. 同フォルダの `csv_helper.html` をブラウザで開く。
    2. フォームに必要な情報を入力する。
    3. ボタンを押すと、完璧な CSV 形式の 1 行がコピーされます。
    4. Calc（マスター）の新しい行に貼り付けるか、直接 `products.csv` に追記してください。
- **入力規則の設定**: [データ] > [入力規則] > [入力値の種類] で **「ユーザー定義」** を選択します。これが Google スプレッドシートの「カスタム数式」と同じ機能です。
- **ロックファイル**: `.~lock.products.csv#` は無視してOKです。
- **CSVデータを貼り付ける場合（GitHubやGeminiから）**:
    1. CSV形式のテキストをすべてコピーする。
    2. Calcの **A1セル** を選択して貼り付ける (`Ctrl + V`)。
    3. 表示される「テキストインポート」ダイアログで、以下を設定する。
        - **区切り記号のオプション**: **「コンマ」** のみチェック。
        - **テキストの区切り記号**: **`"` (ダブルクォーテーション)** を選択。
    4. プレビューを確認し、[OK] をクリック。
    5. 貼り付け後、`.ods` 形式で保存する。

---

## 6. Gemini（AI）への依頼テンプレート（最新版）
最も確実な方法は、プロジェクト内の `docs/AI_INSTRUCTIONS.md` の内容をまるごと Gemini に渡すことです。

1. `docs/AI_INSTRUCTIONS.md` をコピーして Gemini に貼る。
2. `npm start` した時にターミナルに表示される「📋 Gemini用許可タグリスト」をコピーして Gemini に貼る。
3. 商品名やURLを渡す。

---

## 7. 開発者向けセットアップ（テストと自動化）
新しいパソコンで作業を始める場合は、まず Node.js をインストールしてから以下を実行：

0.  **Node.jsインストール**: `sudo apt install nodejs npm`
1.  **初期化**: `npm init -y` (package.jsonの作成)
2.  **ツール設置**: `npm install --save-dev jest` (テストツールの導入)
3.  **テスト実行**: `npx jest` (convert.test.jsの実行)
4.  **監視モード**: `node convert.js --watch`

---

## 8. 公開前チェックリスト (Pre-flight Check)
GitHub に push してサイトを公開する前に、以下の項目を必ず確認してください。

### ① データと機能の確認
- **ビルド確認**: ターミナルで `npm run build`（または `npm start`）を実行しエラーがないこと。
- **全商品表示**: 検索バー空、フィルター「すべて」で全商品が表示されるか？ (ODSの商品数と一致するか？)
- **フィルター機能**: 「犬」「猫」「涙やけ」など、すべてのフィルターが正しく機能するか？ 複数選択もOKか？
- **検索機能**: 商品名、ブランド、タグ、説明文、ラベル、特典情報で検索し、正しく絞り込まれるか？ (全角/半角スペース、ひらがな/カタカナ/漢字で試す)
- **検索結果0件**: 該当なしの場合、「NO PRODUCTS FOUND」が表示されるか？
- **価格と最安値表示**:
    - 各ショップボタンに価格が正しく表示されるか？ (例: `Amazon: ¥1,200`)
    - 最も安いショップに「最安値」バッジが正しく表示されるか？
    - 価格未入力の場合、デフォルトテキスト（例: `Amazonで最安値を確認`）になっているか？
- **リンクの動作**:
    - 各ショップボタンをクリックし、正しいページに飛ぶか？
    - リンクが新しいタブで開くか？ (`target="_blank"`)
    - アフィリエイトIDが正しく含まれているか？ (URLをコピーして確認)
    - URLが `#` の場合、商品名で検索結果ページに飛ぶか？
- **画像表示**:
    - すべての商品画像が正しく表示されるか？
    - 画像URLが未設定（`#`）の場合、デフォルト画像が表示されるか？

### ② デザインとレスポンシブ対応
- **PC表示**: レイアウトが崩れていないか？ 画像やテキストがはみ出していないか？
- **モバイル表示**: スマホ実機またはブラウザのデベロッパーツールで確認し、デザインが崩れていないか？
- **ドラッグスクロール**: タグの横スクロールがマウスドラッグでスムーズに動作するか？

### ③ 技術的な健全性
- **ブラウザのコンソールエラー**: `F12` キーでコンソールを開き、赤いエラーメッセージが表示されていないか？
- **`data.js` の確認**: `public/data.js` を開き、最新の更新日時がコメントとして記載されているか？
- **`npm test` の実行**: ターミナルで `npm test` を実行し、すべてのテストがパスするか？

### ④ SEO (検索エンジン最適化)
- **タイトル**: ブラウザのタブに表示されるタイトルが適切か？
- **メタディスクリプション**: `<meta name="description" ...>` の内容が、サイトの概要を的確に表しているか？