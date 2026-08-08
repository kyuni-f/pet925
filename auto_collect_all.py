#!/usr/bin/env python3
"""
JANコードリストから全自動で products.csv 行を生成する統合スクリプト。

使い方:
  python3 auto_collect_all.py jan_list.csv

ワークフロー:
  1. Product Search API v2 → 商品名・画像・メーカー名・説明文・価格を一発取得
  2. 取得できなければ Item Search API にフォールバック
  3. 説明文が空なら Gemini API で自動生成
  4. rules.csv ベースでタグを自動判定
  5. products.csv に追記

注意:
  GEMINI_API_KEY が .env に設定されている場合、説明文の自動生成が有効になります。
  設定がない場合でも、楽天APIから取得できる情報だけで products.csv は完成します。
"""

import csv
import os
import sys
import time
import re
import json
import unicodedata
import random
import requests
from io import StringIO

# ─────────────────────────────────────────────
# 設定
# ─────────────────────────────────────────────
DATA_DIR = 'data'
PRODUCT_CSV = os.path.join(DATA_DIR, 'products.csv')
BRANDS_CSV = os.path.join(DATA_DIR, 'brands.csv')
TAG_CSV = os.path.join(DATA_DIR, 'tags.csv')
RULE_CSV = os.path.join(DATA_DIR, 'rules.csv')

FIELD_NAMES = ['name', 'brand', 'tags', 'desc', 'size', 'jan', 'img', 'amz', 'rak', 'yah', 'a8', 'label', 'promo', 'amz_p', 'rak_p', 'yah_p']

# 既存JANが見つかった場合でも、この項目だけは自動取得結果で上書き更新する
# （amz/yah/a8/label/promo/size/amz_p/yah_p などの手動編集項目は既存値を保持する）
AUTO_UPDATE_FIELDS = ['name', 'brand', 'tags', 'desc', 'img', 'rak', 'rak_p']

# ─────────────────────────────────────────────
# 設定読み込み
# ─────────────────────────────────────────────
def load_config():
    config = {"RAKUTEN_APP_ID": None, "RAKUTEN_ACCESS_KEY": None, "GEMINI_API_KEY": None, "YAHOO_CLIENT_ID": None}
    # システム環境変数を優先
    for key in config:
        val = os.getenv(key)
        if val:
            config[key] = val
    # .env で補完
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.split('#')[0].strip()
                if not line: continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip(); v = v.strip().strip("'").strip('"')
                    if k in config and not config[k]:
                        config[k] = v
    return config

CONFIG = load_config()
RAKUTEN_APP_ID = CONFIG["RAKUTEN_APP_ID"]
RAKUTEN_ACCESS_KEY = CONFIG["RAKUTEN_ACCESS_KEY"]
GEMINI_API_KEY = CONFIG["GEMINI_API_KEY"]
YAHOO_CLIENT_ID = CONFIG["YAHOO_CLIENT_ID"]

# ─────────────────────────────────────────────
# 正規化ユーティリティ
# ─────────────────────────────────────────────
def normalize_text(s):
    if not s: return ""
    s = unicodedata.normalize('NFKC', str(s))
    chars = []
    for char in s:
        cp = ord(char)
        if 0x3041 <= cp <= 0x3096:
            chars.append(chr(cp + 0x60))
        else:
            chars.append(char)
    s = "".join(chars).lower()
    return re.sub(r'\s+', ' ', s).strip()

def normalize_jan(jan_str):
    jan = str(jan_str).strip().replace(" ", "").replace("-", "")
    if jan.isdigit() and len(jan) == 14:
        return jan[:13]
    return jan

def load_csv_simple(path):
    if not os.path.exists(path): return []
    with open(path, 'r', encoding='utf-8-sig') as f:
        return list(csv.reader(f))

def load_brands_map():
    brands_map = {}
    if os.path.exists(BRANDS_CSV):
        with open(BRANDS_CSV, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'key' in row and 'name' in row:
                    brands_map[row['key'].lower()] = row['name']
    return brands_map

def load_rules_map():
    """rules.csv から {タグID: [キーワードリスト]} を読み込む"""
    rules = {}
    if os.path.exists(RULE_CSV):
        with open(RULE_CSV, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tag = row.get('tag', '').strip()
                kw_str = row.get('keywords', '').strip()
                if tag and kw_str:
                    kws = [normalize_text(k) for k in kw_str.replace(',', ' ').split() if k]
                    rules[tag] = kws
    return rules

def load_allowed_tags():
    """tags.csv から許可タグセットを読み込む"""
    allowed = set()
    # rules.csv のタグも許可
    rules = load_rules_map()
    allowed.update(normalize_text(t) for t in rules.keys())
    # tags.csv の key
    if os.path.exists(TAG_CSV):
        with open(TAG_CSV, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get('key', '').strip()
                if key:
                    allowed.add(normalize_text(key))
    return allowed

# ─────────────────────────────────────────────
# 楽天 Product Search API v2（全情報取得）
# ─────────────────────────────────────────────
def fetch_product_search_v2(jan):
    """
    楽天Product Search API (v2) から全情報を一度に取得する。
    戻り値: {
      "name": "商品名",
      "makerName": "メーカー名",
      "brandName": "ブランド名",
      "description": "商品説明文",
      "catalogPrice": 価格(数値),
      "image": "画像URL"
    } または None
    """
    if not RAKUTEN_APP_ID or not RAKUTEN_ACCESS_KEY or not jan or jan == '#':
        return None
    url = "https://openapi.rakuten.co.jp/ichibaproduct/api/Product/Search/20250801"
    params = {
        "applicationId": RAKUTEN_APP_ID.strip(),
        "accessKey": RAKUTEN_ACCESS_KEY.strip(),
        "keyword": jan,
        "format": "json"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://kyuni-f.github.io/pet925/",
        "Referer": "https://kyuni-f.github.io/pet925/"
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            products = data.get("Products", [])
            if products and isinstance(products, list) and len(products) > 0:
                first_entry = products[0]
                product = first_entry.get("Product", first_entry) if isinstance(first_entry, dict) else first_entry
                if not isinstance(product, dict):
                    return None

                result = {
                    "name": product.get("productName") or product.get("productTitle") or product.get("title"),
                    "makerName": product.get("makerName"),
                    "brandName": product.get("brandName"),
                    "description": product.get("productDescription") or product.get("explanation"),
                    "catalogPrice": product.get("catalogPrice") or product.get("price"),
                    "image": None
                }
                # 画像URL
                img_url = product.get("mediumImageUrl") or product.get("smallImageUrl") or product.get("imageUrl")
                if img_url:
                    result["image"] = re.sub(r"\?_ex=.*$", "", img_url)
                return result
        elif resp.status_code == 429:
            print(f"  ⚠️ Product Search API レート制限: JAN {jan}")
        else:
            print(f"  ⚠️ Product Search API エラー {resp.status_code}: JAN {jan}")
    except Exception as e:
        print(f"  ❌ Product Search API 通信エラー: {e} (JAN: {jan})")
    return None

# ─────────────────────────────────────────────
# 楽天 Item Search API（フォールバック用）
# ─────────────────────────────────────────────
def fetch_item_search(jan):
    """
    楽天Item Search API。Product Search API で取得できなかった場合のフォールバック。
    戻り値: {"name": ..., "image": ..., "url": ...} または None
    """
    if not RAKUTEN_APP_ID or not RAKUTEN_ACCESS_KEY or not jan or jan == '#':
        return None
    url = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401"
    params = {
        "applicationId": RAKUTEN_APP_ID.strip(),
        "accessKey": RAKUTEN_ACCESS_KEY.strip(),
        "keyword": jan,
        "hits": 1,
        "format": "json",
        "formatVersion": 2
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://kyuni-f.github.io/pet925/",
        "Referer": "https://kyuni-f.github.io/pet925/"
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items") or data.get("Items", [])
            if items:
                entry = items[0]
                item = entry.get("Item") if isinstance(entry, dict) and "Item" in entry else entry
                if not isinstance(item, dict):
                    return None
                img_url = None
                if item.get("image_url"):
                    img_url = item.get("image_url")
                else:
                    urls_list = item.get("medium_image_urls") or item.get("mediumImageUrls")
                    if urls_list and isinstance(urls_list, list) and len(urls_list) > 0:
                        first_item = urls_list[0]
                        if isinstance(first_item, dict):
                            img_url = first_item.get("imageUrl")
                        else:
                            img_url = first_item
                return {
                    "name": item.get("itemName") or item.get("name"),
                    "image": re.sub(r"\?_ex=.*$", "", img_url) if img_url else None,
                    "url": item.get("itemUrl")
                }
        elif resp.status_code == 429:
            print(f"  ⚠️ Item Search API レート制限: JAN {jan}")
        else:
            print(f"  ⚠️ Item Search API エラー {resp.status_code}: JAN {jan}")
    except Exception as e:
        print(f"  ❌ Item Search API 通信エラー: {e} (JAN: {jan})")
    return None

# ─────────────────────────────────────────────
# Yahoo!ショッピング API（フォールバック用）
# ─────────────────────────────────────────────
def fetch_yahoo_shopping(jan):
    """Yahoo!ショッピングAPIから商品名と画像を取得"""
    if not YAHOO_CLIENT_ID or not jan or jan == '#':
        return None
    url = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
    params = {"appid": YAHOO_CLIENT_ID.strip(), "jan_code": jan, "results": 1}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            hits = data.get("hits", [])
            if hits and isinstance(hits, list):
                first = hits[0]
                if isinstance(first, dict):
                    img_obj = first.get("image", {})
                    img_url = img_obj.get("medium") or img_obj.get("small")
                    if img_url:
                        img_url = img_url.replace("/i/c/", "/i/g/").replace("/i/d/", "/i/g/")
                    return {
                        "name": first.get("name"),
                        "image": img_url,
                        "url": first.get("url")
                    }
    except Exception as e:
        pass  # フォールバックなのでエラーは表示しない
    return None

# ─────────────────────────────────────────────
# Gemini API で説明文を自動生成
# ─────────────────────────────────────────────
def generate_description_via_gemini(product_name, maker_name, raw_description, jan):
    """
    Gemini API を使用して60字程度の説明文を生成する。
    元ネタ（raw_description）がある場合はそれを参考にする。
    """
    if not GEMINI_API_KEY:
        return None

    model_name = "gemini-2.5-flash"
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"

    # 元ネタがある場合はそれをプロンプトに含める
    source_text = f"\n【参考: 商品説明の元ネタ】\n{raw_description[:500]}" if raw_description else ""

    prompt = f"""あなたはペットフード比較サイトのデータ作成アシスタントです。
以下の商品の「特徴・おすすめポイント」を、**60文字程度**で簡潔に説明してください。

【商品名】{product_name}
【メーカー】{maker_name or "不明"}【JANコード】{jan}{source_text}

【ルール】
- 商品の特徴を具体的に（例：主原料、対応年齢、健康ケア）
- 「どんな悩みを持つ犬・猫におすすめか」というユーザー視点を含める
- 60文字程度（50〜70字）に収める
- 宣伝文句や誇張表現は避ける
- 余計な解説は一切不要。説明文のみを出力してください。"""

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            res_data = resp.json()
            if "candidates" in res_data and len(res_data["candidates"]) > 0:
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                # 説明文のみを取り出す（余計な改行・引用など除去）
                desc = text.replace("```", "").strip()
                # 60文字前後になるよう調整
                if len(desc) > 80:
                    desc = desc[:77] + "..."
                return desc
    except Exception as e:
        print(f"  ⚠️ Gemini API エラー: {e}")
    return None

# ─────────────────────────────────────────────
# タグ自動判定
# ─────────────────────────────────────────────
def auto_assign_tags(product_name, maker_name, rules_map, allowed_tags):
    """
    rules.csv のルールと商品名から自動でタグを判定する。
    戻り値: ["dog", "adult", "gf", ...] のリスト
    """
    tags = set()
    check_text = normalize_text(f"{maker_name or ''} {product_name or ''}")

    # 1. rules.csv のキーワードマッチング
    for tag_id, keywords in rules_map.items():
        for kw in keywords:
            if kw in check_text:
                tags.add(normalize_text(tag_id))
                break

    # 2. 年齢判定
    name_lower = (product_name or "").lower()
    if re.search(r'子[犬猫]|パピー|puppy|子いぬ|子ねこ|り乳|幼犬|幼猫', name_lower):
        tags.add('puppy')
    elif re.search(r'シニア|senior|老[犬猫]|高齢', name_lower):
        tags.add('senior')
    elif re.search(r'成[犬猫]|adult|1歳|2歳|3歳|4歳|5歳|6歳', name_lower):
        tags.add('adult')
    else:
        # 「全年齢」「全齢」がなければall_agesにしない（デフォルトはadultと判断）
        if re.search(r'全年齢|全齢|all.?ages|オールステージ', name_lower):
            tags.add('all_ages')
        else:
            tags.add('adult')

    # 3. 動物種判定
    if re.search(r'[犬]|dog', name_lower):
        tags.add('dog')
    if re.search(r'[猫]|cat', name_lower):
        tags.add('cat')
    # dog も cat もなければ両方つける（汎用フード）
    if 'dog' not in tags and 'cat' not in tags:
        tags.add('dog')
        tags.add('cat')

    # 許可タグのみフィルタ
    return sorted([t for t in tags if t in allowed_tags])

def merge_into_existing(existing_row, new_data, fieldnames):
    """
    既存行に対して、AUTO_UPDATE_FIELDS の項目だけ新データで上書きする。
    新データの値が '#' や空文字の場合は既存値を維持する。
    手動編集項目（amz/yah/a8/label/promo/size/amz_p/yah_p など）は変更しない。
    """
    for field in AUTO_UPDATE_FIELDS:
        new_val = new_data.get(field)
        if new_val is not None and new_val != '#' and str(new_val).strip() != '':
            existing_row[field] = new_val
    # jan は変わらないはずだが念のため保持
    existing_row['jan'] = new_data.get('jan', existing_row.get('jan'))
    # fieldnames に存在しないキーが無いことを保証
    for f in fieldnames:
        if f not in existing_row:
            existing_row[f] = '#'
    return existing_row

# ─────────────────────────────────────────────
# メイン処理
# ─────────────────────────────────────────────

def main(jan_list_path):
    if not os.path.exists(jan_list_path):
        print(f"エラー: JANコードリスト '{jan_list_path}' が見つかりません。")
        sys.exit(1)

    print(f"{'='*60}")
    print("pet925 全自動データ収集スクリプト")
    print(f"{'='*60}")

    # 設定チェック
    if not RAKUTEN_APP_ID or not RAKUTEN_ACCESS_KEY:
        print("❌ エラー: 楽天APIの設定が不足しています（RAKUTEN_APP_ID, RAKUTEN_ACCESS_KEY）")
        print("   .env ファイルまたは環境変数を確認してください。")
        sys.exit(1)

    print(f"🔑 楽天API: 設定済み")
    if GEMINI_API_KEY:
        print(f"🔑 Gemini API: 設定済み（説明文自動生成が有効）")
    else:
        print(f"⚠️ Gemini API: 未設定（説明文は自動生成されません。商品名のみで行きます）")

    # 各種データ読み込み
    brands_map = load_brands_map()
    rules_map = load_rules_map()
    allowed_tags = load_allowed_tags()

    print(f"\n📋 ブランド: {len(brands_map)}件")
    print(f"📋 タグルール: {len(rules_map)}件")
    print(f"📋 許可タグ: {len(allowed_tags)}件")

    # ── 既存 products.csv 読み込み ──
    existing_rows = []
    existing_jans = set()
    fieldnames = FIELD_NAMES
    if os.path.exists(PRODUCT_CSV) and os.path.getsize(PRODUCT_CSV) > 0:
        with open(PRODUCT_CSV, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or fieldnames
            for row in reader:
                jan = normalize_jan(row.get('jan', ''))
                if jan and jan != '#':
                    existing_jans.add(jan)
                existing_rows.append(row)
    print(f"\n📂 既存 products.csv: {len(existing_rows)}行 ({len(existing_jans)}件のJAN)")

    # JAN → 既存行 のインデックス（更新用マージに使用）
    existing_row_index = {}
    for row in existing_rows:
        jan_key = normalize_jan(row.get('jan', ''))
        if jan_key and jan_key != '#':
            existing_row_index[jan_key] = row

    # ── JANリスト読み込み ──
    new_jans = []
    update_jans = []
    seen_in_list = set()
    with open(jan_list_path, 'r', encoding='utf-8-sig', newline='') as f:
        for i, row in enumerate(csv.reader(f)):
            if not row: continue
            jan = normalize_jan(row[0])
            if jan and jan != 'Undefined' and jan.isdigit() and len(jan) in [13, 14]:
                jan13 = jan if len(jan) == 13 else jan[:13]
                if jan13 in seen_in_list:
                    print(f"⏭️ 入力ファイル内で重複のためスキップ: JAN {jan13}")
                    continue
                seen_in_list.add(jan13)
                if jan13 in existing_jans:
                    update_jans.append(jan13)
                    print(f"🔄 更新対象: JAN {jan13}")
                else:
                    new_jans.append(jan13)
            else:
                print(f"⚠️ 無効な行 {i+1}: '{row[0]}'")

    all_jans = new_jans + update_jans

    if not all_jans:
        print("\n✅ 処理対象のJANコードはありません。処理を終了します。")
        return

    print(f"\n{'='*60}")
    print(f"🆕 新規JANコード: {len(new_jans)}件 / 🔄 更新JANコード: {len(update_jans)}件 を処理します")
    print(f"{'='*60}")

    # ── 各JANを処理 ──
    collected = []
    updated = []
    success_count = 0
    update_jans_set = set(update_jans)

    for idx, jan in enumerate(all_jans):
        if idx > 0:
            wait = 3.0 + random.uniform(0.5, 2.0)
            print(f"\n⏳ {wait:.0f}秒待機（レート制限回避）...")
            time.sleep(wait)

        is_update = jan in update_jans_set
        print(f"\n{'─'*50}")
        print(f"[{idx+1}/{len(all_jans)}] JAN: {jan} {'（更新）' if is_update else '（新規）'}")


        # Step 1: Product Search API v2（一発取得）
        prod_data = fetch_product_search_v2(jan)
        if prod_data and prod_data.get("name"):
            product_name = prod_data["name"]
            maker_name = prod_data.get("makerName") or prod_data.get("brandName") or ""
            raw_desc = prod_data.get("description") or ""
            catalog_price = prod_data.get("catalogPrice")
            image_url = prod_data.get("image")

            print(f"  ✅ Product Search API: {product_name[:40]}...")
            if maker_name:
                print(f"    メーカー: {maker_name}")
            if catalog_price:
                print(f"    価格: {catalog_price}円")
            if image_url:
                print(f"    画像: {image_url[:50]}...")

            # Step 2: 説明文をGeminiで生成（元ネタあり）
            description = ""
            if GEMINI_API_KEY:
                print(f"  🤖 Geminiで説明文を生成中...")
                desc = generate_description_via_gemini(product_name, maker_name, raw_desc, jan)
                if desc:
                    description = desc
                    print(f"    ✅ 説明文生成: {desc[:40]}...")
                time.sleep(2)  # Gemini API レート制限対策

            # Step 3: タグ自動判定
            tags = auto_assign_tags(product_name, maker_name, rules_map, allowed_tags)
            print(f"  🏷️ タグ: {' '.join(tags)}")

            # Step 4: ブランド名の正規化
            brand_key = normalize_text(maker_name or "")
            brand_display = brands_map.get(brand_key, maker_name or "")

            # Step 5: 価格
            price_str = str(catalog_price) if catalog_price and catalog_price > 0 else "0"

            # Step 6: 結果を保存
            new_row = {f: '#' for f in fieldnames}
            new_row['jan'] = jan
            new_row['name'] = product_name
            new_row['brand'] = brand_display
            new_row['tags'] = ' '.join(tags)
            new_row['desc'] = description
            new_row['img'] = image_url or '#'
            new_row['rak'] = '#'  # 表示時に商品名で検索URLを生成させる
            new_row['rak_p'] = price_str

            if is_update:
                merged = merge_into_existing(existing_row_index[jan], new_row, fieldnames)
                updated.append(merged)
            else:
                collected.append(new_row)
            success_count += 1
            continue


        # Step 1-b: Item Search API（フォールバック）
        print(f"  [フォールバック] Item Search API を試行...")
        item_data = fetch_item_search(jan)
        if item_data and item_data.get("name"):
            product_name = item_data["name"]
            image_url = item_data.get("image")
            item_url = item_data.get("url")

            print(f"  ✅ Item Search API: {product_name[:40]}...")

            # 説明文をGeminiで生成（元ネタなし）
            description = ""
            if GEMINI_API_KEY:
                print(f"  🤖 Geminiで説明文を生成中...")
                desc = generate_description_via_gemini(product_name, "", "", jan)
                if desc:
                    description = desc
                    print(f"    ✅ 説明文生成: {desc[:40]}...")
                time.sleep(2)

            # タグ判定
            tags = auto_assign_tags(product_name, "", rules_map, allowed_tags)
            print(f"  🏷️ タグ: {' '.join(tags)}")

            new_row = {f: '#' for f in fieldnames}
            new_row['jan'] = jan
            new_row['name'] = product_name
            new_row['tags'] = ' '.join(tags)
            new_row['desc'] = description
            new_row['img'] = image_url or '#'
            new_row['rak'] = item_url or '#'  # 実商品URLがあれば使用、なければ表示時に商品名で生成
            new_row['rak_p'] = '0'

            if is_update:
                merged = merge_into_existing(existing_row_index[jan], new_row, fieldnames)
                updated.append(merged)
            else:
                collected.append(new_row)
            success_count += 1
            continue


        # Step 1-c: Yahoo! ショッピング（最終フォールバック）
        print(f"  [最終フォールバック] Yahoo!ショッピングAPI を試行...")
        yahoo_data = fetch_yahoo_shopping(jan)
        if yahoo_data and yahoo_data.get("name"):
            product_name = yahoo_data["name"]
            image_url = yahoo_data.get("image")

            print(f"  ✅ Yahoo! Shopping: {product_name[:40]}...")

            tags = auto_assign_tags(product_name, "", rules_map, allowed_tags)
            print(f"  🏷️ タグ: {' '.join(tags)}")

            new_row = {f: '#' for f in fieldnames}
            new_row['jan'] = jan
            new_row['name'] = product_name
            new_row['tags'] = ' '.join(tags)
            new_row['img'] = image_url or '#'
            new_row['yah'] = '#'  # 表示時に商品名で検索URLを生成させる
            new_row['rak_p'] = '0'

            if is_update:
                merged = merge_into_existing(existing_row_index[jan], new_row, fieldnames)
                updated.append(merged)
            else:
                collected.append(new_row)
            success_count += 1
            continue

        print(f"  ❌ 全API失敗: JAN={jan}")

    # ── products.csv に追記・更新 ──
    print(f"\n{'='*60}")
    print(f"完了: {success_count}/{len(all_jans)}件取得成功（新規 {len(collected)}件 / 更新 {len(updated)}件）")

    if collected or updated:
        # 新規行を既存行リストに追加
        # （updated の内容は existing_row_index 経由で existing_rows 内のオブジェクトを
        #   直接書き換えているため、既に existing_rows に反映済み）
        for item in collected:
            jan = item.get('jan', '')
            if jan:
                existing_rows.append(item)

        # JANコード順にソート
        existing_rows.sort(key=lambda r: (0, normalize_jan(r.get('jan', '#'))) if r.get('jan', '#') != '#' and r['jan'].isdigit() else (1, r.get('name', '')))

        # 書き出し
        with open(PRODUCT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)

        print(f"\n✅ products.csv を更新しました（全{len(existing_rows)}行、新規{len(collected)}件・更新{len(updated)}件）")
        print(f"💡 内容を確認するには ODS で開くか、以下のコマンドを実行:")
        print(f"   python3 csv_to_json.py")
        print(f"💡 手動で微調整したい場合は pet925_master.ods の products シートに貼り付けてください")
    else:
        print("どのAPIからもデータを取得できませんでした。")
        print("JANコードが正しいか確認してください。")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用法: python3 auto_collect_all.py [JANリストCSV]")
        print("")
        print("JANリストCSVの形式: 1列目に13桁のJANコードを並べたファイル")
        print("例: python3 auto_collect_all.py jan_list.csv")
        sys.exit(1)
    main(sys.argv[1])