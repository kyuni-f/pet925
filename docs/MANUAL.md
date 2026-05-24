# pet925 管理マニュアル

## 1. 運用ワークフロー（黄金のサイクル）
データの更新は、すべての情報を一つのマスターファイルで管理し、一括で書き出すのが効率的です。

1.  **Geminiに依頼**: 商品情報を依頼する。
2.  **マスターへ貼り付け**: `data/pet925_master.ods` 内の該当シート（products/tags/brands/rules/categories）を更新。
3.  **一括CSV出力**: Calcのマクロを使用して、5つのCSVを一気に書き出す。
4.  **ビルドとデプロイ**: ターミナルで `npm run deploy` を実行。
5.  **確認**: 公開されたサイトを開き、**Ctrl + F5**。実行ボタンに「準備完了（◯◯件）」と表示されるのを確認。

> **💡 自動バリデーション**: `npm run deploy` を実行すると、Python が「商品名の重複」「未登録タグ」「必須項目の欠落」を自動でチェックします。エラーがある場合は公開（Git push）を自動的に停止します。
> **💡 キャッシュ回避**: Web Worker を使用しているため、コードの変更が反映されにくい場合があります。反映されない時は迷わず **Ctrl + F5**（強力な再読み込み）を行ってください。

---
## 2. タグマスターの管理方法 (tags.csv)
フィルターボタンの種類や表示名は、`data/tags.csv` で一括管理しています。マスター（.ods）の「タグ一覧」シートを更新し、CSVとして書き出すことでサイトに反映されます。

### tags.csv の列構成
| 列名 | 説明 | 例 |
| :--- | :--- | :--- |
| **category** | フィルターの表示グループ | `animal`, `age`, `pref`, `cond` |
| **key** | `products.csv` の `tags` 列に記入する英単語 | `lamb`, `tear`, `gf` |
| **name** | サイトのボタンに表示される名前 | `ラム肉 (LAMB)` |

### タグ・エイリアス設定 (rules.csv)
特定の言葉が含まれている場合に、自動で正式なタグ（絞り込み用）を付与する「別名リスト」です。

- **判定場所**: 商品名、説明文、およびタグ列のすべてが対象です。
- **設定例**: 
    - `gf,グレインフリー 穀物不使用` -> 商品名にこれらがあれば自動で「GF」タグを付与。
    - `lamb,ラム肉` -> 商品名にこれらがあれば自動で「ラム肉 (LAMB)」に分類。

キーワードは**スペース、カンマ、または読点**で区切って1行にまとめて記述できます。

> **注意**: `グルテンフリー` という言葉での自動判定は廃止されました。

### カテゴリの役割
- **animal**: 種類（犬・猫など。単一選択）
- **age**: 年齢（成犬・シニアなど。単一選択）
- **cond**: こだわり・お悩み（原材料や健康ケアの条件。**複数選択可**）

---

## 3. ブランドエイリアスの管理 (brands.csv)
「Nutro」を「ニュートロ」で検索できるようにする設定は `data/brands.csv` で行います。

**💡 賢い名寄せ機能**:
`products.csv` の `brand` 列に英語名（nutro等）を入力しても、`brands.csv` に登録があれば自動的に正式名称（ニュートロ）に変換してサイトに表示します。また、英語名でも日本語名でも検索にヒットするよう `brand_id` が内部で自動保持されます。

**✅ ベストプラクティス**:
サイト上の表示は `products.csv` に入力した文字がそのまま使われます（例: `Nutro`）。バリデーションエラーを防ぎ、日本語検索を最も安定させるため、`products.csv` のブランド名は、可能な限り `brands.csv` の `key` 列と（大文字小文字を含めて）表記を揃えることを推奨します。

### brands.csv の列構成
- **key**: CSVの `brand` 列に記入している英語名（小文字で判定されます）
- **name**: 日本語での読み方

---

## 4. 注意事項（ここだけは気をつけて！）

### ① ファイル名と場所
- `data/` フォルダ内に `products.csv` や `categories.csv` 等が存在する必要があります。
- `products (1).csv` などの余計なファイルがあれば削除してください。
- **ファイル名の末尾に半角スペースが入らないよう注意してください。**（例：`products.csv ` はNG。プログラムが変更を検知できなくなる原因になります）

### ② CSVの書き出し
- `.~lock.products.csv#` などの一時ファイルは、編集ソフトを閉じれば消えます。
- CSV保存時に「テキスト形式で保存しますか？」と聞かれたら **[はい]** を選んでください。

### ③ A8.netなどの広告コード
- `img` 列には「画像のURL」のみ、`a8` 列には「リンク先のURL」のみを貼り付けてください。
- コードを丸ごと貼り付けると表示が崩れる原因になります。
> **💡 ヒント**: 価格情報は表示されなくなりましたが、CSVにデータを残しておいても動作に影響はありません。

### ④ ビルドエラーの確認
- `npm run deploy` でエラー（❌ 変換失敗）が出た場合は、ターミナルのログを確認して CSV の不備を修正してください。

### ⑤ products.csv が上書きできない場合
1. **LibreOfficeを閉じる**: 保存時に「エラー」が出る場合、Calcがロックファイルを生成しています。Calcを閉じ、フォルダ内の `.~lock.products.csv#` を削除してください。
2. **ファイルを閉じる**: 他のソフトで CSV を開いていると上書きできないことがあります。
3. **権限の確認**: Linuxの権限エラーが出る場合は、ターミナルで `sudo chown $USER:$USER data/products.csv` を実行してください。

---

## 5. Google スプレッドシートでの運用方法
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

## 6. マスターファイルの一元管理（LibreOffice Calc）
- **マルチシート運用**: `pet925_master.ods` 内に `products`, `tags`, `brands`, `rules` の4シートを作成してください。
- **一括出力・バリデーションマクロ**: 
    1. [ツール] > [マクロ] > [マクロを管理] > [LibreOffice Basic] を開く。
    2. 以下の `ExportAllSheetsToCSV` と `CheckMandatoryFields` マクロを登録する。

```basic
Sub ExportAllSheetsToCSV
    Dim oDoc As Object, oSheets As Object, oSheet As Object
    Dim sURL As String, sPath As String
    Dim args(2) As New com.sun.star.beans.PropertyValue
    Dim aParts() As String
    
    oDoc = ThisComponent

    ' ファイルが保存されているか（URLがあるか）チェック
    If (oDoc.URL = "") Then
        MsgBox "エラー: ファイルが保存されていません。" & Chr(13) & _
               "先に一度ファイルを保存してから実行してください。", 16, "実行失敗"
        Exit Sub
    End If

    ' パス取得（InStrRevのエラーを避けるため、URLを分割して再結合する安全な方式を採用）
    aParts = Split(oDoc.URL, "/")
    aParts(UBound(aParts)) = ""
    sPath = Join(aParts, "/")

    oSheets = oDoc.Sheets
    
    ' CSV出力の設定
    args(0).Name = "Overwrite"
    args(0).Value = True
    args(1).Name = "FilterName"
    args(1).Value = "Text - txt - csv (StarCalc)"
    args(2).Name = "FilterOptions"
    args(2).Value = "44,34,76,1,,0,false,true,true" ' カンマ区切り, UTF-8

    Dim i As Long
    For i = 0 To oSheets.Count - 1
        oSheet = oSheets.getByIndex(i)
        sName = oSheet.Name

        ' 書き出し前に必須項目の空欄チェックを実行
        If Not CheckMandatoryFields(oSheet, sName) Then
            MsgBox sName & " シートに不備があるため、書き出しを中断しました。", 48, "エラー"
            Exit Sub
        End If

        If oSheet.IsVisible Then ' 非表示のシートは出力から除外
            oDoc.CurrentController.setActiveSheet(oSheet)
            sURL = sPath & sName & ".csv"
            oDoc.storeToURL(sURL, args)
        End If
    Next i
    
    MsgBox "全てのバリデーションをクリアし、CSVの一括出力が完了しました！", 64, "完了"
End Sub

Function CheckMandatoryFields(oSheet As Object, sName As String) As Boolean
    Dim i As Long, col As Integer
    Dim mandatoryCols As Variant
    Dim sNameLower As String
    
    sNameLower = LCase(sName) ' 小文字に統一

    ' シートごとの必須列（A=0, B=1, C=2...）
    If sNameLower = "products" Then
        mandatoryCols = Array(0, 1, 2) ' name, brand, tags
    ElseIf sNameLower = "tags" Then
        mandatoryCols = Array(0, 1, 2) ' category, key, name
    ElseIf sNameLower = "brands" Then
        mandatoryCols = Array(0, 1)    ' key, name
    ElseIf sNameLower = "categories" Then
        mandatoryCols = Array(0, 1, 2, 3) ' key, jp, en, type
    Else
        mandatoryCols = Array()
    End If

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

'''
''' 7. 高度な自動化：ブランド名の自動同期
''' products シートに入力したブランド名やタグが各マスターにない場合、自動で追加します。
'''
Sub SyncBrandToMaster(oEvent As Object)
    Dim oDoc As Object, oSheets As Object, oTargetSheet As Object
    Dim sValue As String, oCell As Object
    Dim i As Long, bExists As Boolean
    Dim nCol As Integer

    ' セル単体の変更のみ対象
    If Not oEvent.supportsService("com.sun.star.table.Cell") Then Exit Sub

    oDoc = ThisComponent
    oSheets = oDoc.Sheets
    nCol = oEvent.CellAddress.Column

    ' --- B列 (ブランド) の処理 ---
    If nCol = 1 Then
        sValue = Trim(oEvent.String)
        If sValue = "" Or sValue = "brand" Or sValue = "ブランド" Then Exit Sub
        oTargetSheet = oSheets.getByName("brands")
        i = 1 : bExists = False
        Do
            oCell = oTargetSheet.getCellByPosition(0, i) ' Key列
            If oCell.String = "" Then Exit Do
            If LCase(oCell.String) = LCase(sValue) Or LCase(oTargetSheet.getCellByPosition(1, i).String) = LCase(sValue) Then
                bExists = True : Exit Do
            End If
            i = i + 1
        Loop
        If Not bExists Then
            If MsgBox("ブランド '" & sValue & "' は brands シートに未登録です。追加しますか？", 4 + 32, "ブランド自動登録") = 6 Then
                oTargetSheet.getCellByPosition(0, i).String = LCase(sValue)
                oTargetSheet.getCellByPosition(1, i).String = sValue
                MsgBox "brands シートに登録しました。", 64
            End If
        End If

    ' --- C列 (タグ) の処理 ---
    ElseIf nCol = 2 Then
        Dim aTags() As String, sTag As String
        sValue = oEvent.String
        If sValue = "" Or sValue = "tags" Or sValue = "タグ" Then Exit Sub
        ' スペースやカンマで分割
        aTags = Split(Replace(sValue, ",", " "), " ")
        oTargetSheet = oSheets.getByName("tags")
        
        For Each sTag In aTags
            sTag = Trim(sTag)
            If Len(sTag) > 1 Then ' 1文字以下は無視
                i = 1 : bExists = False
                Do
                    oCell = oTargetSheet.getCellByPosition(1, i) ' Key列 (B列)
                    If oCell.String = "" Then Exit Do
                    If LCase(oCell.String) = LCase(sTag) Then
                        bExists = True : Exit Do
                    End If
                    i = i + 1
                Loop
                
                If Not bExists Then
                    If MsgBox("タグ '" & sTag & "' は tags シートに未登録です。追加しますか？", 4 + 32, "タグ自動登録") = 6 Then
                        Dim sCat As String, sDisp As String
                        sCat = InputBox("カテゴリを入力してください (animal, age, cond):", "タグ追加", "cond")
                        If sCat <> "" Then
                            sDisp = InputBox("表示名を入力してください:", "タグ追加", sTag)
                            oTargetSheet.getCellByPosition(0, i).String = sCat ' カテゴリ (A列)
                            oTargetSheet.getCellByPosition(1, i).String = sTag ' キー (B列)
                            oTargetSheet.getCellByPosition(2, i).String = sDisp ' 表示名 (C列)
                        End If
                    End If
                End If
            End If
        Next sTag
    End If
End Sub
```

    3. **ボタンの配置**:
        - [ツール] > [カスタマイズ] > [ツールバー] タブを開く。
        - カテゴリから [LibreOffice マクロ] > [マイマクロ] > [Standard] > [Module1] を選択。
        - `ExportAllSheetsToCSV` を「割り当てられたコマンド」に追加。
        - 追加した項目を選択し、**右側の「歯車アイコン」または「修正」ボタン**をクリックして「名前の変更」や「アイコンの変更」を行う。（右クリックでも変更可能です）
        - ツールバーの使いやすい位置に配置する。
    4. 1クリックで全てのCSVが `data/` フォルダへ書き出されます。
    5. `npm start` がそれらを検知し、即座にサイトが更新されます。

- **Geminiを使わずに自力で入力する場合**:
    1. 同フォルダの `csv_helper.html` をブラウザで開く。
    2. フォームに必要な情報を入力する。
    3. ボタンを押すと、完璧な CSV 形式の 1 行がコピーされます。
    4. Calc（マスター）の新しい行に貼り付けるか、直接 `products.csv` に追記してください。
- **入力規則の設定**: [データ] > [入力規則] > [入力値の種類] で **「ユーザー定義」** を選択します。これが Google スプレッドシートの「カスタム数式」と同じ機能です。
- **ロックファイル**: `.~lock.products.csv#` は無視してOKです。
- **CSVデータを貼り付ける場合（GitHubやGeminiから）**:
    1. CSV形式のテキストをすべてコピーする。

### 💡 Calc内でのデータ連動テクニック
マスターファイル（.ods）の編集を楽にする設定です。
1. **ブランドのドロップダウン**: `brands`シートのキー範囲に名前を付け、`products`シートのブランド列で **[データ] > [入力規則] > [セル範囲]** を設定すると、リストから選択可能になります。
2. **未登録タグのハイライト**: **[条件付き書式]** で `COUNTIF` 関数を使えば、`tags`シートに存在しない単語を `products`シート上で赤く光らせることができます。
3. **自動集計シートの作成**: 新しいシートを作り `=COUNTIF(products.C2:C1000, ".*gf.*")` のような数式を入れれば、現在何件のグレインフリー商品があるかリアルタイムで把握できます。

- **CSVデータを貼り付ける場合（GitHubやGeminiから）**:
    1. CSV形式のテキストをすべてコピーする。
    2. Calcの **A1セル** を選択して貼り付ける (`Ctrl + V`)。
    3. 表示される「テキストインポート」ダイアログで、以下を設定する。
        - **区切り記号のオプション**: **「コンマ」** のみチェック。
        - **テキストの区切り記号**: **`"` (ダブルクォーテーション)** を選択。
    4. プレビューを確認し、[OK] をクリック。
    5. 貼り付け後、`.ods` 形式で保存する。

---

## 7. Gemini（AI）への依頼テンプレート（最新版）
最も確実な方法は、プロジェクト内の `docs/AI_INSTRUCTIONS.md` の内容をまるごと Gemini に渡すことです。

1. `docs/AI_INSTRUCTIONS.md` をコピーして Gemini に貼る。
2. `npm start` した時にターミナルに表示される「📋 Gemini用許可タグリスト」をコピーして Gemini に貼る。
3. 商品名やURLを渡す。

---

## 8. 開発環境のセットアップ
作業環境を構築する場合は、**Node.js** と **Python 3** をインストールしてから以下を実行します：

0.  **Node.jsインストール**: `sudo apt install nodejs npm`
1.  **準備**: `npm install`
2.  **Python環境**: `python3 --version` で Python 3 が入っていることを確認。
3.  **ビルドテスト**: `npm run build` で `product_data.json` が生成されるか確認。
4.  **公開**: `npm run deploy`

---

## 9. 公開前チェックリスト (Pre-flight Check)
GitHub に push してサイトを公開する前に、以下の項目を必ず確認してください。

### ① データと機能の確認
- **ビルド確認**: ターミナルで `npm run build`（または `npm start`）を実行しエラーがないこと。
- **全商品表示**: 実行ボタンに表示される件数が、ODSの商品数と一致するか？
- **フィルター機能**: 「犬」「猫」「涙やけ」など、すべてのフィルターが正しく機能するか？ 複数選択もOKか？
- **Web Worker**: 実行ボタンが「準備完了（XXX件）」となっているか？（これが「データを読み込み中...」のままならエラーです）
- **検索機能**: 「ニュートロ」などの単語で検索し、正しく絞り込まれるか？ (全角/半角スペース、ひらがな/カタカナ/漢字で試す)
- **検索結果0件**: 該当なしの場合、「NO PRODUCTS FOUND」が表示されるか？
- **価格と最安値表示**:
    - （将来用：現在はデータ保持のみ）各ショップボタンが正しく表示され、それぞれのモールへリンクしているか？
- **ショップ横断検索**: 商品URLが未入力（#）の場合でも、ブランド名と商品名から各モールの検索結果へ正しく誘導されるか？
- **リンクの動作**:
    - 各ショップボタンをクリックし、正しいページに飛ぶか？
    - リンクが新しいタブで開くか？ (`target="_blank"`)
    - アフィリエイトIDが正しく含まれているか？ (URLをコピーして確認)
    - URLが `#` の場合、商品名で検索結果ページに飛ぶか？
- **画像表示**:
    - すべての商品画像が正しく表示されるか？
    - 画像が未設定（`#`）や読み込みエラーの場合、軽量な「no image」SVG（外部通信が発生しない仕組み）が表示されるか？

### ② デザインとレスポンシブ対応
- **PC表示**: レイアウトが崩れていないか？ 画像やテキストがはみ出していないか？
- **モバイル表示**: スマホ実機またはブラウザのデベロッパーツールで確認し、デザインが崩れていないか？
- **タイルレイアウト**: タグボタンが画面幅に合わせて適切に折り返されて表示されているか？

### ③ 技術的な健全性
- **ブラウザのコンソールエラー**: `F12` キーでコンソールを開き、赤いエラーメッセージが表示されていないか？
- **`product_data.json` の確認**: ビルド後、このファイルに最新のデータが反映されているか？

### ④ SEO (検索エンジン最適化)
- **タイトル**: ブラウザのタブに表示されるタイトルが適切か？
- **紹介文**: ヘッダーの導入文が正しく表示されているか？

### ⑤ GA4 計測の確認
- **リアルタイム**: 自分で検索した際、GA4 のリアルタイムレポートに `search` イベントが表示されるか？
- **0件ヒット**: 存在しないワードで検索した際、`search_no_results` が計測されるか？

### ⑥ 主なエラーと解決策の例
- **「スプレッドシートの「見出し行」が見つかりません」**: `pet925_master.ods` の `products` シートの1行目または2行目に `name` や `brand` 列があるか確認してください。
- **「products.csv が見つかりません」**: `data/` フォルダに `products.csv` が存在するか、またはマスターファイルからCSVを正しく書き出しているか確認してください。
- **「タグに〇〇個の入力ミスが見つかりました」**: `tags.csv` に定義されていないタグが `products.csv` の `tags` 列に入力されています。許可タグリストを確認し、修正してください。
- **「ブランド〇〇は brands.csv に未登録です」**: `brands.csv` に定義されていないブランド名が `products.csv` の `brand` 列に入力されています。`brands.csv` に追加するか、既存のブランド名に修正してください。
- **「商品名 '◯◯' が重複しています」**: ODS 上で同じ商品名が複数回登録されています。名前をユニークにするか、重複行を削除してください。
- **「Worker data load failed」**: ブラウザが `product_data.json` を見つけられていません。ビルドが成功しているか確認してください。

---

## 10. 商品追加からウェブ公開までの具体的な手順（クイックガイド）

1.  **マスターデータの編集**
    - `data/pet925_master.ods` を開き、「products」シートの末尾に新しい商品情報を追加します。
    - 新しいブランドやタグを使用する場合は、それぞれ「brands」「tags」シートにも登録が必要です。

2.  **CSVの一括出力**
    - Calcのツールバーに配置した「CSV一括出力（ExportAllSheetsToCSV）」ボタンをクリックします。
    - `data/` フォルダ内の各CSVが最新状態に更新されます。

3.  **ローカル環境での最終確認**
    - ターミナルで `npm run build` を実行します。
    - バリデーションエラー（⚠️マーク）が出ていないかチェックします。

4.  **GitHubへのデプロイ（公開実行）**
    - ターミナルで以下のコマンドを実行します：
      ```bash
      npm run deploy
      ```
    - これにより、Pythonによる検品・ビルド・コミット・プッシュが一度に行われます。

5.  **本番サイトの確認**
    - GitHub Actionsの処理が完了するまで（約1〜2分）待ちます。
    - `https://kyuni-f.github.io/pet925/` にアクセスし、**Ctrl + F5** で強力な再読み込みを行い、変更が反映されていることを確認します。