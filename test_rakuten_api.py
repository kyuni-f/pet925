#!/usr/bin/env python3
import requests
import os

def load_rakuten_id():
    """ .envファイルから RAKUTEN_APP_ID を堅牢に読み込む """
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() == "RAKUTEN_APP_ID":
                        return value.strip().strip("'").strip('"')
    return None

app_id = load_rakuten_id()

if not app_id:
    print("❌ エラー: .env ファイルに RAKUTEN_APP_ID が設定されていません。")
else:
    # テスト用のJANコード（以前エラーが出た商品）
    test_jan = "4902418803128"
    url = f"https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706?format=json&keyword={test_jan}&applicationId={app_id}&hits=1"

    # デバッグ情報：IDが正しく読み込めているか確認（セキュリティのため一部伏せ字）
    if app_id:
        masked_id = app_id[:4] + "*" * (len(app_id) - 8) + app_id[-4:] if len(app_id) > 8 else "****"
        print(f"ID確認: {masked_id} (長さ: {len(app_id)}文字)")
    else:
        print("ID確認: 読み込み失敗")

    print(f"🔍 楽天APIにリクエストを送信中... (JAN: {test_jan})")
    
    try:
        response = requests.get(url, timeout=10)
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