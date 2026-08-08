import csv
import json
import os
import unicodedata
import sys
import re
import datetime
import time
import concurrent.futures
import difflib

from pet_utils import (
    normalize_text,
    get_env_value,
    load_dict_rows,
)



# 設定
DATA_DIR = 'data'  # CSVファイルが格納されているディレクトリ
PRODUCT_CSV = os.path.join(DATA_DIR, 'products.csv')
CAT_CSV = os.path.join(DATA_DIR, 'categories.csv')
TAG_CSV = os.path.join(DATA_DIR, 'tags.csv')
RULE_CSV = os.path.join(DATA_DIR, 'rules.csv')

OUTPUT_JSON = 'product_data.json'
CHUNK_SIZE = 5000  # 1ファイルあたりの最大件数
OUTPUT_MASTER_JS = 'data_master.js'

# サイト上の問い合わせメールリンク難読化用のアドレス読み込み（.envのCONTACT_EMAILのみを使用し、リポジトリには平文で残さない）
def load_contact_config():
    return {"email": get_env_value("CONTACT_EMAIL")}

contact_config = load_contact_config()
CONTACT_EMAIL = contact_config["email"] or "your-email@example.com"

# CSVファイル名と、それがdata_master.jsでどの変数名になるかのマッピング
# products.csv は特別扱いなのでここには含めない
SPECIFIC_MASTER_CSVS = {
    'categories.csv', 'tags.csv', 'rules.csv'
}


# ターミナル出力用の色設定
COLOR_RED = '\033[31m'
COLOR_GREEN = '\033[32m'
COLOR_YELLOW = '\033[33m'
COLOR_CYAN = '\033[36m'
COLOR_BOLD = '\033[1m'
COLOR_RESET = '\033[0m'

validation_errors = []
validation_warnings = []

def process_row_task(line_num, row, tag_keywords, tag_to_cat_index, allowed_tags, tag_lookup_for_suggest):
    """1行分の重い処理を担当するワーカー関数"""
    row_errors = []
    row_warnings = []
    name = row.get('name', '').strip()

    # ヘッダー行そのものがデータとして混入している場合はスキップ
    if name.lower() == 'name' or name == '商品名':
        return None, [], [], None, line_num

    if not name:
        return None, [f"行 {line_num}: 商品名(name)が空です。"], [], None, line_num

    # 16列構成（必須列。17列目のexclude_tagsは任意列のためここには含めない）
    expected_keys = ['name', 'brand', 'tags', 'desc', 'size', 'jan', 'img', 'amz', 'rak', 'yah', 'a8', 'label', 'promo', 'amz_p', 'rak_p', 'yah_p']
    missing_keys = [k for k in expected_keys if k not in row or row[k] is None]
    if missing_keys:
        row_errors.append(f"行 {line_num}: 列が足りません。期待される列: {len(expected_keys)}、検出された列: {len(row)}。欠落: {', '.join(missing_keys)}")

    norm_name = normalize_text(name)
    desc = row.get('desc', '').strip()
    check_text = normalize_text(name + desc)

    # ブランド情報の処理 (直接入力値をIDとしても使用)
    brand_name = row.get('brand', '').strip()
    row['brand'] = brand_name
    row['brand_id'] = normalize_text(brand_name)

    tags = row.get('tags', '').replace(',', ' ').split()
    tags = [normalize_text(t) for t in tags if t]
    for t in tags:
        if t not in allowed_tags:
            row_errors.append(f"行 {line_num}: 未登録タグ '{t}' (商品: {name[:20]}...)")

    # 除外タグの読み込み（tags.csv/rules.csv と同じ英語タグID表記。例: appetite）
    # これに含まれるタグIDは、キーワード一致による自動付与・提案の対象から除外する
    exclude_tags_raw = str(row.get('exclude_tags', '#')).strip()
    excluded_tag_ids = set()
    if exclude_tags_raw and exclude_tags_raw != '#':
        excluded_tag_ids = {normalize_text(t) for t in exclude_tags_raw.replace(',', ' ').split() if t}
        for t in excluded_tag_ids:
            if t not in allowed_tags:
                row_warnings.append(f"行 {line_num}: exclude_tags に未登録タグ '{t}' が指定されています (商品: {name[:20]}...)")

    # 1. rules.csv に基づく自動付与（除外タグは対象外）
    for tag_id, keywords in tag_keywords.items():
        if tag_id not in tags and tag_id not in excluded_tag_ids:
            found_kw = next((kw for kw in keywords if kw in check_text), None)
            if found_kw:
                tags.append(tag_id)

    # 2. タグ名そのものが説明文に含まれている場合の提案 (除外タグ適用後)
    for t_name_norm, t_id in tag_lookup_for_suggest.items():
        if t_id not in tags and t_id not in excluded_tag_ids and t_name_norm in check_text:
            row_warnings.append(f"行 {line_num}: 説明文に '{t_name_norm}' が含まれています。タグ '{t_id}' の付与を検討してください。")

    # 価格の数値形式チェック
    for p_col in ['amz_p', 'rak_p', 'yah_p']:
        p_val = str(row.get(p_col, '0')).strip()
        if p_val and p_val != '0' and p_val != '#':
            if not p_val.isdigit():
                row_errors.append(f"行 {line_num}: 価格 {p_col} は半角数字のみで入力してください（カンマや単位は禁止）: '{p_val}'")

    # リンク/画像URLの簡易形式チェック
    for l_col in ['img', 'amz', 'rak', 'yah', 'a8']:
        # 引用符や空白を徹底的に除去
        l_val = str(row.get(l_col, '#')).strip().strip('"').strip("'")
        
        # 有効な形式: 1. '#' (未設定)  2. 'http'で始まる  3. '['で始まるJSONリスト(imgのみ)
        is_valid = (l_val == '#') or (l_val.startswith('http')) or (l_col == 'img' and l_val.startswith('['))
        
        if not is_valid:
            row_errors.append(f"行 {line_num}: {l_col} のURL形式が正しくありません（httpから開始するか # にしてください）")

    tags.sort(key=lambda t: tag_to_cat_index.get(t, 999))
    row['tags'] = tags
    return row, row_errors, row_warnings, norm_name, line_num

def convert(exit_on_error=True):
    print(f"--- 変換処理を開始します ---")
    start_time = time.perf_counter()
    global validation_errors, validation_warnings
    validation_errors = []
    validation_warnings = []

    # --- 重複チェック用の変数をここで確実に初期化 ---
    seen_names = {}      # 商品名重複チェック用
    seen_jans = {}       # JANコード重複チェック用
    names_by_brand = {}  # 類似商品チェック用

    # 1. カテゴリマスタの読み込み（列名ベースで読み込むため、categories.csvの列順を変更しても壊れない）
    category_master = {}
    category_order = []
    for row in load_dict_rows(CAT_CSV):
        key = (row.get('key') or '').strip()
        if not key:
            continue
        jp = (row.get('jp') or '').strip()
        en = (row.get('en') or '').strip()
        m_type = (row.get('type') or '').strip()
        category_master[key] = {"jp": jp, "en": en, "multi": m_type == 'multi'}
        category_order.append(key)

    # 2. タグマスタの読み込み（列名ベース。tags.csvの列順を変更しても壊れない）
    tag_master = {}
    allowed_tags = set()
    tag_lookup_for_suggest = {} # 提案用：正規化名 -> タグID
    for row in load_dict_rows(TAG_CSV):
        cat = (row.get('category') or '').strip()
        key = (row.get('key') or '').strip()
        name = (row.get('name') or '').strip()
        if not cat or not key:
            continue
        if cat not in category_master:
            validation_errors.append(f"tags.csv 行内: カテゴリ '{cat}' は categories.csv に定義されていません。")
        if cat not in tag_master: tag_master[cat] = {}
        norm_key = normalize_text(key)
        tag_master[cat][norm_key] = name
        allowed_tags.add(norm_key)
        tag_lookup_for_suggest[normalize_text(name)] = norm_key

    # タグのカテゴリ所属マップを作成（ソート用）
    tag_to_cat_index = {}
    for idx, cat_key in enumerate(category_order):
        if cat_key in tag_master:
            for t_key in tag_master[cat_key]:
                tag_to_cat_index[t_key] = idx

    # ビルド時間をバージョンとして記録
    build_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    # 4. 自動ルール（キーワード）の読み込み（列名ベース。rules.csvの列順を変更しても壊れない）
    tag_keywords = {}
    for row in load_dict_rows(RULE_CSV):
        tag = (row.get('tag') or '').strip()
        kw_str = (row.get('keywords') or '').strip()
        if tag and kw_str:
            # カンマやスペースで分割して正規化
            kws = [normalize_text(k) for k in kw_str.replace(',', ' ').split() if k]
            if tag not in tag_keywords: tag_keywords[tag] = []
            tag_keywords[tag].extend(kws)
            allowed_tags.add(normalize_text(tag))

    # 5. 動的に他の未認識マスターCSVを読み込む
    other_masters_data = {}
    if os.path.exists(DATA_DIR):
        for filename in os.listdir(DATA_DIR):
            # 特定のマスター以外のCSVを自動取得
            is_other_csv = filename.endswith('.csv') and filename != 'products.csv' and filename not in SPECIFIC_MASTER_CSVS
            if is_other_csv:
                filepath = os.path.join(DATA_DIR, filename)
                var_name = os.path.splitext(filename)[0]
                var_name = re.sub(r'[^a-zA-Z0-9_]', '_', var_name)
                
                data = load_dict_rows(filepath)
                if data:
                    other_masters_data[var_name] = data
                    print(f"   - 追加マスター検出: {filename} -> const {var_name}")
                else:
                    validation_warnings.append(f"追加マスター '{filename}' は中身が空か、形式が正しくないためスキップされました。")

    # 6. 商品データの読み込みと加工
    if not os.path.exists(PRODUCT_CSV):
        print(f"エラー: {PRODUCT_CSV} が見つかりません。")
        return

    # データの読み込み
    all_rows_input = []
    with open(PRODUCT_CSV, 'r', encoding='utf-8-sig', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader, start=2):
            all_rows_input.append((i, r))

    # 並列処理の実行
    print(f"   - {len(all_rows_input)}件を並列処理中...")
    processed_results = []

     # max_workers を指定することで使用するCPUコア数を制限できます
    # 例: os.cpu_count() // 2 とすれば、パソコンの能力の半分だけを使います
    num_cores = os.cpu_count() or 1
    max_workers = max(1, min(num_cores - 1, 8)) # 1コアをOS用に残し、最大8プロセスで並列化
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_row_task, ln, row, tag_keywords, tag_to_cat_index, allowed_tags, tag_lookup_for_suggest)
                   for ln, row in all_rows_input]
        
        for future in concurrent.futures.as_completed(futures):
            res_row, res_errs, res_warns, norm_name, ln = future.result()
            validation_errors.extend(res_errs)
            validation_warnings.extend(res_warns)
            if res_row:
                processed_results.append((ln, res_row, norm_name))

    # 全プロセス終了後、行番号で並び替えて元の順序を復元
    processed_results.sort(key=lambda x: x[0])
    products = [r[1] for r in processed_results]

    for ln, res_row, norm_name in processed_results:
        # JAN重複チェック (# はスキップ)
        jan_val = str(res_row.get('jan', '#')).strip()
        # 全角を半角に変換し、数字以外を除去
        jan_val = unicodedata.normalize('NFKC', jan_val).replace(" ", "").replace("-", "")
        res_row['jan'] = jan_val

        # 商品名重複チェック用のキー（ブランドID + 空白を除去した名前）
        dup_key = f"{res_row['brand_id']}|{''.join(norm_name.split())}"

        if jan_val != '#':
            if not jan_val.isdigit() or len(jan_val) != 13:
                validation_warnings.append(f"行 {ln}: JANコード '{jan_val}' が標準的な13桁の数字ではありません。画像生成に失敗する可能性があります。")

            if jan_val in seen_jans:
                validation_errors.append(f"行 {ln}: JANコード '{jan_val}' が重複しています。(商品: {res_row['name']} / 既出: 行 {seen_jans[jan_val]})")
            else:
                seen_jans[jan_val] = ln

        # 商品名重複チェック
        brand_id = res_row['brand_id']

        if dup_key in seen_names:
            validation_errors.append(f"行 {ln}: 商品名 '{res_row['name']}' が重複しています。(既出: 行 {seen_names[dup_key]})")
        else:
            # 類似商品チェック（同じブランド内で 95% 以上一致するものがあるか）
            if brand_id not in names_by_brand: names_by_brand[brand_id] = []
            if len(names_by_brand[brand_id]) < 1000: # 10万件規模では、ブランド内の商品数が少ない場合のみ実行
                close_matches = difflib.get_close_matches(norm_name, names_by_brand[brand_id], n=1, cutoff=0.95)
                if close_matches:
                    validation_warnings.append(f"行 {ln}: '{res_row['name']}' は既出の '{close_matches[0]}' と非常に似ています。")
            seen_names[dup_key] = ln
            names_by_brand[brand_id].append(norm_name)
        
        # お気に入り管理用の不変なIDを付与
        # JANがあればJANを使用、なければ名寄せ用キーのパイプをアンダーバーに変えたものを使用
        res_row['id'] = jan_val if jan_val != '#' else dup_key.replace('|', '_')

    # products リストは既に上で作成済み
    # 画像キャッシュ参照処理: images/{jan}.ext を手動で配置しておくと自動的に採用される
    # （画像の取得自体は auto_collect_all.py の役目。ここは純粋なCSV→JSON変換+検証のみを行う）
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
    os.makedirs(cache_dir, exist_ok=True)

    print("   - 画像キャッシュ参照処理...")
    for row in products:
        jan_val = str(row.get('jan', '#')).strip().replace(" ", "").replace("-", "")

        if jan_val != '#' and len(jan_val) == 13 and jan_val.isdigit():
            for ext in ["jpg", "jpeg", "png", "webp", "gif"]:
                test_path = os.path.join(cache_dir, f"{jan_val}.{ext}")
                if os.path.exists(test_path):
                    row['img'] = f"images/{jan_val}.{ext}"
                    break

    if not validation_errors:
        # 7. エラーが一つもない場合のみファイル書き出しを実行
        # 10万件規模に対応するため、ファイルを分割（チャンク化）して保存
        num_chunks = (len(products) + CHUNK_SIZE - 1) // CHUNK_SIZE
        for i in range(num_chunks):
            chunk = products[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]
            chunk_filename = f'product_data_{i}.json'
            with open(chunk_filename, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, ensure_ascii=False, separators=(',', ':'))
        # メインのJSONにはメタデータのみを記述
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump({"total": len(products), "chunks": num_chunks, "version": build_version}, f)

        with open(OUTPUT_MASTER_JS, 'w', encoding='utf-8') as f:
            f.write(f"const siteVersion = '{build_version}';\n")
            f.write(f"const tagMaster = {json.dumps(tag_master, ensure_ascii=False, indent=4)};\n")
            f.write(f"const categoryMaster = {json.dumps(category_master, ensure_ascii=False, indent=4)};\n")
            f.write(f"const tagKeywords = {json.dumps(tag_keywords, ensure_ascii=False, indent=4)};\n")
            # 問い合わせメールアドレスは平文で書き出さず、文字コード配列としてのみ出力する（main.jsのsetupContactMailLinkが実行時に復元）
            f.write(f"const CONTACT_MAIL_CODES = {json.dumps([ord(c) for c in CONTACT_EMAIL])};\n")
            # 動的に読み込んだマスターデータを追記
            for var_name, data in other_masters_data.items():
                f.write(f"const {var_name} = {json.dumps(data, ensure_ascii=False, indent=4)};\n")

    print(f"--- 変換完了 ---")
    if not validation_errors:
        print(f"   - {OUTPUT_JSON} ({len(products)}件)")
        print(f"   - {OUTPUT_MASTER_JS} (マスタ設定)")
    else:
        print(f"   - ファイル出力は中断されました (不備があるため)")

    exec_time = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    print(f"   ⏰ 実行時刻: {exec_time}")
    duration = time.perf_counter() - start_time
    print(f"   - 処理時間: {duration:.2f}秒")

    # 警告（確認を促すだけでデプロイは止めない）を表示
    if validation_warnings:
        print(f"\n{COLOR_CYAN}{COLOR_BOLD}💡 {len(validation_warnings)} 個の確認推奨項目があります:{COLOR_RESET}")
        for warn in validation_warnings[:10]:
            print(f"{COLOR_CYAN}   - {warn}{COLOR_RESET}")
        if len(validation_warnings) > 10: print(f"   ...他 {len(validation_warnings)-10} 件")

    if validation_errors:
        print(f"\n{COLOR_RED}{COLOR_BOLD}⚠️  {len(validation_errors)} 個のデータ不備が見つかりました:{COLOR_RESET}")
        for err in validation_errors[:10]: # 最初の10件を表示
            print(f"{COLOR_RED}   - {err}{COLOR_RESET}")
        if len(validation_errors) > 10: print(f"   ...他 {len(validation_errors)-10} 件")
        # 致命的なミス（商品名空など）がある場合にデプロイを止めるなら以下を有効にする
        if exit_on_error:
            sys.exit(1)
    else:
        print(f"{COLOR_GREEN}{COLOR_BOLD}✅ すべてのデータが正常に処理されました。{COLOR_RESET}")

if __name__ == '__main__':
    if "--watch" in sys.argv:
        print(f"{COLOR_BOLD}👀 監視モードを起動しました。CSVの変更を待機中... (Ctrl+C で終了){COLOR_RESET}")
        try:
            convert(exit_on_error=False) # 初回実行
        except Exception as e:
            print(f"{COLOR_RED}初回ビルド失敗: {e}{COLOR_RESET}")
        
        # 初期状態のファイル時間を記録
        last_mtimes = {}
        if os.path.exists(DATA_DIR):
            for f in os.listdir(DATA_DIR):
                if f.endswith('.csv') and not f.startswith('.'):
                    path = os.path.join(DATA_DIR, f)
                    last_mtimes[path] = os.path.getmtime(path)

        while True:
            try:
                time.sleep(1) # 1秒間隔でチェック
                changed = False
                for f in os.listdir(DATA_DIR):
                    if f.endswith('.csv') and not f.startswith('.'):
                        path = os.path.join(DATA_DIR, f)
                        mtime = os.path.getmtime(path)
                        if path not in last_mtimes or mtime > last_mtimes[path]:
                            last_mtimes[path] = mtime
                            changed = True
                if changed:
                    print(f"\n{COLOR_YELLOW}🔄 変更を検知しました。再ビルドします...{COLOR_RESET}")
                    time.sleep(0.2) # ファイルの書き込み完了を少し待つ
                    convert(exit_on_error=False)
            except KeyboardInterrupt:
                print(f"\n{COLOR_YELLOW}監視モードを終了します。{COLOR_RESET}")
                break
            except Exception as e:
                print(f"{COLOR_RED}監視中にエラーが発生しました: {e}{COLOR_RESET}")
    else:
        try:
            convert()
        except Exception as e:
            print(f"{COLOR_RED}{COLOR_BOLD}❌ 変換失敗: {e}{COLOR_RESET}")
            sys.exit(1)