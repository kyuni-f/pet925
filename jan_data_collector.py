import csv
import os
import sys
import time
import re
import requests
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote

# 設定ファイル (csv_to_json.pyから一部流用・調整)
DATA_DIR = 'data'
PRODUCT_CSV = os.path.join(DATA_DIR, 'products.csv')
BRANDS_CSV = os.path.join(DATA_DIR, 'brands.csv')

# API設定の読み込み (csv_to_json.pyの関数を流用)
def load_rakuten_config():
    config = {
        "app_id": None,
        "access_key": None,
        "traditional_app_id": None,
        "yahoo_client_id": None
    }
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")

    # ターミナル環境変数を最優先
    config["app_id"] = os.getenv("RAKUTEN_APP_ID")
    config["access_key"] = os.getenv("RAKUTEN_ACCESS_KEY")
    config["traditional_app_id"] = os.getenv("RAKUTEN_TRADITIONAL_APP_ID")
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
                    elif key_clean == "RAKUTEN_TRADITIONAL_APP_ID":
                        config["traditional_app_id"] = val_clean
                    elif key_clean == "YAHOO_CLIENT_ID":
                        config["yahoo_client_id"] = val_clean
    return config

RAKUTEN_CONFIG = load_rakuten_config()
RAKUTEN_APP_ID = RAKUTEN_CONFIG.get("app_id")
RAKUTEN_ACCESS_KEY = RAKUTEN_CONFIG.get("access_key")
RAKUTEN_TRADITIONAL_APP_ID = RAKUTEN_CONFIG.get("traditional_app_id")
YAHOO_CLIENT_ID = RAKUTEN_CONFIG.get("yahoo_client_id")

# 楽天API（マイクロサービス版 Product Search）
def fetch_rakuten_product_data_v2(jan):
    # RAKUTEN_APP_IDとRAKUTEN_ACCESS_KEYを使用
    if not RAKUTEN_APP_ID or not RAKUTEN_ACCESS_KEY or jan == '#':
        print(f"  ⚠️ 楽天Product Search API v2 (高画質カタログ)に必要なAPIキーが設定されていません。")
        return None

    # 現状、楽天Product Search API v2 は403エラーとなるため、コメントアウトしてスキップ
    # url = "https://openapi.rakuten.co.jp/ichibaproduct/api/Product/Search/20250801"
    # params = {
    #     "applicationId": RAKUTEN_APP_ID.strip(),
    #     "accessKey": RAKUTEN_ACCESS_KEY.strip(),
    #     "keyword": jan,
    #     "format": "json"
    # }
    # data = fetch_rakuten_product_data_v2(jan) # これをget_product_info_from_janからは呼ばない
    
    # fetch_rakuten_product_data_v2 関数を一時的に従来のProduct Search APIと同じロジックにする
    # RAKUTEN_TRADITIONAL_APP_ID が None の場合は処理をスキップするように修正
    if RAKUTEN_TRADITIONAL_APP_ID is None or RAKUTEN_TRADITIONAL_APP_ID == "YOUR_RAKUTEN_TRADITIONAL_APP_ID":
        print(f"  ⚠️ RAKUTEN_TRADITIONAL_APP_IDが設定されていないため、fetch_rakuten_traditional_dataをスキップします。")
        return None

    url = "https://app.rakuten.co.jp/services/api/Product/Search/20170426"
    params = {
        "applicationId": RAKUTEN_TRADITIONAL_APP_ID.strip(),
        "keyword": jan,
        "format": "json"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            products = data.get("Products", [])
            if products and isinstance(products, list) and len(products) > 0:
                product = products[0].get("Product", products[0])
                img_url = product.get("productImageUrl")
                if img_url:
                    high_res_image = re.sub(r"\?_ex=.*$", "", img_url)
                    return {
                        "name": product.get("productName"),
                        "brand": product.get("brandName"),
                        "image": high_res_image,
                        "url": product.get("productUrl")
                    }
        elif resp.status_code == 429:
            print(f"  ⚠️ 楽天Product Search API v2 レート制限: JAN {jan}")
        else:
            print(f"  ⚠️ 楽天Product Search API v2 エラー {resp.status_code}: JAN {jan}")
    except Exception as e:
        print(f"  ❌ 楽天Product Search API v2 通信エラー: {e} (JAN: {jan})")
    return None

def fetch_rakuten_traditional_data(jan):
    # RAKUTEN_TRADITIONAL_APP_IDを使用
    if not RAKUTEN_TRADITIONAL_APP_ID or jan == "#" or RAKUTEN_TRADITIONAL_APP_ID == "YOUR_RAKUTEN_TRADITIONAL_APP_ID": # YOUR_RAKUTEN_TRADITIONAL_APP_IDも考慮
        # print(f"  ⚠️ 楽天Traditional Product Search APIに必要なAPIキーが設定されていません。") # JAN個別にメッセージが出力されすぎるためコメントアウト
        return None

    url = "https://app.rakuten.co.jp/services/api/Product/Search/20170426"
    params = {
        "applicationId": RAKUTEN_TRADITIONAL_APP_ID.strip(),
        "keyword": jan,
        "format": "json"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            products = data.get("Products", [])
            if products and isinstance(products, list) and len(products) > 0:
                product = products[0].get("Product", {})
                img_url = product.get("productImageUrl")
                if img_url:
                    high_res_image = re.sub(r"\?_ex=.*$", "", img_url)
                    return {
                        "name": product.get("productName"),
                        "brand": product.get("brandName"),
                        "image": high_res_image,
                        "url": product.get("productUrl")
                    }
        elif resp.status_code == 429:
            print(f"  ⚠️ 楽天Traditional API レート制限: JAN {jan}")
        else:
            print(f"  ⚠️ 楽天Traditional API エラー {resp.status_code}: JAN {jan}")
    except Exception as e:
        print(f"  ❌ 楽天Traditional API 通信エラー: {e} (JAN: {jan})")
    return None

    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            products = data.get("Products", [])
            if products and isinstance(products, list) and len(products) > 0:
                product = products[0].get("Product", {})
                img_url = product.get("productImageUrl")
                if img_url:
                    high_res_image = re.sub(r"\?_ex=.*$", "", img_url)
                    return {
                        "name": product.get("productName"),
                        "brand": product.get("brandName"),
                        "image": high_res_image,
                        "url": product.get("productUrl")
                    }
        elif resp.status_code == 429:
            print(f"  ⚠️ 楽天Traditional API レート制限: JAN {jan}")
        else:
            print(f"  ⚠️ 楽天Traditional API エラー {resp.status_code}: JAN {jan}")
    except Exception as e:
        print(f"  ❌ 楽天Traditional API 通信エラー: {e} (JAN: {jan})")
    return None

# Yahoo!ショッピング商品検索API
def fetch_yahoo_shopping_data(jan):
    if not YAHOO_CLIENT_ID or jan == '#':
        return None

    url = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
    params = {
        "appid": YAHOO_CLIENT_ID.strip(),
        "jan_code": jan,
        "results": 1
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            hits = data.get("hits", [])
            if hits and isinstance(hits, list):
                first_hit = hits[0]
                if isinstance(first_hit, dict) and "image" in first_hit:
                    img_obj = first_hit.get("image", {})
                    img_url = img_obj.get("medium") or img_obj.get("small")
                    if img_url:
                        # Yahooの画像URLに含まれるサイズを表すフォルダ文字を「g」(最大・高画質)に変換
                        img_url = img_url.replace("/i/c/", "/i/g/").replace("/i/d/", "/i/g/")
                        return {
                            "name": first_hit.get("name"),
                            "brand": first_hit.get("seller", {}).get("name"),
                            "image": img_url,
                            "url": first_hit.get("url")
                        }
        elif resp.status_code == 429:
            print(f"  ⚠️ Yahoo!ショッピングAPI レート制限: JAN {jan}")
        else:
            print(f"  ⚠️ Yahoo!ショッピングAPI エラー {resp.status_code}: JAN {jan}")
    except Exception as e:
        print(f"  ❌ Yahoo!ショッピングAPI 通信エラー: {e} (JAN: {jan})")
    return None

# JANコードから商品情報を取得するメイン関数
def get_product_info_from_jan(jan, existing_products_by_jan):
    if not jan or jan == '#' or not jan.isdigit() or (len(jan) != 13 and len(jan) != 14):
        return None

    # 既存のCSVに同じJANコードがあればスキップ
    if jan in existing_products_by_jan:
        return None

    # API呼び出しの間にウェイトを挟む
    time.sleep(1.0 + random.uniform(0.1, 0.5))

    print(f"Attempting to fetch data for JAN: {jan}")
    
    # API呼び出しの優先順位を調整
    # 優先度1: 楽天Traditional Product Search APIを試す (RAKUTEN_TRADITIONAL_APP_ID が必須)
    if RAKUTEN_TRADITIONAL_APP_ID and RAKUTEN_TRADITIONAL_APP_ID != "YOUR_RAKUTEN_TRADITIONAL_APP_ID":
        print(f"  [楽天Traditional API] 検索中: JAN={jan}")
        data = fetch_rakuten_traditional_data(jan)
        if data: return data
    else:
        print(f"  ⚠️ 楽天Traditional Product Search APIに必要なAPIキーが設定されていないためスキップされました。")
    
    time.sleep(1.0 + random.uniform(0.1, 0.5))

    # 優先度2: Yahoo!ショッピング商品検索APIを試す (YAHOO_CLIENT_ID が必須)
    if YAHOO_CLIENT_ID and YAHOO_CLIENT_ID != "YOUR_YAHOO_CLIENT_ID":
        print(f"  [Yahoo!ショッピングAPI] 検索中: JAN={jan}")
        data = fetch_yahoo_shopping_data(jan)
        if data: return data
    else:
        print(f"  ⚠️ Yahoo!ショッピングAPIに必要なAPIキーが設定されていないためスキップされました。")

    time.sleep(1.0 + random.uniform(0.1, 0.5))

    # 優先度3: 楽天Product Search API v2 (RAKUTEN_APP_ID と RAKUTEN_ACCESS_KEY が必須)
    if RAKUTEN_APP_ID and RAKUTEN_ACCESS_KEY: 
        print(f"  [楽天Product Search API v2] 検索中: JAN={jan}")
        data = fetch_rakuten_product_data_v2(jan)
        if data: return data
    else:
        print(f"  ⚠️ 楽天Product Search API v2 (高画質カタログ)に必要なAPIキーが設定されていないためスキップされました。")

    print(f"  No data found for JAN: {jan} from any API.")
    return None

# ブランド名寄せマップを読み込む
def load_brands_map():
    brands_map = {}
    if os.path.exists(BRANDS_CSV):
        with open(BRANDS_CSV, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'key' in row and 'name' in row:
                    brands_map[row['key'].lower()] = row['name']
    return brands_map

# JANコードから取得したブランド名を正規化・名寄せする
def normalize_brand(brand_name, brands_map):
    if not brand_name: return ''
    normalized_name = brand_name.lower().strip()
    # brands.csvに登録があれば、それに名寄せ
    for key, name in brands_map.items():
        if normalized_name == key or name.lower() in normalized_name:
            return name
    return brand_name # 名寄せできなければ元の名前を返す


def main(jan_list_path):
    if not os.path.exists(jan_list_path):
        print(f"エラー: JANコードリストファイル '{jan_list_path}' が見つかりません。")
        sys.exit(1)

    # 既存のproducts.csvを読み込み、JANコードをキーにしたマップを作成
    existing_products_by_jan = {}
    if os.path.exists(PRODUCT_CSV):
        with open(PRODUCT_CSV, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                jan = row.get('jan', '').strip().replace(" ", "").replace("-", "")
                if jan and jan != '#':
                    existing_products_by_jan[jan] = row

    # ブランド名寄せマップをロード
    brands_map = load_brands_map()

    new_jans_to_process = []
    with open(jan_list_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if not row: continue
            jan = row[0].strip().replace(" ", "").replace("-", "")
            if jan and jan != 'Undefined' and jan.isdigit() and (len(jan) == 13 or len(jan) == 14) and jan not in existing_products_by_jan:
                new_jans_to_process.append(jan)
            elif jan in existing_products_by_jan:
                print(f"Skipping existing JAN: {jan}")
            else:
                print(f"Invalid or empty JAN code in {jan_list_path} line {i+1}: '{row[0]}'")

    if not new_jans_to_process:
        print("処理すべき新しいJANコードが見つかりませんでした。")
        return

    print(f"Processing {len(new_jans_to_process)} new JAN codes...")

    # スレッドプールでAPI呼び出しを並列実行
    collected_data = []
    max_workers = 5 # 同時実行スレッド数 (APIレート制限を考慮して調整)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(get_product_info_from_jan, jan, existing_products_by_jan) for jan in new_jans_to_process]
        for i, future in enumerate(as_completed(futures)):
            data = future.result()
            if data:
                collected_data.append(data)
            sys.stdout.write(f"\rProgress: {i+1}/{len(new_jans_to_process)} JAN codes processed.")
            sys.stdout.flush()

    print("\nFinished API data collection.")

    if not collected_data:
        print("APIから商品情報を取得できませんでした。")
        return

    # 最終的なCSVデータ形式を定義
    # csv_to_json.py の期待する16列構成
    # 最終的なCSVデータ形式を定義
    # csv_to_json.py の期待する16列構成
    # 既存のproducts.csvを読み込み、すべての列名を取得
    existing_fieldnames = []
    if os.path.exists(PRODUCT_CSV) and os.path.getsize(PRODUCT_CSV) > 0:
        with open(PRODUCT_CSV, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            try:
                existing_fieldnames = next(reader)
            except StopIteration:
                pass
    
    # 新しく収集したデータで必要なフィールド名を追加
    collected_data_fieldnames = set()
    for item in collected_data:
        for key in item.keys():
            collected_data_fieldnames.add(key)

    # 最終的なフィールド名は、既存のフィールド名 + 収集したデータのフィールド名 + デフォルトのフィールド名
    # csv_to_json.pyが期待するフィールド順序を優先し、不足分を追加
    default_fieldnames = ['name', 'brand', 'tags', 'desc', 'size', 'jan', 'img', 'amz', 'rak', 'yah', 'a8', 'label', 'promo', 'amz_p', 'rak_p', 'yah_p']
    all_fieldnames_set = set(existing_fieldnames).union(collected_data_fieldnames).union(default_fieldnames)
    final_fieldnames = [f for f in default_fieldnames if f in all_fieldnames_set]
    for f in sorted(list(all_fieldnames_set.difference(final_fieldnames))):
        final_fieldnames.append(f)
    
    # 既存のデータと結合するための辞書型リストに変換
    existing_rows = []
    if os.path.exists(PRODUCT_CSV) and os.path.getsize(PRODUCT_CSV) > 0:
        with open(PRODUCT_CSV, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            existing_rows = list(reader)

    # 新しく収集したデータを既存の行にマージ (または新規追加)
    # JANコードで既存行を特定し、取得できた項目で更新する
    updated_products = {row.get('jan', '').strip().replace(" ", "").replace("-", ""): row for row in existing_rows if row.get('jan') and row.get('jan') != '#'}

    for item in collected_data:
        jan_code = item.get('jan', '').strip().replace(" ", "").replace("-", "")
        if jan_code and jan_code != '#':
            if jan_code not in updated_products:
                # 新規商品の場合、空の行を作成し、既知のフィールドを埋める
                new_row = {field: '' for field in final_fieldnames}
                new_row['jan'] = jan_code
                new_row['name'] = item.get('name', '')
                new_row['brand'] = normalize_brand(item.get('brand', ''), brands_map)
                new_row['img'] = item.get('image', '')
                new_row['rak'] = item.get('url', '') if item.get('url', '').startswith('http') and 'rakuten' in item.get('url', '') else ''
                new_row['amz'] = item.get('url', '') if item.get('url', '').startswith('http') and 'amazon' in item.get('url', '') else ''
                new_row['yah'] = item.get('url', '') if item.get('url', '').startswith('http') and 'yahoo' in item.get('url', '') else ''
                updated_products[jan_code] = new_row
            else:
                # 既存商品の場合、取得できた項目で更新 (AIによる説明文などは上書きしない)
                existing_row = updated_products[jan_code]
                if not existing_row.get('name'): existing_row['name'] = item.get('name', '')
                if not existing_row.get('brand'): existing_row['brand'] = normalize_brand(item.get('brand', ''), brands_map)
                if not existing_row.get('img'): existing_row['img'] = item.get('image', '')
                if not existing_row.get('rak') and item.get('url', '').startswith('http') and 'rakuten' in item.get('url', ''):
                    existing_row['rak'] = item.get('url', '')
                if not existing_row.get('amz') and item.get('url', '').startswith('http') and 'amazon' in item.get('url', ''):
                    existing_row['amz'] = item.get('url', '')
                if not existing_row.get('yah') and item.get('url', '').startswith('http') and 'yahoo' in item.get('url', ''):
                    existing_row['yah'] = item.get('url', '')

    # JANコード順でソートして出力
    final_products_list = sorted(list(updated_products.values()), key=lambda x: x.get('jan', ''))

    # products.csvへの書き出し
    with open(PRODUCT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=final_fieldnames) # fieldnamesをfinal_fieldnamesに修正
        writer.writeheader()
        writer.writerows(final_products_list)

    print(f"\nSuccessfully updated/created '{PRODUCT_CSV}' with {len(final_products_list)} product entries.")
    print("💡 この後、`python3 csv_to_json.py` を実行してWeb用のJSONをビルドしてください。")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用法: python3 jan_data_collector.py [JANコードリストCSVファイルパス]")
        print("  例: python3 jan_data_collector.py my_jans.csv")
        sys.exit(1)
    
    jan_file = sys.argv[1]
    main(jan_file)
