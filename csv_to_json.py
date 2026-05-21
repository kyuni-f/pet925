import csv
import json
import os
import unicodedata

# 設定
DATA_DIR = 'data'  # CSVファイルが格納されているディレクトリ
PRODUCT_CSV = os.path.join(DATA_DIR, 'products.csv')
CAT_CSV = os.path.join(DATA_DIR, 'categories.csv')
TAG_CSV = os.path.join(DATA_DIR, 'tags.csv')
BRAND_CSV = os.path.join(DATA_DIR, 'brands.csv')
RULE_CSV = os.path.join(DATA_DIR, 'rules.csv')

OUTPUT_JSON = 'product_data.json'
OUTPUT_MASTER_JS = 'data_master.js'

validation_errors = []

def normalize_text(s):
    """JS版のnormalizeと動作を合わせる（NFKC正規化 + ひらがなをカタカナへ）"""
    if not s: return ""
    s = unicodedata.normalize('NFKC', str(s))
    # ひらがな (U+3041-3096) を カタカナ (U+30A1-30F6) に変換 (+0x60)
    chars = []
    for char in s:
        cp = ord(char)
        if 0x3041 <= cp <= 0x3096:
            chars.append(chr(cp + 0x60))
        else:
            chars.append(char)
    return "".join(chars).lower().strip()

def load_csv_simple(path):
    if not os.path.exists(path): return []
    with open(path, 'r', encoding='utf-8-sig') as f:
        return list(csv.reader(f))

def convert():
    print(f"--- 変換処理を開始します ---")
    global validation_errors
    validation_errors = []

    # 1. カテゴリマスタの読み込み
    category_master = {}
    category_order = []
    cat_rows = load_csv_simple(CAT_CSV)
    for row in cat_rows:
        if len(row) < 4 or row[0].lower() in ['key', 'キー']: continue
        key, jp, en, m_type = [s.strip() for s in row[:4]]
        category_master[key] = {"jp": jp, "en": en, "multi": m_type == 'multi'}
        category_order.append(key)

    # 2. タグマスタの読み込み
    tag_master = {}
    allowed_tags = set()
    tag_rows = load_csv_simple(TAG_CSV)
    for row in tag_rows:
        if len(row) < 3 or row[0].lower() in ['category', 'カテゴリ']: continue
        cat, key, name = [s.strip() for s in row[:3]]
        if cat not in tag_master: tag_master[cat] = {}
        norm_key = normalize_text(key)
        tag_master[cat][norm_key] = name
        allowed_tags.add(norm_key)

    # タグのカテゴリ所属マップを作成（ソート用）
    tag_to_cat_index = {}
    for idx, cat_key in enumerate(category_order):
        if cat_key in tag_master:
            for t_key in tag_master[cat_key]:
                tag_to_cat_index[t_key] = idx

    # 3. ブランドマスタの読み込み
    brand_master = {}
    brand_rows = load_csv_simple(BRAND_CSV)
    for row in brand_rows:
        if len(row) < 2 or row[0].lower() in ['key', 'キー']: continue
        key, name = [s.strip() for s in row[:2]]
        brand_master[normalize_text(key)] = name

    # 4. 自動ルール（キーワード）の読み込み
    tag_keywords = {}
    rule_rows = load_csv_simple(RULE_CSV)
    for row in rule_rows:
        if len(row) < 2 or row[0].lower() in ['tag', 'タグ']: continue
        tag, kw_str = row[0].strip(), row[1].strip()
        if tag and kw_str:
            # カンマやスペースで分割して正規化
            kws = [normalize_text(k) for k in kw_str.replace(',', ' ').split() if k]
            if tag not in tag_keywords: tag_keywords[tag] = []
            tag_keywords[tag].extend(kws)
            allowed_tags.add(normalize_text(tag))

    # 5. 商品データの読み込みと加工
    products = []
    if not os.path.exists(PRODUCT_CSV):
        print(f"エラー: {PRODUCT_CSV} が見つかりません。")
        return

    with open(PRODUCT_CSV, 'r', encoding='utf-8-sig', errors='replace') as f:
        reader = csv.DictReader(f)
        for line_num, row in enumerate(reader, start=2):
            name = row.get('name', '').strip()
            if not name:
                validation_errors.append(f"行 {line_num}: 商品名(name)が空です。")
                continue

            desc = row.get('desc', '').strip()
            check_text = normalize_text(name + desc)

            # ブランド情報の処理
            brand_val = row.get('brand', '').strip()
            if brand_val:
                # CSVにブランド名がある場合は、そこからIDを生成
                row['brand_id'] = normalize_text(brand_val)
            else:
                # 空の場合は名前や説明文からマスタを検索して自動判定
                for b_id, b_name in brand_master.items():
                    if b_id in check_text or normalize_text(b_name) in check_text:
                        row['brand_id'] = b_id
                        row['brand'] = b_name
                        break
            if 'brand_id' not in row: row['brand_id'] = ""
            if row['brand_id'] and row['brand_id'] not in brand_master:
                validation_errors.append(f"行 {line_num}: ブランド '{row['brand']}' は brands.csv に未登録です。")

            # タグの処理
            tags = row.get('tags', '').replace(',', ' ').split()
            tags = [normalize_text(t) for t in tags if t]

            # 未登録タグのチェック
            for t in tags:
                if t not in allowed_tags:
                    validation_errors.append(f"行 {line_num}: 未登録タグ '{t}' (商品: {name[:20]}...)")

            # 自動タグ付けルールの適用
            for tag_id, keywords in tag_keywords.items():
                if tag_id not in tags:
                    if any(kw in check_text for kw in keywords):
                        tags.append(tag_id)
            
            # タグをカテゴリ順に並べ替え（index.htmlでの表示を綺麗にするため）
            tags.sort(key=lambda t: tag_to_cat_index.get(t, 999))

            row['tags'] = tags
            products.append(row)

    # 6. ファイル書き出し
    # product_data.json
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=4)

    # data_master.js (JavaScript変数として書き出し)
    with open(OUTPUT_MASTER_JS, 'w', encoding='utf-8') as f:
        f.write(f"const tagMaster = {json.dumps(tag_master, ensure_ascii=False, indent=4)};\n")
        f.write(f"const categoryMaster = {json.dumps(category_master, ensure_ascii=False, indent=4)};\n")
        f.write(f"const brandMaster = {json.dumps(brand_master, ensure_ascii=False, indent=4)};\n")
        f.write(f"const tagKeywords = {json.dumps(tag_keywords, ensure_ascii=False, indent=4)};\n")

    print(f"--- 変換完了 ---")
    print(f"   - {OUTPUT_JSON} ({len(products)}件)")
    print(f"   - {OUTPUT_MASTER_JS} (マスタ設定)")

    if validation_errors:
        print(f"\n⚠️  {len(validation_errors)} 個のデータ不備が見つかりました:")
        for err in validation_errors[:10]: # 最初の10件を表示
            print(f"   - {err}")
        if len(validation_errors) > 10: print(f"   ...他 {len(validation_errors)-10} 件")
    else:
        print(f"✅ すべてのデータが正常に処理されました。")

if __name__ == '__main__':
    try:
        convert()
    except Exception as e:
        print(f"❌ 変換失敗: {e}")