#!/usr/bin/env python3
import os
import sys
import json
import csv
import io
import requests
import time

def load_config():
    """.envファイルから環境変数を読み込む"""
    config = {}
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip().strip("'").strip('"')
    return config

config = load_config()
API_KEY = config.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
RAKUTEN_APP_ID = config.get("RAKUTEN_APP_ID")

if not API_KEY:
    print("❌ エラー: 環境変数 GEMINI_API_KEY が設定されていません。")
    print("💡 解決策: .envファイルに GEMINI_API_KEY=あなたのキー と書き込むか、")
    print("   ターミナルで 'export GEMINI_API_KEY=取得したキー' を実行してください。")
    sys.exit(1)

def fetch_rakuten_official_data(jan):
    """楽天APIを使用して、JANコードから公式の商品名と画像URLを取得する"""
    if not RAKUTEN_APP_ID or not jan or jan == '#':
        return None
    
    url = f"https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706?format=json&keyword={jan}&applicationId={RAKUTEN_APP_ID}&hits=1"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if "Items" in data and len(data["Items"]) > 0:
            item = data["Items"][0]["Item"]
            return {
                "name": item.get("itemName"),
                "image": item.get("mediumImageUrls", [{}])[0].get("imageUrl")
            }
    except:
        return None

def fetch_product_data(target_url):
    """
    URLから商品情報を読み取り、AI_INSTRUCTIONSに基づいたCSV行を生成する
    """
    # 指示書の読み込み
    try:
        with open("docs/AI_INSTRUCTIONS.md", "r", encoding="utf-8") as f:
            instructions = f.read()
    except FileNotFoundError:
        instructions = "CSV 16列形式で出力してください。"

    # --- 診断モード：利用可能なモデルを一覧表示 ---
    if "--list-models" in sys.argv:
        list_url = f"https://generativelanguage.googleapis.com/v1/models?key={API_KEY}"
        try:
            response = requests.get(list_url)
            response.raise_for_status()
            res_data = response.json()
            print("\n📋 利用可能なモデル一覧:")
            for m in res_data.get("models", []):
                print(f"  - {m['name'].replace('models/', '')}")
            sys.exit(0)
        except Exception as e:
            print(f"❌ モデル一覧の取得に失敗しました: {e}")
            sys.exit(1)

    # --- API 設定 ---
    # 404エラー（見つからない）を回避するため、一覧で確認できたモデル名に変更します。
    # --list-models で表示された一覧の中から、使いたいモデル名を正確に指定してください
    model_name = "gemini-2.5-flash"
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
    
    # 補助データの読み込み（AIに判断基準を与える）
    def load_context_csv(path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8-sig") as f:
                return f.read()
        return "ファイルが見つかりません"

    tags_context = load_context_csv("data/tags.csv")
    brands_context = load_context_csv("data/brands.csv")

    csv_header = "name,brand,tags,desc,size,jan,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p"
    
    prompt = f"""{instructions}

【許可タグリスト (data/tags.csv)】\n{tags_context}
【ブランドリスト (data/brands.csv)】\n{brands_context}

【重要】必ず以下の16列のCSV形式で出力してください。ヘッダー行も必ず含めてください。
【商品名の抽出ルール】URL先のページタイトルやH1タグから商品名を探してください。
楽天市場特有の「【...】」で囲まれた宣伝文句や「ポイント〇倍」などはすべて削除し、「ブランド名＋製品名＋種類」の純粋な正式名称のみを抽出してください。
【商品説明の抽出ルール】
商品特徴を60文字程度でまとめ、メーカーのこだわりや「どんな悩みを持つ犬・猫におすすめか」というユーザー視点を必ず含めてください。機械的な羅列ではなく、自然で魅力的な「読み物」としての品質を維持してください。
【JANコード】わかる場合はjan列に13桁の数値を入力してください。不明な場合は # を入力してください。

\n{csv_header}\n\n【解析対象URL】\n{target_url}"""
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"🔍 解析中: {target_url}...")
    
    max_retries = 3
    retry_delay_seconds = 5

    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 503:
                if attempt < max_retries - 1:
                    print(f"⚠️ 503エラー検出。{retry_delay_seconds}秒後に再試行します...")
                    time.sleep(retry_delay_seconds)
                    retry_delay_seconds *= 2
                    continue
            
            response.raise_for_status()
            res_data = response.json()

            if "candidates" in res_data and len(res_data["candidates"]) > 0:
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                csv_line = text.replace("```csv", "").replace("```", "").strip()
                return csv_line
            else:
                raise Exception("AIからの応答を解析できませんでした。")

        except requests.exceptions.RequestException as e:
            raise Exception(f"APIリクエストエラー: {e}")

    raise Exception(f"APIリクエストが最大試行回数 ({max_retries}回) を超えても成功しませんでした。")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用法:")
        print("  1. 解析実行: python3 auto_data_collector.py [商品URL]")
        print("  2. 診断モード: python3 auto_data_collector.py --list-models")
        sys.exit(1)
    
    target_url = sys.argv[1]
    try:
        result_csv = fetch_product_data(target_url)
        
        # 生成されたCSVを解析して、JANコードがあれば楽天APIで「正式データ」に補正する
        f = io.StringIO(result_csv)
        reader = list(csv.DictReader(f))
        
        if reader:
            row = reader[0]
            jan = row.get("jan", "#")
            official = fetch_rakuten_official_data(jan)
            
            if official:
                print(f"✨ 楽天APIから公式データを取得しました: {official['name'][:30]}...")
                # AIが要約してしまった名前を「公式名称」に差し替え
                row["name"] = official["name"]
                # 画像URLも「確定URL」に差し替え（これでビルド時の推測リスト化を防ぐ）
                row["img"] = official["image"]
            
            # 修正後のデータをCSV文字列に戻す
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=row.keys())
            writer.writeheader()
            writer.writerow(row)
            result_csv = output.getvalue()

        print("-" * 30)
        print(result_csv)
        print("-" * 30)
        print(f"✅ 楽天API連携済みのデータ生成に成功しました！")
        print(f"💡 これを pet925_master.ods に貼り付けると、画像表示の失敗やコンソールの重複ロードが解消されます。")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")