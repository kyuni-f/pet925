#!/usr/bin/env python3
import os
import sys
import json
import csv
import io
import urllib.request
import urllib.error

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
        instructions = "CSV 15列形式で出力してください。"

    # --- 診断モード：利用可能なモデルを一覧表示 ---
    if "--list-models" in sys.argv:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
        try:
            with urllib.request.urlopen(list_url) as response:
                res_data = json.loads(response.read().decode("utf-8"))
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
    
    prompt = f"{instructions}\n\n【解析対象URL】\n{target_url}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(api_url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    
    print(f"🔍 解析中: {target_url}...")
    # デバッグ用：アクセス先を表示（キーの末尾4文字だけ表示して確認）
    safe_url = api_url.replace(API_KEY, "*" * (len(API_KEY)-4) + API_KEY[-4:])
    # print(f"DEBUG: Request to {safe_url}") 

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            
            if "candidates" in res_data and len(res_data["candidates"]) > 0:
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                # コードブロックを除去
                csv_line = text.replace("```csv", "").replace("```", "").strip()
                return csv_line
            else:
                raise Exception("AIからの応答を解析できませんでした。")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            err_json = json.loads(error_body)
            message = err_json.get("error", {}).get("message", "不明なエラー")
            if "not found" in message.lower():
                # エラーが起きたURLを特定しやすくするために詳細を表示
                debug_info = f"\n   - 接続先: {api_url.split('?')[0]}"
                debug_info += f"\n   - モデル: {model_name}"
                custom_msg = f"\n\n💡 ヒント: Googleのサーバーが指定のモデルを受け付けていません。"
                custom_msg += f"\n   → Google AI Studio で『Create API key in new project』から新しいキーを作成するか、"
                custom_msg += f"\n     --list-models で利用可能なモデルを確認し、スクリプトの model_name を更新してください。"
                raise Exception(f"APIエラー ({e.code}): {message}{debug_info}{custom_msg}")
            elif e.code == 503:
                raise Exception(f"APIエラー ({e.code}): サービスが一時的に利用できません。時間をおいて再試行してください。")
            else:
                raise Exception(f"APIエラー ({e.code}): {message}")
        except:
            raise Exception(f"HTTPエラー ({e.code}): {error_body}")

def append_to_csv(csv_line, file_path="data/products.csv"):
    """
    生成されたCSV行を既存のファイルに追記する
    """
    if not csv_line:
        return
    
    # 正確なバリデーション (引用符内のカンマを考慮)
    f_input = io.StringIO(csv_line)
    reader = csv.reader(f_input)
    row = next(reader, [])

    if len(row) < 15:
        print(f"⚠️ 列数が足りません ({len(row)}列検出 / 15列必要)。追記をスキップしました。")
        print(f"内容: {csv_line}")
        return

    with open(file_path, "a", encoding="utf-8-sig") as f:
        # ファイルが空でない場合、末尾が改行で終わっているか確認して、必要なら改行を追加
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, "rb+") as f_check:
                f_check.seek(-1, os.SEEK_END)
                if f_check.read(1) != b'\n':
                    f.write("\n")
        f.write(csv_line.strip() + "\n")
    print(f"✅ 追記に成功しました！")
    print(f"📍 保存先: {os.path.abspath(file_path)}")
    print(f"💡 ヒント: LibreOfficeなどで開いている場合は、一度閉じて開き直すと反映されます。")

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
        
        confirm = input("このデータを追記しますか？ (y/n): ")
        if confirm.lower() == 'y':
            append_to_csv(result_csv)
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")