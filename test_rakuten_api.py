#!/usr/bin/env python3
import os
import requests
import json
import time

COLOR_YELLOW = "\033[93m"
COLOR_RESET = "\033[0m"

def get_rakuten_config():
    """ 認証用の環境設定を環境変数または.envファイルから取得する """
    config = {"app_id": None, "access_key": None, "use_api_for_images": "false"}

    # 1. まずはシステム環境変数（export）を最優先でチェック
    if os.getenv("RAKUTEN_APP_ID"):
        config["app_id"] = os.getenv("RAKUTEN_APP_ID")
    if os.getenv("RAKUTEN_ACCESS_KEY"):
        config["access_key"] = os.getenv("RAKUTEN_ACCESS_KEY")
    if os.getenv("USE_RAKUTEN_API_FOR_IMAGES"):
        config["use_api_for_images"] = os.getenv("USE_RAKUTEN_API_FOR_IMAGES").lower()

    if config["app_id"] and config["access_key"]:
        return config["app_id"], config["access_key"], config["use_api_for_images"], "ターミナル環境変数 (export)"

    # 2. 環境変数がなければ .env ファイルを探索
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    source = f"未設定 (検索先: {env_path})"

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key_clean = key.strip()
                    val_clean = value.strip().strip('"').strip("'")

                    if key_clean == "RAKUTEN_APP_ID":
                        config["app_id"] = val_clean
                        source = ".envファイル"
                    elif key_clean in ["RAKUTEN_ACCESS_KEY", "RAKUTEN_APPLICATION_SECRET"]:
                        config["access_key"] = val_clean
                    elif key_clean == "USE_RAKUTEN_API_FOR_IMAGES":
                        config["use_api_for_images"] = val_clean.lower()

    return config["app_id"], config["access_key"], config["use_api_for_images"], source


# --- メイン処理開始 ---
app_id, access_key, use_api_for_images, id_source = get_rakuten_config()

print(f"--- 楽天API接続準備 (読込元: {id_source}) ---")

if not app_id:
    print("【エラー】RAKUTEN_APP_ID が設定されていません。")
elif not access_key:
    print("【エラー】RAKUTEN_ACCESS_KEY が設定されていません。")
else:
    # テスト用のJANコード（13桁）
    test_jan = "4902418803128"

    # ⭕ 2026年最新のマイクロサービス版URL
    url = "https://rakuten.co.jp"

    params = {
        "keyword": test_jan,
        "hits": 1,
        "format": "json"
    }

    YOUR_REGISTERED_DOMAIN = "https://kyuni-f.github.io/pet925/"  # ←ご自身の登録ドメインに書き換えてください

    headers = {
        "Authorization": access_key.strip(),
        "X-Rakuten-Application-Id": app_id.strip(),
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": YOUR_REGISTERED_DOMAIN,
        "Referer": YOUR_REGISTERED_DOMAIN + "/"
    }

    print(f" 楽天市場 総合商品検索API へ接続中... (JAN: {test_jan})")

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print(f" ステータスコード: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            # RAP Native API は 'items' (小文字) で返し、Item ラッパーがない構造が標準です
            items = data.get("items") or data.get("Items", [])
            if items:
                for entry in items:
                    item = entry.get("Item") if isinstance(entry, dict) and "Item" in entry else entry
                    item_name = item.get("itemName") or item.get("name") or "商品名なし"
                    print(f" 成功: 商品が見つかりました！")
                    print(f" 商品名: {item_name[:50]}...")

                    # 画像URLの取得 (RAP Native の構造に対応)
                    image_url = item.get("image_url") or item.get("medium_image_urls", [None])[0] or item.get("mediumImageUrls", [{}])[0].get("imageUrl")
                    if image_url:
                        print(f" 画像URL: {image_url}")
                    else:
                        print(" ⚠️ 商品はありましたが、画像URLが見つかりませんでした。")
            else:
                print(" ⚠️ 通信は成功しましたが、該当する商品は見つかりませんでした。")
        else:
            print(f"❌ APIエラー: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ 通信エラーが発生しました: {e}")