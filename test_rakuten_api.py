#!/usr/bin/env python3
import requests
import os
import json
import time

COLOR_YELLOW = '\033[33m'
COLOR_RESET = '\033[0m'

def get_rakuten_config():
    """ IDの読み込み元を特定しながら取得する """
    config = {"app_id": None, "access_key": None}
    use_api_for_images = True # デフォルトはAPI使用
    # 実行場所に関わらず、スクリプトと同じディレクトリの .env を探す
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    source = f"未設定 (検索先: {env_path})"

    # 2026年仕様: まずシステム環境変数 (export) を最優先にチェックする
    config["app_id"] = os.getenv("RAKUTEN_APP_ID")
    config["access_key"] = os.getenv("RAKUTEN_ACCESS_KEY")
    if os.getenv("USE_RAKUTEN_API_FOR_IMAGES"):
        use_api_for_images = os.getenv("USE_RAKUTEN_API_FOR_IMAGES").lower() == "true"
    
    if config["app_id"] and config["access_key"]:
        return config["app_id"], config["access_key"], use_api_for_images, "ターミナル環境変数 (export)"

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                # コメント部分（#以降）を除去
                line = line.split('#')[0].strip()
                if not line:
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key_clean = key.strip()
                    val_clean = value.strip().strip("'").strip('"')
                    if key_clean == "RAKUTEN_APP_ID":
                        config["app_id"] = val_clean
                        source = ".envファイル"
                    elif key_clean in ["RAKUTEN_ACCESS_KEY", "RAKUTEN_APPLICATION_SECRET"]:
                        config["access_key"] = val_clean
                    elif key_clean == "USE_RAKUTEN_API_FOR_IMAGES":
                        use_api_for_images = val_clean.lower() == "true"
    

    return config["app_id"], config["access_key"], use_api_for_images, source

app_id, access_key, use_api_for_images, id_source = get_rakuten_config()

print(f"--- 楽天API 接続診断 ---")

if not app_id: # RAKUTEN_APP_ID が設定されていない場合のメッセージを修正
    print("🛑 エラー: RAKUTEN_APP_ID が設定されていません。")
elif not access_key: # access_key が設定されていない場合のメッセージを追加
    print("🛑 エラー: RAKUTEN_ACCESS_KEY が設定されていません。")
else:
    # テスト用のJANコード
    test_jan = "4902418803128"
    
    # 2026年最新統合ゲートウェイ: 日付(20170706等)を含まない互換パスを使用
    url = "https://app.rakuten.co.jp/services/api/IchibaItem/Search"

    params = {
        "keyword": test_jan,
        "hits": 1,
        "format": "json"
    }
    
    headers = {
        "Authorization": f"Bearer {access_key.strip()}",
        "User-Agent": "Mozilla/5.0 pet925-search-engine/1.0"
    }

    print(f"🔍 2026年最新統合ゲートウェイ (Bearer認証・バージョン日付なし) で送信中... (JAN: {test_jan})")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10) # headersは空の辞書を渡す
        print(f"📡 ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            items = data.get("Items", [])
            if items:
                item = items[0].get("Item")
                print(f"✅ 成功！商品が見つかりました:")
                print(f"   商品名: {item.get('itemName')[:50]}...")
                print(f"   画像URL: {item.get('mediumImageUrls', [{}])[0].get('imageUrl')}")
            else:
                print("⚠️ 通信は成功しましたが、該当する商品は見つかりませんでした。")
        else:
            print(f"❌ APIエラー: {response.text}")
    except Exception as e:
        print(f"❌ 通信エラーが発生しました: {e}")