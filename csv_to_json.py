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
    
    # 1. カテゴリマスタの読み込み
    category_master = {}
    cat_rows = load_csv_simple(CAT_CSV)
    for row in cat_rows:
        if len(row) < 4 or row[0].lower() in ['key', 'キー']: continue
        key, jp, en, m_type = [s.strip() for s in row[:4]]
        category_master[key] = {"jp": jp, "en": en, "multi": m_type == 'multi'}

    # 2. タグマスタの読み込み
    tag_master = {}
    tag_rows = load_csv_simple(TAG_CSV)
    for row in tag_rows:
        if len(row) < 3 or row[0].lower() in ['category', 'カテゴリ']: continue
        cat, key, name = [s.strip() for s in row[:3]]
        if cat not in tag_master: tag_master[cat] = {}
        tag_master[cat][normalize_text(key)] = name

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

    # 5. 商品データの読み込みと加工
    products = []
    if not os.path.exists(PRODUCT_CSV):
        print(f"エラー: {PRODUCT_CSV} が見つかりません。")
        return

    with open(PRODUCT_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('name', '').strip()
            desc = row.get('desc', '').strip()
            check_text = normalize_text(name + desc)

            # ブランドの自動判定
            if not row.get('brand'):
                for b_id, b_name in brand_master.items():
                    if b_id in check_text or normalize_text(b_name) in check_text:
                        row['brand'] = b_name
                        break
            
            # タグの処理
            tags = row.get('tags', '').replace(',', ' ').split()
            tags = [normalize_text(t) for t in tags if t]

            # 自動タグ付けルールの適用
            for tag_id, keywords in tag_keywords.items():
                if tag_id not in tags:
                    if any(kw in check_text for kw in keywords):
                        tags.append(tag_id)
            
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

    print(f"✅ 完了:")
    print(f"   - {OUTPUT_JSON} ({len(products)}件)")
    print(f"   - {OUTPUT_MASTER_JS} (マスタ設定)")
    print(f"   (ソースCSV: {DATA_DIR} フォルダ内)")

if __name__ == '__main__':
    try:
        convert()
    except Exception as e:
        print(f"❌ 変換失敗: {e}")