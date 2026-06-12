#!/usr/bin/env python3
import requests
import os

def get_rakuten_config():
    """ IDの読み込み元を特定しながら取得する """
    config = {"app_id": None, "access_key": None}
    
    # 実行場所に関わらず、スクリプトと同じディレクトリの .env を探す
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
                    if key.strip() == "RAKUTEN_APP_ID":
                        config["app_id"] = value.strip().strip("'").strip('"')
                        source = ".envファイル"
                    elif key.strip() == "RAKUTEN_ACCESS_KEY":
                        config["access_key"] = value.strip().strip("'").strip('"')
    
    # ファイルになければシステム環境変数をチェック
    if not config["app_id"]:
        config["app_id"] = os.getenv("RAKUTEN_APP_ID")
        if config["app_id"]: source = "ターミナル環境変数 (export)"
    if not config["access_key"]:
        config["access_key"] = os.getenv("RAKUTEN_ACCESS_KEY")

    return config["app_id"], config["access_key"], source

app_id, access_key, id_source = get_rakuten_config()

print(f"--- 楽天API 接続診断 ---")

if not app_id:
    print("❌ エラー: .env ファイルに RAKUTEN_APP_ID が設定されていません。")
else:
    print(f"📂 読み込み元: {id_source}")

    print(f"📡 アプリケーションID: {app_id}")
    print(f"🔑 アクセスコード: {'設定済み' if access_key else '❌ 未設定'}")

    if not access_key:
        print("🛑 エラー: RAKUTEN_ACCESS_KEY が .env に設定されていません。")

    # テスト用のJANコード
    test_jan = "4902418803128"
    
    # 2026年最新仕様: ヘッダー認証方式
    url = f"https://app.rakuten.co.jp/services/api/IchibaItem/Search/20260401"
    headers = {
        "X-Rakuten-Application-Id": app_id.strip(),
        "X-Rakuten-Application-Secret": access_key.strip() if access_key else ""
    }
    params = {
        "format": "json",
        "keyword": test_jan,
        "hits": 1
    }

    print(f"🔍 2026年最新ヘッダー認証でリクエストを送信中... (JAN: {test_jan})")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"📡 ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "Items" in data and len(data["Items"]) > 0:
                item = data["Items"][0]["Item"]
                print(f"✅ 成功！商品が見つかりました:")
                print(f"   商品名: {item['itemName'][:50]}...")
                print(f"   画像URL: {item['mediumImageUrls'][0]['imageUrl']}")
            else:
                print("⚠️ 通信は成功しましたが、該当する商品は見つかりませんでした。")
        else:
            print(f"❌ APIエラー: {response.text}")
    except Exception as e:
        print(f"❌ 通信エラーが発生しました: {e}")