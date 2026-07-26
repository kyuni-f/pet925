import csv
import os
import sys
import time
import re
import requests
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote

DATA_DIR = 'data'
PRODUCT_CSV = os.path.join(DATA_DIR, 'products.csv')
BRANDS_CSV = os.path.join(DATA_DIR, 'brands.csv')

def load_rakuten_config():
    config = {
        "app_id": None,
        "access_key": None,
        "yahoo_client_id": None
    }
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    config["app_id"] = os.getenv("RAKUTEN_APP_ID")
    config["access_key"] = os.getenv("RAKUTEN_ACCESS_KEY")
    config["yahoo_client_id"] = os.getenv("YAHOO_CLIENT_ID")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.split('#')[0].strip()
                if not line: continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key_clean = key.strip()
                    val_clean = value.strip().strip("'").strip('"')
                    if key_clean == "RAKUTEN_APP_ID":
                        config["app_id"] = val_clean
                    elif key_clean in ["RAKUTEN_ACCESS_KEY", "RAKUTEN_APPLICATION_SECRET"]:
                        config["access_key"] = val_clean
                    elif key_clean == "YAHOO_CLIENT_ID":
                        config["yahoo_client_id"] = val_clean
    return config

RAKUTEN_CONFIG = load_rakuten_config()
RAKUTEN_APP_ID = RAKUTEN_CONFIG.get("app_id")
RAKUTEN_ACCESS_KEY = RAKUTEN_CONFIG.get("access_key")
YAHOO_CLIENT_ID = RAKUTEN_CONFIG.get("yahoo_client_id")

def fetch_rakuten_item_data(jan):
    if not RAKUTEN_APP_ID or not RAKUTEN_ACCESS_KEY or jan == '#':
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
    YOUR_REGISTERED_DOMAIN = "https://kyuni-f.github.io/pet925/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": YOUR_REGISTERED_DOMAIN,
        "Referer": YOUR_REGISTERED_DOMAIN + "/"
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
                name = item.get("itemName") or item.get("name")
                result = {
                    "name": name,
                    "brand": None,
                    "image": None,
                    "url": item.get("itemUrl")
                }
                if img_url:
                    result["image"] = re.sub(r"\?_ex=.*$", "", img_url)
                return result
        elif resp.status_code == 429:
            print(f"  ⚠️ 楽天Item Search API レート制限: JAN {jan}")
        else:
            print(f"  ⚠️ 楽天Item Search API エラー {resp.status_code}: JAN {jan}")
    except Exception as e:
        print(f"  ❌ 楽天Item Search API 通信エラー: {e} (JAN: {jan})")
    return None

def fetch_yahoo_shopping_data(jan):
    if not YAHOO_CLIENT_ID or jan == '#':
        return None
    url = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
    params = {
        "appid": YAHOO_CLIENT_ID.strip(),
        "jan_code": jan,
        "results": 1
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            hits = data.get("hits", [])
            if hits and isinstance(hits, list):
                first_hit = hits[0]
                if isinstance(first_hit, dict) and "image" in first_hit:
                    img_obj = first_hit.get("image", {})
                    img_url = img_obj.get("medium") or img_obj.get("small")
                    if img_url:
                        img_url = img_url.replace("/i/c/", "/i/g/").replace("/i/d/", "/i/g/")
                        return {
                            "name": first_hit.get("name"),
                            "brand": first_hit.get("seller", {}).get("name"),
                            "image": img_url,
                            "url": first_hit.get("url")
                        }
        elif resp.status_code == 429:
            print(f"  ⚠️ Yahoo!ショッピングAPI レート制限: JAN {jan}")
        elif resp.status_code == 400:
            print(f"  ⚠️ Yahoo!ショッピングAPI エラー 400 (JAN:{jan})")
    except Exception as e:
        print(f"  ❌ Yahoo!ショッピングAPI 通信エラー: {e} (JAN: {jan})")
    return None

def load_brands_map():
    brands_map = {}
    if os.path.exists(BRANDS_CSV):
        with open(BRANDS_CSV, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'key' in row and 'name' in row:
                    brands_map[row['key'].lower()] = row['name']
    return brands_map

def normalize_brand(brand_name, brands_map):
    if not brand_name: return ''
    normalized_name = brand_name.lower().strip()
    for key, name in brands_map.items():
        if normalized_name == key or name.lower() in normalized_name:
            return name
    return brand_name

def normalize_jan(jan_str):
    jan = jan_str.strip().replace(" ", "").replace("-", "")
    if jan.isdigit() and len(jan) == 14:
        return jan[:13]
    return jan

def fetch_jan_data(jan_code):
    """JANコード1件に対して全APIを順次試行。結果にjanフィールドを含めて返す"""
    if not jan_code or jan_code == '#' or not jan_code.isdigit() or len(jan_code) not in [13, 14]:
        return None

    jan = normalize_jan(jan_code)
    print(f"\n{'='*50}")
    print(f"JAN: {jan}")

    # 優先度1: 楽天Item Search API
    if RAKUTEN_APP_ID and RAKUTEN_ACCESS_KEY:
        print(f"  [楽天Item Search API] 検索中 ...")
        data = fetch_rakuten_item_data(jan)
        if data:
            data['jan'] = jan
            print(f"  ✅ 楽天からデータ取得成功: {data.get('name','')[:50]}")
            return data
        time.sleep(3.0 + random.uniform(0.5, 1.5))

    # 優先度2: Yahoo!ショッピングAPI (13桁のみ)
    if len(jan) == 13 and YAHOO_CLIENT_ID and YAHOO_CLIENT_ID != "YOUR_YAHOO_CLIENT_ID":
        print(f"  [Yahoo!ショッピングAPI] 検索中 ...")
        data = fetch_yahoo_shopping_data(jan)
        if data:
            data['jan'] = jan
            print(f"  ✅ Yahoo!からデータ取得成功: {data.get('name','')[:50]}")
            return data

    print(f"  ❌ データ取得失敗: JAN={jan}")
    return None

def main(jan_list_path):
    if not os.path.exists(jan_list_path):
        print(f"エラー: JANコードリスト '{jan_list_path}' が見つかりません。")
        sys.exit(1)

    # 既存CSV読込
    existing_rows = []
    existing_jans = set()
    fieldnames = ['name', 'brand', 'tags', 'desc', 'size', 'jan', 'img', 'amz', 'rak', 'yah', 'a8', 'label', 'promo', 'amz_p', 'rak_p', 'yah_p']
    if os.path.exists(PRODUCT_CSV) and os.path.getsize(PRODUCT_CSV) > 0:
        with open(PRODUCT_CSV, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or fieldnames
            for row in reader:
                jan = normalize_jan(row.get('jan', ''))
                if jan and jan != '#':
                    existing_jans.add(jan)
                existing_rows.append(row)

    brands_map = load_brands_map()

    # JANリスト読込
    new_jans = []
    with open(jan_list_path, 'r', encoding='utf-8-sig', newline='') as f:
        for i, row in enumerate(csv.reader(f)):
            if not row: continue
            jan = normalize_jan(row[0])
            if jan and jan != 'Undefined' and jan.isdigit() and len(jan) in [13, 14]:
                # 13桁に正規化
                jan13 = jan if len(jan) == 13 else jan[:13]
                if jan13 not in existing_jans:
                    new_jans.append(jan13)
                    existing_jans.add(jan13)
                else:
                    print(f"Skipping existing JAN: {jan13}")
            else:
                print(f"Invalid JAN in line {i+1}: '{row[0]}'")

    if not new_jans:
        print("新しいJANコードはありません。")
        return

    print(f"\n{'='*50}")
    print(f"新規JANコード: {len(new_jans)}件を処理します")
    print(f"{'='*50}")

    # 逐次APIコール
    collected = []
    for idx, jan in enumerate(new_jans):
        if idx > 0:
            wait = 4.0 + random.uniform(0.5, 2.0)
            print(f"\n⏳ {wait:.0f}秒待機...")
            time.sleep(wait)
        result = fetch_jan_data(jan)
        if result:
            collected.append(result)

    print(f"\n{'='*50}")
    print(f"完了: {len(collected)}/{len(new_jans)}件取得成功")

    if collected:
        # 取得したデータを既存行に追加
        for item in collected:
            jan = item.get('jan', '')
            if jan:
                new_row = {f: '#' for f in fieldnames}  # デフォルトは#に（未設定を示す）
                new_row['jan'] = jan
                new_row['name'] = item.get('name', '')
                new_row['brand'] = normalize_brand(item.get('brand', ''), brands_map)
                new_row['img'] = item.get('image', '') or '#'
                new_row['rak'] = item.get('url', '') if item.get('url', '').startswith('http') and 'rakuten' in item.get('url', '') else '#'
                new_row['amz'] = item.get('url', '') if item.get('url', '').startswith('http') and 'amazon' in item.get('url', '') else '#'
                new_row['yah'] = item.get('url', '') if item.get('url', '').startswith('http') and 'yahoo' in item.get('url', '') else '#'
                existing_rows.append(new_row)

        # JANコード順にソート
        def sort_key(r):
            j = normalize_jan(r.get('jan', '#'))
            if j and j != '#':
                return (0, j)
            return (1, r.get('name', ''))

        existing_rows.sort(key=sort_key)

        # 書き出し（既存行すべて + 新規行を保持！）
        with open(PRODUCT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)

        print(f"\n✅ products.csv を更新しました（全{len(existing_rows)}行）")
        print("💡 次に python3 csv_to_json.py を実行してください")
    else:
        print("どのAPIからもデータを取得できませんでした。")
        print("JANコードが正しいか確認してください。")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用法: python3 jan_data_collector.py [JANリストCSV]")
        sys.exit(1)
    main(sys.argv[1])