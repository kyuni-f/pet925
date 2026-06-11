#!/usr/bin/env python3
import os
import sys
import json
import csv
import io
import requests
import time

def load_env():
    """.envファイルから環境変数を手動で読み込む（標準ライブラリのみ）"""
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() == "GEMINI_API_KEY":
                        # 前後の空白や引用符 (" または ') を取り除く
                        return value.strip().strip("'").strip('"')
    return os.getenv("GEMINI_API_KEY")

API_KEY = load_env()

if not API_KEY:
    print("❌ エラー: 環境変数 GEMINI_API_KEY が設定されていません。")
    print("💡 解決策: .envファイルに GEMINI_API_KEY=あなたのキー と書き込むか、")
    print("   ターミナルで 'export GEMINI_API_KEY=取得したキー' を実行してください。")
    sys.exit(1)

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
    model_name = "gemini-2.0-flash"
    api_url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={API_KEY}"
    
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
        print("-" * 30)
        print(result_csv)
        print("-" * 30)
        print(f"✅ データ生成に成功しました！上記CSVをコピーして pet925_master.ods の products シートに貼り付けてください。")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")