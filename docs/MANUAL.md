# pet925 管理マニュアル

## 1. 運用ワークフロー（黄金のサイクル）

### A. 効率的なデータ収集（推奨）
1.  **供給源の選択**: 楽天市場の商品ページ、または提携している**ドロップシッピングサイト（TopSeller等）**のカタログから商品を探す。
2.  **画像URL取得**: 
    - 楽天の場合：ブックマークレットを使用して高画質URLを取得。
    - ドロップシッピングの場合：提供されている画像URLを直接コピー。
3.  **マスター反映**: `pet925_master.ods` の `img` 列（G列）に貼り付け。
4.  **仕上げ**: 商品名（A列）、ブランド名（B列）、タグ（C列）を手動で入力または調整。
    - **画像について**: JANコードが入力されている場合、Pythonビルド時に以下の優先順位で自動取得します。
    1. **楽天Product Search API(v2)**（最優先）- 透かし・ロゴなしの公式カタログ画像（`r.r10s.jp`）
    2. **楽天商品価格ナビAPI(従来)** - `RAKUTEN_APP_ID` が必要
    3. **Yahoo!ショッピングAPI** - 一部ショップロゴが入る場合あり
    4. **楽天商品検索API(IchibaItem)** - スコアリングフィルター適用
    5. **推測ショップリスト** - `csv_to_json.py` の `DEFAULT_RAKUTEN_IMAGE_SHOPS` で設定
    6. **Google CSE** - ローカルキャッシュにダウンロード保存
    - いずれも見つからない場合は「No Image」プレースホルダーを表示します。
    - 画像左上の「参考画像」バッジや出典注釈は表示されません（楽天公式カタログ画像のため）。
    - 手動で特定の画像URLを指定したい場合は、`img` 列に直接URLを入力してください（自動取得より優先されます）。


### A-2. JANコードからのCSV自動生成（`jan_list.csv` 運用）
JANコード（バーコード番号）だけが分かっている商品を、楽天・Yahoo!・Gemini の各APIを使って自動的に `products.csv` へ登録する方法です。

#### 手順
1.  **JANコードを記入**: プロジェクト直下の `jan_list.csv` を開き、**1行に1つ**、13桁または14桁のJANコードを記入します（見出し行は不要）。
    ```
    4902418002415
    4902418002439
    ```
2.  **実行**: ターミナルで以下のいずれかを実行します。
    - 推奨（説明文・タグまで全自動）: `npm run collect:all`
    - データ収集のみ（JSON変換は別途行う）: `npm run collect`
3.  **確認**: 処理が終わると `data/products.csv` に新しい行が追加されます。`npm run collect:all` の場合は自動で `csv_to_json.py` も実行されるため、続けて `npm start` や `npm run deploy` を行えます。

#### 内部での自動処理（`auto_collect_all.py`）
1. **楽天Product Search API (v2)** で商品名・メーカー名・説明文・価格・画像を一括取得。
2. 上記が失敗した場合は **楽天Item Search API** → **Yahoo!ショッピングAPI** の順にフォールバック。
3. 説明文が取得できない場合、`.env` に `GEMINI_API_KEY` が設定されていれば **Gemini API** が60字程度の説明文を自動生成。
4. `data/rules.csv` のキーワードルールに基づき、タグ（動物種・年齢・こだわり等）を自動判定。
5. `data/brands.csv` を参照してブランド名を正式表記に変換。
6. 完成した行を既存の `products.csv` に追記し、JANコード順に並び替えて保存。

#### ⚠️ 追加方式であることに関する重要ポイント
- **`jan_list.csv`**: 使い切りの「今回処理したいJANコードの入力リスト」です。実行後は自動でクリアされないため、**次回は新しいJANコードだけに書き換えてから実行してください**（前回分が残っていても、既存JANは自動でスキップされるので害はありませんが、処理時間が無駄になります）。
- **`data/products.csv`**: 既存のデータは消えず、**新規JANコードのみが追加**されます。同じJANコードが `jan_list.csv` に含まれていても「⏭️ 重複スキップ」と表示され、二重登録は起きません。
- 自動生成された説明文・タグ・ブランド名は完璧とは限らないため、`pet925_master.ods` を開いて内容を必ず目視確認・修正してください。

---
### B. 手動一括管理（メンテナンス時）

（略）
1.  **マスター更新**: `data/pet925_master.ods` を編集。
2.  **CSV出力**: ツールバーの「CSV一括出力」ボタン（マクロ）をクリック。
3.  **公開**: ターミナルで `npm run deploy` を実行。
4.  **確認**: サイト上で **Ctrl + F5**。

> **💡 開発中の自動ビルド**: `npm start` を実行すると、CSVの変更を自動で検知して JSON を再生成します。ブラウザは IndexedDB にデータをキャッシュしているため、最新のデータを反映させるには **Ctrl + F5**（キャッシュ破棄）が必要です。
> **💡 バリデーション**: `npm run deploy` を実行すると、公開前にデータに不備がないか厳格にチェックします。

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

### 自動タグ付与の除外設定 (`products.csv` の `exclude_tags` 列)
`rules.csv` によるキーワード自動判定は便利な反面、意図しないタグが付いてしまう場合があります。特定の商品だけ自動付与を止めたいタグがある場合は、`products.csv` の **17列目 `exclude_tags`** にそのタグの `key`（`tags`列と同じ英単語表記、複数指定は半角スペース区切り）を入力してください。指定したタグは、キーワード一致による自動付与・付与提案の両方から除外されます。通常は使わない列なので、不要な場合は空欄または `#` のままで構いません。

### カテゴリの役割
- **animal**: 種類（犬・猫など。単一選択）
- **age**: 年齢（成犬・シニアなど。単一選択）
- **cond**: こだわり・お悩み（原材料や健康ケアの条件。**複数選択可**）

---
## 3. ブランドエイリアスの管理 (brands.csv)
「Nutro」を「ニュートロ」で検索できるようにする設定は `data/brands.csv` で行います。

**💡 賢い名寄せ機能**:
`products.csv` の `brand` 列に英語名（nutro等）を入力しても、`brands.csv` に登録があれば自動的に正式名称（ニュートロ）に変換してサイトに表示します。また、英語名でも日本語名でも検索にヒットするよう `brand_id` が内部で自動保持されます。

**💡 ブランド名（Key）がわからない時は？**:
- **海外ブランド**: Gemini に「公式の英語スペルを教えて」と聞く。
- **国内ブランド**: 読み方をローマ字にする（例: `uchinogohan`）。
- **どうしても不明**: 日本語のまま登録しても動作はします（半角英数の方が将来的に安全です）。

**✅ ベストプラクティス**:
サイト上の表示は `products.csv` に入力した文字がそのまま使われます（例: `Nutro`）。バリデーションエラーを防ぎ、日本語検索を最も安定させるため、`products.csv` のブランド名は、可能な限り `brands.csv` の `key` 列と（大文字小文字を含めて）表記を揃えることを推奨します。

### brands.csv の列構成
- **key**: CSVの `brand` 列に記入している英語名（小文字で判定されます）
- **name**: 日本語での読み方

**💡 楽天ショップID（英数字）の見つけ方**:
楽天市場の店舗ページを開いた際のURL `https://www.rakuten.co.jp/○○○/` の **○○○** の部分がショップIDです。これを `main.js` の `rakutenImageShop` に設定します。
※日本語で入力するとURLが「%E6%AD...」と化け、画像が表示されません。

---
## 4. 価格・リンクの管理
*   **価格**: 現在サイト上では非表示ですが、将来の機能拡張のため CSV (`amz_p`, `rak_p`, `yah_p`) には半角数字で保持し続けてください。
*   **リンク**: URLが不明な場合は `#` を入力。システムが商品名から自動検索リンクを生成します。

---
## 5. カスタムドメインの導入手順
詳細は `README.md` の「🌐 カスタムドメインの導入手順」セクションを参照してください。

> **注意**: ドメイン変更直後は、お気に入りデータ（localStorage）がリセットされます。旧ドメインと新ドメインはブラウザから見て「別の場所」と判断されるためです。
 
## 6. 注意事項（ここだけは気をつけて！）

### ① ファイル名と場所
- `data/` フォルダ内に `products.csv` や `categories.csv` 等が存在する必要があります。
- `products (1).csv` などの余計なファイルがあれば削除してください。
- **ファイル名の末尾に半角スペースが入らないよう注意してください。**（例：`products.csv ` はNG。プログラムが変更を検知できなくなる原因になります）

### ② CSVの書き出し
- `.~lock.products.csv#` などの一時ファイルは、編集ソフトを閉じれば消えます。
- CSV保存時に「テキスト形式で保存しますか？」と聞かれたら **[はい]** を選んでください。

### ③ 広告コードとリンク (img, amz, rak, yah, a8)
- `img` 列には「画像のURL」のみ、`amz`, `rak`, `yah`, `a8` 列には「リンク先のURL」のみを貼り付けてください。
- コードを丸ごと貼り付けると表示が崩れる原因になります。
> **💡 ヒント**: 価格情報は表示されなくなりましたが、CSVにデータを残しておいても動作に影響はありません。

**💡 画像URLの自動取得について**:
1. JANコードが13桁で正しく入力されていれば、ビルド時に楽天Product Search API(v2)が自動的に高品質なカタログ画像（`r.r10s.jp`）を取得します。
2. この画像は**ショップロゴや透かしが入っていない**クリーンな商品画像です。
3. 自動取得が失敗する場合は、ブックマークレットを使って `img` 列にURLを直接貼り付けてください。

**⚖️ 画像利用に関するガイドライン**:
- 楽天Product Search APIを経由して取得した画像は、楽天のAPI利用規約の範囲内での適法な利用です。
- 商品紹介（引用）の目的で使用し、各商品カードに出典元（楽天市場）へのリンクを併記しています。
- 直リンク方式（自サーバーへの複製・再配信なし）を採用し、著作権者の配信管理権を尊重しています。
- 現在、Amazon、楽天、Yahoo!ショッピングとのアフィリエイト提携は停止中です。

### ④ ビルドエラーの確認
- `npm run deploy` でエラー（❌ 変換失敗）が出た場合は、ターミナルのログを確認して CSV の不備を修正してください。
- **警告（💡マーク）の確認**: `npm run deploy` 時に警告（💡マーク）が表示される場合があります。これはデプロイを停止しませんが、データ品質向上のための提案です。内容を確認し、必要に応じて修正してください。

### ⑤ products.csv が上書きできない場合
1. **LibreOfficeを閉じる**: 保存時に「エラー」が出る場合、Calcがロックファイルを生成しています。Calcを閉じ、フォルダ内の `.~lock.products.csv#` を削除してください。
2. **ファイルを閉じる**: 他のソフトで CSV を開いていると上書きできないことがあります。
3. **権限の確認**: Linuxの権限エラーが出る場合は、ターミナルで `sudo chown $USER:$USER data/products.csv` を実行してください。

---
## 7. プライバシーポリシー・免責事項について
- サイト下部の「プライバシーポリシー・免責事項」リンクをクリックすると表示されるモーダルの内容は、`index.html` に直接記述されています。
- アフィリエイト提携状況や免責事項に変更があった場合は、`index.html` の該当箇所を直接編集してください。

---
## 8. AI (Gemini) 連携の設定と依頼方法

### A. API キーの設定
1. Google AI Studio で **「Get API key」** を作成。
2. プロジェクト直下の **`.env`** ファイルに `GEMINI_API_KEY=AIza...` を保存。

### B. 商品データの作成依頼
商品データを AI に作成させる際は、**`docs/AI_INSTRUCTIONS.md`** の内容をそのままプロンプトとして渡してください。これにより、16列のCSV形式とタグの整合性が保たれます。

---

## 9. コメントの追加（comments.csv）
商品に対するコメントを管理するための `comments.csv` ファイルを追加しました。このファイルは、商品に関する補足情報やレビューなどを記述するために使用されます。

### comments.csv の列構成
| 列名       | 説明                   | 例                  |
| :--------- | :--------------------- | :------------------ |
| **product_id** | 商品を一意に識別するID | `brand_name-item_name` |
| **author**     | コメント投稿者         | `kyuni`             |
| **comment**    | コメントの内容         | `この商品はおすすめです。` |

---

## 10. マスターファイルの一元管理（LibreOffice / Sheets）
- **マルチシート運用**: `pet925_master.ods` 内に `products`, `tags`, `brands`, `rules`, `categories` の5シートを作成してください。
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

    ' 変更が保存されていない場合は警告
    If oDoc.isModified Then
        If MsgBox("ファイルに変更があります。保存してから実行しますか？", 4 + 32, "確認") = 6 Then oDoc.store()
    End If

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
    
    ' 必要なシートが存在するか一括チェック
    Dim requiredSheets As Variant, sNameCheck As String
    requiredSheets = Array("products", "tags", "brands", "categories", "rules")
    For Each sNameCheck In requiredSheets
        If Not oSheets.hasByName(sNameCheck) Then
            MsgBox "エラー: シート '" & sNameCheck & "' が見つかりません。", 16, "実行失敗"
            Exit Sub
        End If
    Next sNameCheck

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

'''
''' 現在表示しているシートのみをCSV出力する（高速版）
'''
Sub ExportCurrentSheetOnly
    Dim oDoc As Object, oSheet As Object
    Dim sURL As String, sPath As String
    Dim args(2) As New com.sun.star.beans.PropertyValue
    Dim aParts() As String

    oDoc = ThisComponent
    oSheet = oDoc.CurrentController.ActiveSheet
    
    If Not CheckMandatoryFields(oSheet, oSheet.Name) Then Exit Sub

    aParts = Split(oDoc.URL, "/")
    aParts(UBound(aParts)) = ""
    sPath = Join(aParts, "/")

    args(0).Name = "Overwrite" : args(0).Value = True
    args(1).Name = "FilterName" : args(1).Value = "Text - txt - csv (StarCalc)"
    args(2).Name = "FilterOptions" : args(2).Value = "44,34,76,1,,0,false,true,true"

    sURL = sPath & oSheet.Name & ".csv"
    oDoc.storeToURL(sURL, args)

    MsgBox "[" & oSheet.Name & ".csv] のみ出力しました。", 64, "完了"
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
''' products シートの変更を検知し、未登録のブランドやタグを brands/tags シートへ自動追加を促すマクロ。
''' 一括貼り付け（Range）にも対応し、エラー耐性を高めた改良版。
'''
Sub SyncBrandToMaster(oEvent As Object)
    On Error GoTo ErrorHandler ' エラーが発生しても異常終了させない
    
    Dim oDoc As Object, oSheets As Object, oSheet As Object, oTargetSheet As Object
    Dim startRow As Long, endRow As Long, startCol As Long, endCol As Long
    Dim iRow As Long, i As Long, bExists As Boolean
    Dim sValue As String, oCell As Object, oCellName As Object

    ' 1回の貼り付けで何度も聞かないための記憶リスト
    Static sProcessedBrands As String
    Static sProcessedTags As String

    oDoc = ThisComponent
    oSheets = oDoc.Sheets

    ' イベントの発生した範囲を特定
    If oEvent.supportsService("com.sun.star.sheet.SheetCell") Then
        startRow = oEvent.CellAddress.Row : endRow = startRow
        startCol = oEvent.CellAddress.Column : endCol = startCol
        oSheet = oSheets.getByIndex(oEvent.CellAddress.Sheet)
    ElseIf oEvent.supportsService("com.sun.star.sheet.SheetCellRange") Or _
           oEvent.supportsService("com.sun.star.table.CellRange") Then
        startRow = oEvent.RangeAddress.StartRow : endRow = oEvent.RangeAddress.EndRow
        startCol = oEvent.RangeAddress.StartColumn : endCol = oEvent.RangeAddress.EndColumn
        oSheet = oSheets.getByIndex(oEvent.RangeAddress.Sheet)
    Else
        Exit Sub
    End If

    ' products シート以外は無視
    If oSheet.Name <> "products" Then Exit Sub

    ' 記憶リストの初期化（セッション開始時：1回の貼り付け単位で重複を防ぐ）
    sProcessedBrands = "|" 
    sProcessedTags = "|"

    ' 変更された全行をチェック
    For iRow = startRow To endRow
        If iRow = 0 Then GoTo NextRow ' ヘッダーはスキップ

        ' --- B列 (ブランド / Index 1) が変更範囲に含まれているか ---
        If startCol <= 1 And endCol >= 1 Then
            sValue = Trim(oSheet.getCellByPosition(1, iRow).String)
            ' 既知のキーワードや空欄を除外
            If sValue <> "" And sValue <> "brand" And sValue <> "ブランド" And sValue <> "#" And InStr(sProcessedBrands, "|" & sValue & "|") = 0 Then
                oTargetSheet = oSheets.getByName("brands")
                bExists = False
                i = 1 ' 2行目から検索
                
                ' brandsシートを最大5000行までスキャン（空行があっても飛ばさない）
                Do While i < 5000
                    oCell = oTargetSheet.getCellByPosition(0, i) ' Key列
                    oCellName = oTargetSheet.getCellByPosition(1, i) ' Name列
                    
                    ' 完全一致チェック
                    If LCase(Trim(oCell.String)) = LCase(sValue) Or LCase(Trim(oCellName.String)) = LCase(sValue) Then
                        bExists = True
                        Exit Do
                    End If
                    
                    ' 両方の列が空ならそこがデータの末尾
                    If oCell.String = "" And oCellName.String = "" Then Exit Do
                    i = i + 1
                Loop

                If Not bExists Then
                    If MsgBox("新ブランド '" & sValue & "' を brands シートに登録しますか？", 4 + 32, "クイック追加") = 6 Then
                        Dim sKey As String, sBrandName As String
                        sKey = LCase(InputBox("システム用ID (半角英数):", "1/2 ステップ", sValue))
                        If sKey <> "" Then
                            sBrandName = InputBox("サイトでの表示名:", "2/2 ステップ", sValue)
                            oTargetSheet.getCellByPosition(0, i).String = sKey
                            oTargetSheet.getCellByPosition(1, i).String = sBrandName
                        End If
                    End If
                    sProcessedBrands = sProcessedBrands & sValue & "|"
                End If
            End If
        End If

        ' --- C列 (タグ / Index 2) が変更範囲に含まれているか ---
        If startCol <= 2 And endCol >= 2 Then
            sValue = Trim(oSheet.getCellByPosition(2, iRow).String)
            If sValue <> "" And sValue <> "tags" And sValue <> "タグ" Then
                Dim aTags() As String, sTag As String
                aTags = Split(Replace(Replace(sValue, ",", " "), "　", " "), " ")
                oTargetSheet = oSheets.getByName("tags")
                For Each sTag In aTags
                    sTag = Trim(sTag)
                    If Len(sTag) > 1 And InStr(sProcessedTags, "|" & sTag & "|") = 0 Then
                        bExists = False
                        i = 1
                        Do While i < 5000
                            oCell = oTargetSheet.getCellByPosition(1, i) ' Key列
                            If LCase(Trim(oCell.String)) = LCase(sTag) Then
                                bExists = True
                                Exit Do
                            End If
                            If oCell.String = "" And oTargetSheet.getCellByPosition(0, i).String = "" Then Exit Do
                            i = i + 1
                        Loop
                        If Not bExists Then
                            ' カテゴリ入力を省き、デフォルトで 'cond'（こだわり・お悩み）として追加
                            If MsgBox("新タグ '" & sTag & "' を tags シートに追加しますか？", 4 + 32, "タグクイック追加") = 6 Then
                                Dim sDisp As String
                                sDisp = InputBox("サイトでの表示名:", "タグ追加", sTag)
                                oTargetSheet.getCellByPosition(0, i).String = "cond"
                                oTargetSheet.getCellByPosition(1, i).String = sTag
                                oTargetSheet.getCellByPosition(2, i).String = sDisp
                            End If
                            sProcessedTags = sProcessedTags & sTag & "|"
                        End If
                    End If
                Next sTag
            End If
        End If
NextRow:
    Next iRow
    Exit Sub

ErrorHandler:
    ' エラーが起きた場合は無視して次へ（一括貼り付け時のクラッシュ防止）
    Resume Next
End Sub
```

    3. ボタンの配置**:
        - [ツール] > [カスタマイズ] > [ツールバー] タブを開く。
        - カテゴリから [LibreOffice マクロ] > [マイマクロ] > [Standard] > [Module1] を選択。
        - `ExportAllSheetsToCSV` を「割り当てられたコマンド」に追加。
        - 追加した項目を選択し、**右側の「歯車アイコン」または「修正」ボタン**をクリックして「名前の変更」や「アイコンの変更」を行う。（右クリックでも変更可能です）
        - ツールバーの使いやすい位置に配置する。
    4. 1クリックで全てのCSVが `data/` フォルダへ書き出されます。
    5. `npm start` がそれらを検知し、即座にサイトが更新されます。

### 💡 Google スプレッドシートでの運用
1. **ダウンロード**: [ファイル] > [ダウンロード] > [CSV] を選択し、`data/` 内の各ファイルへ上書きします。
2. **AIデータの貼り付け**: コピーしたCSVを貼り付けた後、右下のアイコンから「テキストを列に分割」を選択してください。

### 💡 Calc (LibreOffice) のテクニック
1. **入力補助**: `csv_helper.html` を使うと、正確なCSV行を生成できます。
2. **データ連動**: `brands`シートのキー範囲に名前を付け、`products`シートのブランド列で「入力規則」を設定すると、リストから選択可能になります。
3. **自動集計**: `=COUNTIF(products.C2:C1000, ".*gf.*")` で特定のタグの件数をリアルタイム把握できます。

### 💡 CSVデータのインポート
    1. CSV形式のテキストをすべてコピーする。
    2. Calcの **A1セル** を選択して貼り付ける (`Ctrl + V`)。
    3. 表示される「テキストインポート」ダイアログで、以下を設定する。
        - **区切り記号のオプション**: **「コンマ」** のみチェック。
        - **テキストの区切り記号**: **`"` (ダブルクォーテーション)** を選択。
    4. プレビューを確認し、[OK] をクリック。
    5. 貼り付け後、`.ods` 形式で保存する。

---
## 10. 開発環境のセットアップ
Node.js と Python 3 が必要です。

0.  **Node.jsインストール**: `sudo apt install nodejs npm`
1.  **Python環境**: `python3 --version` で Python 3 が入っていることを確認。
2.  **ライブラリインストール**: 以下のいずれかを実行してください。
    - 推奨（システム全体）: `sudo apt install python3-requests`
    - 推奨（仮想環境）: `python3 -m venv venv && source venv/bin/activate && pip install requests`
    - 強制実行（非推奨）: `pip install requests --break-system-packages`
2.  **ビルドテスト**: `npm run build` で `product_data.json` が生成されるか確認。
3.  **公開**: `npm run deploy`

---

## 11. 公開前チェックリスト (Pre-flight Check)
GitHub に push してサイトを公開する前に、以下の項目を必ず確認してください。

### ① データと機能の確認
- **ビルド確認**: ターミナルで `npm run build`（または `npm start`）を実行しエラーがないこと。
- **全商品表示**: 実行ボタンに表示される件数が、ODSの商品数と一致するか？
- **フィルター機能**: 「犬」「猫」「涙やけ」など、すべてのフィルターが正しく機能するか？ 複数選択もOKか？
- **Web Worker**: 実行ボタンが「準備完了（XXX件）」となっているか？（これが「データを読み込み中...」のままならエラーです）
- **検索機能**: 「ニュートロ」などの単語で検索し、正しく絞り込まれるか？ (全角/半角スペース、ひらがな/カタカナ/漢字で試す)
- **検索結果0件**: 該当なしの場合、「NO PRODUCTS FOUND」が表示されるか？
- **お気に入り機能**:
    - 商品カードのハートアイコンをクリックすると登録・解除できるか？
    - 「お気に入り」ボタンで絞り込み、件数が正しく表示されるか？
    - 「CLEAR ❤ ×」ボタンで一括解除できるか？（カスタムモーダルが表示されるか？）
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
- **コンソール警告**: `F12` キーでコンソールを開いた際に「STOP!」という警告メッセージが表示されるか？

### ④ SEO (検索エンジン最適化)
- **タイトル**: ブラウザのタブに表示されるタイトルが適切か？
- **紹介文**: ヘッダーの導入文が正しく表示されているか？

## 12. トラブルシューティング
- **「スプレッドシートの「見出し行」が見つかりません」**: `pet925_master.ods` の `products` シートの1行目または2行目に `name` や `brand` 列があるか確認してください。
- **「products.csv が見つかりません」**: `data/` フォルダに `products.csv` が存在するか、またはマスターファイルからCSVを正しく書き出しているか確認してください。
- **「タグに〇〇個の入力ミスが見つかりました」**: `tags.csv` に定義されていないタグが `products.csv` の `tags` 列に入力されています。許可タグリストを確認し、修正してください。
- **「ブランド '〇〇' は brands.csv に未登録です」**: `brands.csv` に定義されていないブランド名が `products.csv` の `brand` 列に入力されています。`brands.csv` に追加するか、既存のブランド名に修正してください。
- **「商品名 '◯◯' が重複しています」**: ODS 上で同じ商品名が複数回登録されています。名前をユニークにするか、重複行を削除してください。
- **「Worker data load failed」**: ブラウザが `product_data.json` を見つけられていません。ビルドが成功しているか確認してください。
- **「GA4で30分間のデータ（リアルタイム）しか見えない」**: 標準レポートへの反映には24-48時間の遅延があります。また、詳細な検索ワードを見るには、GA4管理画面の「カスタムディメンション」で `item_label` をカスタムディメンションとして登録する必要があります。

## 13. GA4 の推奨設定
1. **データ保持期間の変更**: 「管理 > データ収集と修正 > データの保持」を **14ヶ月** に変更してください（デフォルトは2ヶ月で、古いデータが消えてしまいます）。
2. **カスタムディメンションの登録**: 「管理 > データ表示 > カスタム定義」から、パラメータ名 `item_label` を登録してください。これにより `search_no_results` 等で送信した具体的な単語がレポートに表示されます。