import csv
import json
import os
import unicodedata
import sys
import re
import datetime
import time
import concurrent.futures
import difflib
import requests
import random
from urllib.parse import unquote



# 設定
DATA_DIR = 'data'  # CSVファイルが格納されているディレクトリ
PRODUCT_CSV = os.path.join(DATA_DIR, 'products.csv')
CAT_CSV = os.path.join(DATA_DIR, 'categories.csv')
TAG_CSV = os.path.join(DATA_DIR, 'tags.csv')
RULE_CSV = os.path.join(DATA_DIR, 'rules.csv')

OUTPUT_JSON = 'product_data.json'
CHUNK_SIZE = 5000  # 1ファイルあたりの最大件数
OUTPUT_MASTER_JS = 'data_master.js'

# 画像自動生成に使用するデフォルトの楽天ショップIDリスト
# これらのショップが cabinet/jan/ 形式を採用している場合、JANコードから画像を自動生成します。
# 優先度の高い順に並べてください。
DEFAULT_RAKUTEN_IMAGE_SHOPS = [
    'rakuten24',         # 楽天24 (大手でJANコード管理がしっかりしている可能性が高い)
    'petgo',             # ペットゴー (ペット用品大手、自社物流)
    'chanet',            # チャーム (ペット用品最大手、JAN画像あり)
    'pet-kan',           # ペット館 (ペット用品大手)
    'pet-gardeninglife', # チャーム（別ID・ペットガーデニングライフ）
    'net-baby',          # ネットベビー
]

# 楽天API・アフィリエイト設定の読み込み
def load_rakuten_config():
    config = {
        "app_id": None, 
        "access_key": None, 
        "affiliate_id": None, 
        "use_api_for_images": True,
        "traditional_app_id": None,
        "yahoo_client_id": None
    }
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")

    # ターミナル環境変数を最優先
    config["app_id"] = os.getenv("RAKUTEN_APP_ID")
    config["access_key"] = os.getenv("RAKUTEN_ACCESS_KEY")
    config["affiliate_id"] = os.getenv("RAKUTEN_AFFILIATE_ID")
    config["traditional_app_id"] = os.getenv("RAKUTEN_TRADITIONAL_APP_ID")
    config["yahoo_client_id"] = os.getenv("YAHOO_CLIENT_ID")
    if os.getenv("USE_RAKUTEN_API_FOR_IMAGES"): 
        config["use_api_for_images"] = os.getenv("USE_RAKUTEN_API_FOR_IMAGES").lower() == "true"
    
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
                    elif key.strip() == "RAKUTEN_AFFILIATE_ID":
                        config["affiliate_id"] = val_clean
                    elif key_clean == "USE_RAKUTEN_API_FOR_IMAGES":
                        config["use_api_for_images"] = val_clean.lower() == "true"
    return config

rak_config = load_rakuten_config()
RAKUTEN_APP_ID = rak_config["app_id"]
RAKUTEN_ACCESS_KEY = rak_config["access_key"]
RAKUTEN_AFFILIATE_ID = rak_config["affiliate_id"]
RAKUTEN_TRADITIONAL_APP_ID = rak_config["traditional_app_id"]
YAHOO_CLIENT_ID = rak_config["yahoo_client_id"]

# Google Custom Search API の設定読み込み
def load_google_config():
    config = {"cx": None, "api_key": None}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")

    # ターミナル環境変数を最優先
    config["cx"] = os.getenv("GOOGLE_CSE_ID")
    config["api_key"] = os.getenv("GOOGLE_API_KEY")
    
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.split('#')[0].strip()
                if not line: continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key_clean = key.strip()
                    val_clean = value.strip().strip("'").strip('"')
                    if key_clean == "GOOGLE_CSE_ID":
                        config["cx"] = val_clean
                    elif key_clean == "GOOGLE_API_KEY":
                        config["api_key"] = val_clean
    return config

google_config = load_google_config()
GOOGLE_CSE_ID = google_config["cx"]
GOOGLE_API_KEY = google_config["api_key"]

# CSVファイル名と、それがdata_master.jsでどの変数名になるかのマッピング
# products.csv は特別扱いなのでここには含めない
SPECIFIC_MASTER_CSVS = {
    'categories.csv', 'tags.csv', 'rules.csv'
}


# ターミナル出力用の色設定
COLOR_RED = '\033[31m'
COLOR_GREEN = '\033[32m'
COLOR_YELLOW = '\033[33m'
COLOR_CYAN = '\033[36m'
COLOR_BOLD = '\033[1m'
COLOR_RESET = '\033[0m'

validation_errors = []
validation_warnings = []

def normalize_text(s):
    """JS版のnormalizeと動作を合わせる（NFKC正規化 + ひらがなをカタカナへ）"""
    if not s: return ""
    s = unicodedata.normalize('NFKC', str(s))
    # ひらがな (U+3041-3096) を カタカナ (U+30A1-30F6) に変換 (+0x60)
    chars = []
    for char in s:
        cp = ord(char)
        if 0x3041 <= cp <= 0x3096:
            chars.append(chr(cp + 0x60))
        else:
            chars.append(char)
    s = "".join(chars).lower()
    return re.sub(r'\s+', ' ', s).strip() # 連続する空白を1つに統合

def load_csv_simple(path):
    if not os.path.exists(path): return []
    with open(path, 'r', encoding='utf-8-sig') as f:
        return list(csv.reader(f))

def load_csv_dict_list(path):
    """ヘッダーを持つCSVを読み込み、辞書のリストとして返す"""
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8-sig', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        return list(reader)

# NG ワード（これらが API の商品名に含まれていたら除外）
_API_FORBIDDEN_WORDS = [
    "セット", "ケース", "まとめ買い", "まとめ", "箱", "ボックス",
    "set", "case", "box", "pack", "パック",
    "24本", "48本", "12本", "6本",  # 本数入りセット商品を除外
    "12袋", "×12", "x12", "500g×", "500g x", "個包装", "小分け包装", "小分け",
]

# 箱売り・容量違いを検出（500g×12袋 等）
_BULK_PACK_RE = re.compile(
    r'500\s*g\s*[×x✕]\s*12|500\s*g\s*×\s*12\s*袋|6\s*kg\s*[\(（].*12',
    re.IGNORECASE,
)

# 「1歳」と「11歳」を区別するため、直前に数字がない N歳 のみを抽出
_AGE_TOKEN_RE = re.compile(r'(?<!\d)(\d+)歳')
_AGE_FROM_RE = re.compile(r'(?<!\d)(\d+)歳から')
_KG_VALUE_RE = re.compile(r'(\d+(?:\.\d+)?)\s*kg', re.IGNORECASE)


def _extract_age_numbers(text: str) -> set:
    """テキストから年齢数字を抽出（例: '11歳から' → {'11'}、'1' は含めない）"""
    if not text:
        return set()
    return set(_AGE_TOKEN_RE.findall(text))


def _extract_kg_values(text: str) -> set:
    """テキストから kg 表記を抽出（'3kg' → {'3'}）"""
    if not text:
        return set()
    norm = normalize_text(text)
    vals = _KG_VALUE_RE.findall(norm)
    res = set()
    for v in vals:
        try:
            # 2 と 2.0 が一致するように float に変換して丸める
            res.add(str(float(v)))
        except ValueError:
            res.add(v)
    return res


def _get_api_item_text(item: dict) -> str:
    """API商品のメイン名＋サブ文字（キャプション等）を結合して返す"""
    if not isinstance(item, dict):
        return ""
    parts = [
        item.get("itemName") or item.get("item_name") or "",
        item.get("itemCaption") or item.get("item_caption") or "",
        item.get("catchcopy") or "",
        item.get("itemSpec") or item.get("item_spec") or "",
    ]
    return " ".join(p for p in parts if p).strip()


def _text_has_exact_age(text: str, age_num: str) -> bool:
    """指定年齢が単独トークンとして含まれるか（'1' が '11歳' に誤マッチしない）"""
    if not text or not age_num:
        return False
    return bool(re.search(rf'(?<!\d){re.escape(age_num)}歳', normalize_text(text)))


def _keyword_matches_text(keyword: str, text: str) -> bool:
    """キーワード照合。年齢・英数字コードは厳密な境界マッチを使う。"""
    norm_kw = normalize_text(keyword)
    norm_text = normalize_text(text)
    age_in_kw = _AGE_TOKEN_RE.search(norm_kw)
    if age_in_kw:
        return _text_has_exact_age(text, age_in_kw.group(1))
    # MCA-24 等の商品コードは部分一致（MCA-2 等）を防ぐ
    if re.fullmatch(r'[a-z0-9\-]+', norm_kw):
        return bool(re.search(rf'(?<![a-z0-9\-]){re.escape(norm_kw)}(?![a-z0-9\-])', norm_text))
    return norm_kw in norm_text


def _is_api_item_valid(
    api_item_text: str,
    product_name: str,
    brand_name: str,
    product_size: str = "",
) -> bool:
    """
    楽天 API から返ってきた商品テキストが、元の CSVデータと合致しているか簡易判定する。

    - 禁止ワードが含まれていれば除外
    - CSVの商品名・ブランド名から抽出したキーワードが API 商品名に「1つも含まれない」場合は除外
    - 対象年齢（〇歳から）の数字が CSV と API で一致しない場合は除外
    - 容量（kg）が CSV と矛盾する場合は除外
    """
    if not api_item_text or not api_item_text.strip():
        return False

    api_name_norm = normalize_text(api_item_text)

    # ① 禁止ワードチェック（元の形 + 正規化後、両方でチェック）
    for fw in _API_FORBIDDEN_WORDS:
        if fw in api_item_text or normalize_text(fw) in api_name_norm:
            return False
    if _BULK_PACK_RE.search(api_item_text):
        return False

    # ② 対象年齢チェック（「1歳」と「11歳」を正確に区別する）
    csv_age_nums = _extract_age_numbers(product_name)
    if csv_age_nums:
        api_age_nums = _extract_age_numbers(api_item_text)
        # API側に年齢表記があるのに、CSV側と1つも一致しなければ除外
        if api_age_nums and csv_age_nums.isdisjoint(api_age_nums):
            return False

        # CSV が「N歳から」と明示している場合、API 側（サブ文字含む）にも同じ年齢の明示が必須
        required_from_ages = set(_AGE_FROM_RE.findall(product_name))
        if required_from_ages and not required_from_ages.issubset(api_age_nums):
            return False

    # ②-b 容量チェック（1歳3kg 商品に 11歳6kg 箱セットが部分一致で通るのを防ぐ）
    csv_kgs = _extract_kg_values(product_size)
    api_kgs = _extract_kg_values(api_item_text)
    if csv_kgs and api_kgs and csv_kgs.isdisjoint(api_kgs):
        return False

    # ③ ブランド名や商品名からキーワードを抽出して照合
    def extract_keywords(text):
        norm = normalize_text(text)
        tokens = re.split(r'[\s・/\-_,()（）【】\[\]]+', norm)
        return [t for t in tokens if len(t) >= 2] # 3文字以上から2文字以上に条件を緩和

    csv_keywords = extract_keywords(product_name) + extract_keywords(brand_name)
    if not csv_keywords:
        return True

    # サブ文字列1件一致では不十分。複数キーワードの過半数一致を要求 → 1/3以上のキーワードが一致すればOKに緩和
    matched = sum(1 for kw in csv_keywords if _keyword_matches_text(kw, api_item_text))
    min_required = max(1, len(csv_keywords) // 3)
    return matched >= min_required


# ===== Layer 1: 画像URL パターン検査 =====

# これらのパスが URL に含まれていたらロゴ・宣伝用画像の可能性が高い → スコアを下げる
_IMAGE_URL_BAD_PATTERNS = [
    "/logo/", "/banner/", "/promo/", "/promotion/", "/campaign/",
    "/header/", "/footer/", "/top/",
    "_logo", "logo_", "_banner", "banner_",
    "free_ship", "freeship", "送料無料",
    "point", "coupon", "sale_", "_sale",
    "tokubai",   # 特売
    "osusume",   # おすすめ帯
    "ranking",
]

# 特定ショップのロゴ入り・宣伝画像（pet oukoku 等）→ 即除外レベルの大減点
_IMAGE_URL_SHOP_EXCLUDE_PATTERNS = [
    "pet-oukoku",
    "petoukoku",
    "pet_oukoku",
    "pet oukoku",
    "petoukokupremium",
    "/@0_mall/pet-oukoku/",
]

# /cabinet/ 以下でも JAN 管理以外（item/shop 等）はショップロゴ合成の可能性大
_IMAGE_URL_NON_JAN_CABINET_RE = re.compile(
    r'/@0_mall/[^/]+/cabinet/(?!jan/)',
    re.IGNORECASE,
)

# これらのパスが URL に含まれていたら正規の商品画像の可能性が高い → スコアを上げる
_IMAGE_URL_GOOD_PATTERNS = [
    "/cabinet/jan/",   # JANコード管理画像（最も信頼性高）
    "/item/",          # 商品個別画像
    "/product/",
    "thumbnail.image.rakuten.co.jp",  # 楽天画像CDN（商品画像が集中）
    "r.r10s.jp",       # 楽天商品画像CDN（高品質・カタログ画像）
]


def _score_image_url(url: str, product_name: str = "") -> int:
    """
    画像URLのパターンから「クリーンな商品画像らしさ」をスコアリングする。

    Returns:
        int: スコア値。高いほど商品パッケージのみのクリーンな画像である可能性が高い。
             NG パターンにヒットすると -10 の大きなペナルティ。
    """
    if not url:
        return 0
    url_lower = url.lower()
    score = 0

    for shop_bad in _IMAGE_URL_SHOP_EXCLUDE_PATTERNS:
        if shop_bad.lower() in url_lower:
            return -100  # ショップロゴ入り画像は即除外

    # 楽天ショップの cabinet/item 等（JAN管理外）はロゴ合成画像になりやすい
    if _IMAGE_URL_NON_JAN_CABINET_RE.search(url):
        score -= 2 # 50から2に大幅緩和して、JAN管理画像を優先するだけに留める。

    for bad in _IMAGE_URL_BAD_PATTERNS:
        if bad.lower() in url_lower:
            score -= 10  # NG パターン1件につき大きなペナルティ

    for good in _IMAGE_URL_GOOD_PATTERNS:
        if good.lower() in url_lower:
            score += 5   # Good パターン1件につきボーナス

    # URL 内の年齢表記が CSV 商品名と矛盾する場合も大減点
    if product_name:
        url_ages = _extract_age_numbers(unquote(url))
        csv_ages = _extract_age_numbers(product_name)
        if csv_ages and url_ages and csv_ages.isdisjoint(url_ages):
            score -= 100

    return score


def fetch_rakuten_product_data_v2(jan):
    """
    楽天商品検索API（マイクロサービス版 商品（Product）Search）を使用して、
    白バックのきれいな公式カタログ画像を取得する。
    同じRAKUTEN_APP_IDで利用可能（別途 traditional_app_id 不要）。
    """
    if not RAKUTEN_APP_ID or jan == '#' or not RAKUTEN_ACCESS_KEY:
        return None
    
    # ⭕ 2026年 マイクロサービス版 Product Search API
    url = "https://openapi.rakuten.co.jp/ichibaproduct/api/Product/Search/20250801"
    params = {
        "applicationId": RAKUTEN_APP_ID.strip(),
        "accessKey": RAKUTEN_ACCESS_KEY.strip(),
        "keyword": jan,
        "format": "json"
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
            products = data.get("Products", [])
            if products and isinstance(products, list) and len(products) > 0:
                first_entry = products[0]
                # レスポンス構造: {"Product": { ... }}
                product = first_entry.get("Product", first_entry) if isinstance(first_entry, dict) else first_entry
                
                # mediumImageUrl または smallImageUrl を取得
                img_url = product.get("mediumImageUrl") or product.get("smallImageUrl")
                if img_url:
                    # パラメータを除去して高画質化
                    high_res_image = re.sub(r"\?_ex=.*$", "", img_url)
                    return high_res_image
    except Exception as e:
        print(f"   ⚠️ 楽天商品検索API(Product)通信エラー: {e}")
    return None


def fetch_rakuten_product_data(jan):
    """楽天商品価格ナビ製品検索API（従来のProduct Search API）を使用して白バックのきれいな公式画像を取得する"""
    if not RAKUTEN_TRADITIONAL_APP_ID or jan == '#' or RAKUTEN_TRADITIONAL_APP_ID == "YOUR_RAKUTEN_TRADITIONAL_APP_ID":
        return None
    url = "https://app.rakuten.co.jp/services/api/Product/Search/20170426"
    params = {
        "applicationId": RAKUTEN_TRADITIONAL_APP_ID.strip(),
        "keyword": jan,
        "format": "json"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            products = data.get("Products", [])
            if products and isinstance(products, list):
                # 最初の製品
                first_prod_entry = products[0]
                if isinstance(first_prod_entry, dict) and "Product" in first_prod_entry:
                    product = first_prod_entry.get("Product", {})
                    img_url = product.get("productImageUrl")
                    if img_url:
                        # パラメータを除去して高画質化
                        high_res_image = re.sub(r"\?_ex=.*$", "", img_url)
                        return high_res_image
        else:
            print(f"   ⚠️ 楽天価格ナビAPIエラー: {resp.status_code}")
    except Exception as e:
        print(f"   ⚠️ 楽天価格ナビAPI通信エラー: {e}")
    return None

def fetch_yahoo_shopping_data(jan):
    """Yahoo!ショッピング商品検索APIを使用してクリアな商品画像を取得する"""
    if not YAHOO_CLIENT_ID or jan == '#' or YAHOO_CLIENT_ID == "YOUR_YAHOO_CLIENT_ID":
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
                        # Yahooの画像URLに含まれるサイズを表すフォルダ文字を「g」(最大・高画質)に変換して高画質化
                        if "/i/c/" in img_url:
                            img_url = img_url.replace("/i/c/", "/i/g/")
                        elif "/i/d/" in img_url:
                            img_url = img_url.replace("/i/d/", "/i/g/")
                        return img_url
        else:
            print(f"   ⚠️ Yahoo!ショッピングAPIエラー: {resp.status_code}")
    except Exception as e:
        print(f"   ⚠️ Yahoo!ショッピングAPI通信エラー: {e}")
    return None

def fetch_rakuten_data(jan, product_name="", brand_name="", product_size=""):
    """楽天APIを使用してJANコードから画像URLを取得する（アフィリエイトリンクは将来用に温存）"""
    if not RAKUTEN_APP_ID or jan == '#' or not RAKUTEN_ACCESS_KEY: return None
    
    # ⭕ 2026年最新のマイクロサービス版URL
    url = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401"
    params = {
        "applicationId": RAKUTEN_APP_ID.strip(),
        "accessKey": RAKUTEN_ACCESS_KEY.strip(),
        "keyword": jan,
        "hits": 5,  # 複数件取得して最適なものを選ぶ
        "format": "json",
        "formatVersion": 2
    }
    if RAKUTEN_AFFILIATE_ID:
        params["affiliateId"] = RAKUTEN_AFFILIATE_ID

    YOUR_REGISTERED_DOMAIN = "https://kyuni-f.github.io/pet925/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": YOUR_REGISTERED_DOMAIN,
        "Referer": YOUR_REGISTERED_DOMAIN + "/"
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 衝突回避のためのジッター待機
            # attempt=0 の時は 0.2〜0.7秒、リトライ毎に待機時間を延ばす
            wait_time = 0.2 + random.uniform(0.1, 0.5) * (attempt + 1)
            time.sleep(wait_time)
            
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items") or data.get("Items", [])
                if not items: return None

                # --- 商品名 & URL パターンフィルタリング: 全候補にスコアを付けて最適な1件を選ぶ ---
                candidates = []  # [(score, raw_image_url), ...]
                for entry in items:
                    item = entry.get("Item") if isinstance(entry, dict) and "Item" in entry else entry
                    if not isinstance(item, dict):
                        continue

                    api_item_text = _get_api_item_text(item)

                    # ① 商品名＋サブ文字の合致チェック（NG ならスキップ）
                    if not _is_api_item_valid(api_item_text, product_name, brand_name, product_size):
                        label = api_item_text[:40] if api_item_text else "(テキストなし)"
                        print(f"   🚫 商品名不一致スキップ: 「{label}」(JAN:{jan})")
                        continue

                    # ② 画像URLの抽出
                    raw_image = None
                    if item.get("image_url"):
                        raw_image = item.get("image_url")
                    else:
                        urls_list = item.get("medium_image_urls") or item.get("mediumImageUrls")
                        if urls_list and isinstance(urls_list, list) and len(urls_list) > 0:
                            first_item = urls_list[0]
                            if isinstance(first_item, dict):
                                raw_image = first_item.get("imageUrl")
                            else:
                                raw_image = first_item

                    if not raw_image:
                        continue

                    # ③ [Layer 1] URL パターンスコアリング
                    url_score = _score_image_url(raw_image, product_name)
                    if url_score < -5:  # NG パターンが強い場合はスキップ
                        print(f"   🚫 ロゴ/宣伝URL スキップ: {raw_image[:60]}... (score={url_score})")
                        continue

                    candidates.append((url_score, raw_image))

                # JAN管理パスの画像を最優先（ロゴ合成の item/ 画像より信頼性が高い）
                jan_path = f"/cabinet/jan/{jan.lower()}"
                jan_candidates = [c for c in candidates if jan_path in c[1].lower()]
                if jan_candidates:
                    candidates = jan_candidates

                # スコアの高い順にソートして最上位を採用
                candidates.sort(key=lambda x: x[0], reverse=True)
                best_image = candidates[0][1] if candidates else None

                if not best_image:
                    return None

                # 画像URLを高画質化 (パラメータ ?_ex=... を削除)
                high_res_image = re.sub(r"\?_ex=.*$", "", best_image)

                return {
                    "image": high_res_image,
                    "url": None # アフィリエイトリンクは取得せず、検索リンクに任せる
                }
            elif resp.status_code == 429:
                if attempt < max_retries - 1:
                    # 429超過時はリトライを促すため長めにスリープ (1.5〜2.5秒)
                    time.sleep(1.5 + random.uniform(0.1, 1.0))
                    continue
                else:
                    print(f"❌ APIレート制限超過 (JAN {jan}): リトライ上限に達しました (429)")
                    return None
            else:
                print(f"⚠️ APIステータスエラー (JAN {jan}): {resp.status_code} - {resp.text[:150]}")
                return None
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1.0 + random.uniform(0.1, 0.5))
                continue
            print(f"⚠️ API接続エラー (JAN {jan}): {e}")
            return None
    return None

def fetch_google_image(jan, brand_name="", product_name=""):
    """Google Custom Search JSON API (image search) を利用してメーカー公式等から単品画像を検索し、ダウンロードしてローカルキャッシュに保存する"""
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        return None

    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
    os.makedirs(cache_dir, exist_ok=True)

    # 既存のキャッシュ画像があるかチェック
    for ext in ["jpg", "jpeg", "png", "webp", "gif"]:
        test_path = os.path.join(cache_dir, f"{jan}.{ext}")
        if os.path.exists(test_path):
            return f"images/{jan}.{ext}"

    # クエリの作成。基本は「ブランド名 + JANコード」または「JANコード + 商品名」など、または単に「JANコード」
    query = f"{brand_name} {jan}".strip() if brand_name else jan
    
    # サーバーに迷惑をかけないよう、APIリクエスト前に3秒ウェイト
    time.sleep(3)

    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "searchType": "image",
        "num": 3  # 上位3件を取得して有効なものを探す
    }

    try:
        resp = requests.get(search_url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items", [])
            if not items:
                # JANコード単体でもう一度試す
                if brand_name:
                    time.sleep(3)
                    params["q"] = jan
                    resp2 = requests.get(search_url, params=params, timeout=10)
                    if resp2.status_code == 200:
                        items = resp2.json().get("items", [])
            
            for item in items:
                img_url = item.get("link")
                if not img_url:
                    continue
                
                # 直リンクは規約違反やブロックのリスクがあるため、絶対に行わずダウンロードしてキャッシュする
                ext = "jpg"
                url_lower = img_url.lower()
                if ".png" in url_lower:
                    ext = "png"
                elif ".webp" in url_lower:
                    ext = "webp"
                elif ".gif" in url_lower:
                    ext = "gif"
                elif ".jpeg" in url_lower:
                    ext = "jpeg"

                dest_filename = f"{jan}.{ext}"
                dest_path = os.path.join(cache_dir, dest_filename)

                # サーバーに迷惑をかけないよう、ダウンロード前に3秒ウェイト
                time.sleep(3)

                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
                    }
                    img_resp = requests.get(img_url, headers=headers, timeout=10)
                    if img_resp.status_code == 200:
                        with open(dest_path, "wb") as f:
                            f.write(img_resp.content)
                        print(f"   📥 Google APIで見つかった画像を保存しました: {img_url} -> images/{dest_filename}")
                        return f"images/{dest_filename}"
                except Exception as ex:
                    print(f"   ⚠️ 画像のダウンロードに失敗しました ({img_url}): {ex}")
                    continue
        else:
            print(f"   ⚠️ Google Custom Search APIエラー: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        print(f"   ⚠️ Google Custom Search API接続エラー: {e}")

    return None

def process_row_task(line_num, row, tag_keywords, tag_to_cat_index, allowed_tags, tag_lookup_for_suggest, rakuten_shop_ids, force_refresh=False):
    """1行分の重い処理を担当するワーカー関数"""
    row_errors = []
    row_warnings = []
    name = row.get('name', '').strip()

    # ヘッダー行そのものがデータとして混入している場合はスキップ
    if name.lower() == 'name' or name == '商品名':
        return None, [], [], None, line_num

    if not name:
        return None, [f"行 {line_num}: 商品名(name)が空です。"], [], None, line_num

    # 16列構成（JANコード対応版）
    expected_keys = ['name', 'brand', 'tags', 'desc', 'size', 'jan', 'img', 'amz', 'rak', 'yah', 'a8', 'label', 'promo', 'amz_p', 'rak_p', 'yah_p']
    missing_keys = [k for k in expected_keys if k not in row or row[k] is None]
    if missing_keys:
        row_errors.append(f"行 {line_num}: 列が足りません。期待される列: {len(expected_keys)}、検出された列: {len(row)}。欠落: {', '.join(missing_keys)}")

    norm_name = normalize_text(name)
    desc = row.get('desc', '').strip()
    check_text = normalize_text(name + desc)

    # ブランド情報の処理 (直接入力値をIDとしても使用)
    brand_name = row.get('brand', '').strip()
    row['brand'] = brand_name
    row['brand_id'] = normalize_text(brand_name)

    # 画像URLのプレレンダリング (JANコードからの自動生成)
    img_val = row.get('img', '#').strip()
    rak_val = row.get('rak', '#').strip()
    jan_val = str(row.get('jan', '#')).strip().replace(" ", "").replace("-", "")

    # --force-refresh 時は既存の画像URLを強制クリアして再取得する
    if force_refresh and img_val != '#':
        img_val = '#'
        row['img'] = '#'

    current_kws = []

    # 外部ライブラリに頼らず、CSV側の「_keywords」フィールドや
    # rules.csv からの情報を統合するのみに留める
    row['_keywords'] = " ".join(list(set(current_kws)))

    tags = row.get('tags', '').replace(',', ' ').split()
    tags = [normalize_text(t) for t in tags if t]
    for t in tags:
        if t not in allowed_tags:
            row_errors.append(f"行 {line_num}: 未登録タグ '{t}' (商品: {name[:20]}...)")
            
    # 1. rules.csv に基づく自動付与（候補を作成）
    auto_added_info = []
    for tag_id, keywords in tag_keywords.items():
        if tag_id not in tags:
            found_kw = next((kw for kw in keywords if kw in check_text), None)
            if found_kw:
                tags.append(tag_id)
                auto_added_info.append((tag_id, found_kw))


    # 3. タグ名そのものが説明文に含まれている場合の提案 (除外タグ適用後)
    for t_name_norm, t_id in tag_lookup_for_suggest.items():
        if t_id not in tags and t_name_norm in check_text:
            row_warnings.append(f"行 {line_num}: 説明文に '{t_name_norm}' が含まれています。タグ '{t_id}' の付与を検討してください。")

    # 価格の数値形式チェック
    for p_col in ['amz_p', 'rak_p', 'yah_p']:
        p_val = str(row.get(p_col, '0')).strip()
        if p_val and p_val != '0' and p_val != '#':
            if not p_val.isdigit():
                row_errors.append(f"行 {line_num}: 価格 {p_col} は半角数字のみで入力してください（カンマや単位は禁止）: '{p_val}'")

    # リンク/画像URLの簡易形式チェック
    for l_col in ['img', 'amz', 'rak', 'yah', 'a8']:
        # 引用符や空白を徹底的に除去
        l_val = str(row.get(l_col, '#')).strip().strip('"').strip("'")
        
        # 有効な形式: 1. '#' (未設定)  2. 'http'で始まる  3. '['で始まるJSONリスト(imgのみ)
        is_valid = (l_val == '#') or (l_val.startswith('http')) or (l_col == 'img' and l_val.startswith('['))
        
        if not is_valid:
            row_errors.append(f"行 {line_num}: {l_col} のURL形式が正しくありません（httpから開始するか # にしてください）")

    tags.sort(key=lambda t: tag_to_cat_index.get(t, 999))
    row['tags'] = tags
    return row, row_errors, row_warnings, norm_name, line_num

def convert(exit_on_error=True, force_refresh=False):
    print(f"--- 変換処理を開始します ---")
    start_time = time.perf_counter()
    global validation_errors, validation_warnings
    validation_errors = []
    validation_warnings = []

    # --- 重複チェック用の変数をここで確実に初期化 ---
    seen_names = {}      # 商品名重複チェック用
    seen_jans = {}       # JANコード重複チェック用
    names_by_brand = {}  # 類似商品チェック用

    # 1. カテゴリマスタの読み込み
    category_master = {}
    category_order = []
    cat_rows = load_csv_simple(CAT_CSV)
    for row in cat_rows:
        if len(row) < 4 or row[0].lower() in ['key', 'キー']: continue
        key, jp, en, m_type = [s.strip() for s in row[:4]]
        category_master[key] = {"jp": jp, "en": en, "multi": m_type == 'multi'}
        category_order.append(key)

    # 2. タグマスタの読み込み
    tag_master = {}
    allowed_tags = set()
    tag_lookup_for_suggest = {} # 提案用：正規化名 -> タグID
    tag_rows = load_csv_simple(TAG_CSV)
    for row in tag_rows:
        if len(row) < 3 or row[0].lower() in ['category', 'カテゴリ']: continue
        cat, key, name = [s.strip() for s in row[:3]]
        if cat not in category_master:
            validation_errors.append(f"tags.csv 行内: カテゴリ '{cat}' は categories.csv に定義されていません。")
        if cat not in tag_master: tag_master[cat] = {}
        norm_key = normalize_text(key)
        tag_master[cat][norm_key] = name
        allowed_tags.add(norm_key)
        tag_lookup_for_suggest[normalize_text(name)] = norm_key

    # タグのカテゴリ所属マップを作成（ソート用）
    tag_to_cat_index = {}
    for idx, cat_key in enumerate(category_order):
        if cat_key in tag_master:
            for t_key in tag_master[cat_key]:
                tag_to_cat_index[t_key] = idx

    # ビルド時間をバージョンとして記録
    build_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    # 4. 自動ルール（キーワード）の読み込み
    tag_keywords = {}
    rule_rows = load_csv_simple(RULE_CSV)
    for row in rule_rows:
        if len(row) < 2 or row[0].lower() in ['tag', 'タグ']: continue
        tag, kw_str = row[0].strip(), row[1].strip()
        if tag and kw_str:
            # カンマやスペースで分割して正規化
            kws = [normalize_text(k) for k in kw_str.replace(',', ' ').split() if k]
            if tag not in tag_keywords: tag_keywords[tag] = []
            tag_keywords[tag].extend(kws)
            allowed_tags.add(normalize_text(tag))

    # 5. 動的に他の未認識マスターCSVを読み込む
    other_masters_data = {}
    if os.path.exists(DATA_DIR):
        for filename in os.listdir(DATA_DIR):
            # 特定のマスター以外のCSVを自動取得
            is_other_csv = filename.endswith('.csv') and filename != 'products.csv' and filename not in SPECIFIC_MASTER_CSVS
            if is_other_csv:
                filepath = os.path.join(DATA_DIR, filename)
                var_name = os.path.splitext(filename)[0]
                var_name = re.sub(r'[^a-zA-Z0-9_]', '_', var_name)
                
                data = load_csv_dict_list(filepath)
                if data is not None:
                    other_masters_data[var_name] = data
                    print(f"   - 追加マスター検出: {filename} -> const {var_name}")
                else:
                    validation_warnings.append(f"追加マスター '{filename}' は中身が空か、形式が正しくないためスキップされました。")

    # 6. 商品データの読み込みと加工
    if not os.path.exists(PRODUCT_CSV):
        print(f"エラー: {PRODUCT_CSV} が見つかりません。")
        return

    # データの読み込み
    all_rows_input = []
    with open(PRODUCT_CSV, 'r', encoding='utf-8-sig', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader, start=2):
            all_rows_input.append((i, r))

    # 並列処理の実行
    print(f"   - {len(all_rows_input)}件を並列処理中...")
    processed_results = []

     # max_workers を指定することで使用するCPUコア数を制限できます
    # 例: os.cpu_count() // 2 とすれば、パソコンの能力の半分だけを使います
    num_cores = os.cpu_count() or 1
    max_workers = max(1, min(num_cores - 1, 8)) # 1コアをOS用に残し、最大8プロセスで並列化
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_row_task, ln, row, tag_keywords, tag_to_cat_index, allowed_tags, tag_lookup_for_suggest, DEFAULT_RAKUTEN_IMAGE_SHOPS, force_refresh) 
                   for ln, row in all_rows_input]
        
        for future in concurrent.futures.as_completed(futures):
            res_row, res_errs, res_warns, norm_name, ln = future.result()
            validation_errors.extend(res_errs)
            validation_warnings.extend(res_warns)
            if res_row:
                processed_results.append((ln, res_row, norm_name))

    # 全プロセス終了後、行番号で並び替えて元の順序を復元
    processed_results.sort(key=lambda x: x[0])
    products = [r[1] for r in processed_results]

    for ln, res_row, norm_name in processed_results:
        # JAN重複チェック (# はスキップ)
        jan_val = str(res_row.get('jan', '#')).strip()
        # 全角を半角に変換し、数字以外を除去
        jan_val = unicodedata.normalize('NFKC', jan_val).replace(" ", "").replace("-", "")
        res_row['jan'] = jan_val

        # 商品名重複チェック用のキー（ブランドID + 空白を除去した名前）
        dup_key = f"{res_row['brand_id']}|{''.join(norm_name.split())}"

        if jan_val != '#':
            if not jan_val.isdigit() or len(jan_val) != 13:
                validation_warnings.append(f"行 {ln}: JANコード '{jan_val}' が標準的な13桁の数字ではありません。画像生成に失敗する可能性があります。")

            if jan_val in seen_jans:
                validation_errors.append(f"行 {ln}: JANコード '{jan_val}' が重複しています。(商品: {res_row['name']} / 既出: 行 {seen_jans[jan_val]})")
            else:
                seen_jans[jan_val] = ln

        # 商品名重複チェック
        brand_id = res_row['brand_id']

        if dup_key in seen_names:
            validation_errors.append(f"行 {ln}: 商品名 '{res_row['name']}' が重複しています。(既出: 行 {seen_names[dup_key]})")
        else:
            # 類似商品チェック（同じブランド内で 95% 以上一致するものがあるか）
            if brand_id not in names_by_brand: names_by_brand[brand_id] = []
            if len(names_by_brand[brand_id]) < 1000: # 10万件規模では、ブランド内の商品数が少ない場合のみ実行
                close_matches = difflib.get_close_matches(norm_name, names_by_brand[brand_id], n=1, cutoff=0.95)
                if close_matches:
                    validation_warnings.append(f"行 {ln}: '{res_row['name']}' は既出の '{close_matches[0]}' と非常に似ています。")
            seen_names[dup_key] = ln
            names_by_brand[brand_id].append(norm_name)
        
        # お気に入り管理用の不変なIDを付与
        # JANがあればJANを使用、なければ名寄せ用キーのパイプをアンダーバーに変えたものを使用
        res_row['id'] = jan_val if jan_val != '#' else dup_key.replace('|', '_')

    # products リストは既に上で作成済み
    # 画像キャッシュ用フォルダの確認と自動補完処理（シーケンシャルに3秒ウェイトを挟む）
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
    os.makedirs(cache_dir, exist_ok=True)

    print("   - 画像自動補完・キャッシュ処理（1件ずつウェイトを挟みながら実行します）...")
    for idx, row in enumerate(products):
        img_val = row.get('img', '#').strip()
        jan_val = str(row.get('jan', '#')).strip().replace(" ", "").replace("-", "")
        name = row.get('name', '').strip()
        brand_name = row.get('brand', '').strip()
        product_size = row.get('size', '').strip()

        if force_refresh:
            img_val = '#'
            row['img'] = '#'

        if jan_val != '#' and len(jan_val) == 13 and jan_val.isdigit():
            # 1. まずローカルのキャッシュ画像があるかチェック
            cached_found = False
            for ext in ["jpg", "jpeg", "png", "webp", "gif"]:
                test_path = os.path.join(cache_dir, f"{jan_val}.{ext}")
                if os.path.exists(test_path):
                    row['img'] = f"images/{jan_val}.{ext}"
                    img_val = f"images/{jan_val}.{ext}"
                    cached_found = True
                    break

            if cached_found:
                continue

            # キャッシュがなく、img_valが '#' の場合のみ各種API/推測を試行する
            if img_val == '#':
                api_success = False

                # ① [最優先] 楽天商品検索API v2（マイクロサービス版 Product Search）- 高品質カタログ画像
                if RAKUTEN_APP_ID and RAKUTEN_ACCESS_KEY:
                    print(f"   [楽天Product Search API(v2)] 検索中: JAN={jan_val} ({name[:20]})")
                    prod_img = fetch_rakuten_product_data_v2(jan_val)
                    if prod_img:
                        row['img'] = prod_img
                        img_val = prod_img
                        api_success = True
                        print(f"   ✅ 楽天Product Search API(v2)から公式カタログ画像を取得しました: {prod_img}")
                    # 連続アクセス防止のため必ず3秒スリープ
                    time.sleep(3)

                # ② [第2優先] 楽天商品価格ナビ（カタログ製品検索）APIで検索（従来版）
                if not api_success and RAKUTEN_TRADITIONAL_APP_ID and RAKUTEN_TRADITIONAL_APP_ID != "YOUR_RAKUTEN_TRADITIONAL_APP_ID":
                    print(f"   [楽天価格ナビAPI(従来)] 検索中: JAN={jan_val} ({name[:20]})")
                    prod_img = fetch_rakuten_product_data(jan_val)
                    if prod_img:
                        row['img'] = prod_img
                        img_val = prod_img
                        api_success = True
                        print(f"   ✅ 楽天価格ナビAPIから公式画像を取得しました: {prod_img}")
                    # 連続アクセス防止のため必ず3秒スリープ
                    time.sleep(3)

                # ③ [第3優先] Yahoo!ショッピング商品検索APIで検索
                if not api_success and YAHOO_CLIENT_ID and YAHOO_CLIENT_ID != "YOUR_YAHOO_CLIENT_ID":
                    print(f"   [Yahoo!ショッピングAPI] 検索中: JAN={jan_val} ({name[:20]})")
                    yahoo_img = fetch_yahoo_shopping_data(jan_val)
                    if yahoo_img:
                        row['img'] = yahoo_img
                        img_val = yahoo_img
                        api_success = True
                        print(f"   ✅ Yahoo!ショッピングAPIから画像を取得しました: {yahoo_img}")
                    # 連続アクセス防止のため必ず3秒スリープ
                    time.sleep(3)

                # ④ [第4優先] 楽天商品検索API（店舗画像、スコアリング付き）で検索
                if not api_success and rak_config["use_api_for_images"] and RAKUTEN_APP_ID and RAKUTEN_ACCESS_KEY:
                    print(f"   [楽天商品検索API(IchibaItem)] 検索中: JAN={jan_val} ({name[:20]})")
                    api_data = fetch_rakuten_data(jan_val, product_name=name, brand_name=brand_name, product_size=product_size)
                    if api_data and api_data["image"]:
                        row['img'] = api_data["image"]
                        img_val = api_data["image"]
                        api_success = True
                        print(f"   ✅ 楽天商品検索APIから画像を取得しました: {api_data['image']}")
                    # リクエスト後は必ず3秒のウエイト
                    time.sleep(3)

                # ⑤ 楽天APIで見つからなかった場合、推測ショップリストから実在する画像をヘッドリクエストで確認
                if not api_success:
                    print(f"   [楽天推測] 実在確認中: JAN={jan_val}")
                    found_img_url = None
                    for shop_id in DEFAULT_RAKUTEN_IMAGE_SHOPS:
                        test_url = f"https://thumbnail.image.rakuten.co.jp/@0_mall/{shop_id}/cabinet/jan/{jan_val}.jpg"
                        try:
                            resp = requests.head(test_url, timeout=2.0)
                            if resp.status_code == 200:
                                found_img_url = test_url
                                print(f"   ✅ 推測ショップ '{shop_id}' から画像を検出しました。")
                                break
                        except Exception:
                            pass
                        # 1リクエストごとに必ず3秒のウエイト
                        time.sleep(3)
                    
                    if found_img_url:
                        row['img'] = found_img_url
                        img_val = found_img_url
                        api_success = True

                # ⑥ それでも見つからなかった場合はGoogle CSE（image search）を利用
                if not api_success and GOOGLE_API_KEY and GOOGLE_CSE_ID:
                    print(f"   [Google CSE] 検索中: JAN={jan_val} ({name[:20]})")
                    local_img_path = fetch_google_image(jan_val, brand_name, name)
                    if local_img_path:
                        row['img'] = local_img_path
                        img_val = local_img_path
                        api_success = True

    if not validation_errors:
        # 7. エラーが一つもない場合のみファイル書き出しを実行
        # 10万件規模に対応するため、ファイルを分割（チャンク化）して保存
        num_chunks = (len(products) + CHUNK_SIZE - 1) // CHUNK_SIZE
        for i in range(num_chunks):
            chunk = products[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]
            chunk_filename = f'product_data_{i}.json'
            with open(chunk_filename, 'w', encoding='utf-8') as f:
                json.dump(chunk, f, ensure_ascii=False, separators=(',', ':'))
        # メインのJSONにはメタデータのみを記述
        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump({"total": len(products), "chunks": num_chunks, "version": build_version}, f)

        with open(OUTPUT_MASTER_JS, 'w', encoding='utf-8') as f:
            f.write(f"const siteVersion = '{build_version}';\n")
            f.write(f"const tagMaster = {json.dumps(tag_master, ensure_ascii=False, indent=4)};\n")
            f.write(f"const categoryMaster = {json.dumps(category_master, ensure_ascii=False, indent=4)};\n")
            f.write(f"const tagKeywords = {json.dumps(tag_keywords, ensure_ascii=False, indent=4)};\n")
            # 動的に読み込んだマスターデータを追記
            for var_name, data in other_masters_data.items():
                f.write(f"const {var_name} = {json.dumps(data, ensure_ascii=False, indent=4)};\n")

    print(f"--- 変換完了 ---")
    if not validation_errors:
        print(f"   - {OUTPUT_JSON} ({len(products)}件)")
        print(f"   - {OUTPUT_MASTER_JS} (マスタ設定)")
    else:
        print(f"   - ファイル出力は中断されました (不備があるため)")

    exec_time = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    print(f"   ⏰ 実行時刻: {exec_time}")
    duration = time.perf_counter() - start_time
    print(f"   - 処理時間: {duration:.2f}秒")

    # 警告（確認を促すだけでデプロイは止めない）を表示
    if validation_warnings:
        print(f"\n{COLOR_CYAN}{COLOR_BOLD}💡 {len(validation_warnings)} 個の確認推奨項目があります:{COLOR_RESET}")
        for warn in validation_warnings[:10]:
            print(f"{COLOR_CYAN}   - {warn}{COLOR_RESET}")
        if len(validation_warnings) > 10: print(f"   ...他 {len(validation_warnings)-10} 件")

    if validation_errors:
        print(f"\n{COLOR_RED}{COLOR_BOLD}⚠️  {len(validation_errors)} 個のデータ不備が見つかりました:{COLOR_RESET}")
        for err in validation_errors[:10]: # 最初の10件を表示
            print(f"{COLOR_RED}   - {err}{COLOR_RESET}")
        if len(validation_errors) > 10: print(f"   ...他 {len(validation_errors)-10} 件")
        # 致命的なミス（商品名空など）がある場合にデプロイを止めるなら以下を有効にする
        if exit_on_error:
            sys.exit(1)
    else:
        print(f"{COLOR_GREEN}{COLOR_BOLD}✅ すべてのデータが正常に処理されました。{COLOR_RESET}")

if __name__ == '__main__':
    force_refresh = "--force-refresh" in sys.argv
    if force_refresh:
        print(f"{COLOR_YELLOW}{COLOR_BOLD}🔄 --force-refresh モード: すべての画像を新フィルターで取り直します。{COLOR_RESET}")

    if "--watch" in sys.argv:
        print(f"{COLOR_BOLD}👀 監視モードを起動しました。CSVの変更を待機中... (Ctrl+C で終了){COLOR_RESET}")
        try:
            convert(exit_on_error=False, force_refresh=force_refresh) # 初回実行
        except Exception as e:
            print(f"{COLOR_RED}初回ビルド失敗: {e}{COLOR_RESET}")
        
        # 初期状態のファイル時間を記録
        last_mtimes = {}
        if os.path.exists(DATA_DIR):
            for f in os.listdir(DATA_DIR):
                if f.endswith('.csv') and not f.startswith('.'):
                    path = os.path.join(DATA_DIR, f)
                    last_mtimes[path] = os.path.getmtime(path)

        while True:
            try:
                time.sleep(1) # 1秒間隔でチェック
                changed = False
                for f in os.listdir(DATA_DIR):
                    if f.endswith('.csv') and not f.startswith('.'):
                        path = os.path.join(DATA_DIR, f)
                        mtime = os.path.getmtime(path)
                        if path not in last_mtimes or mtime > last_mtimes[path]:
                            last_mtimes[path] = mtime
                            changed = True
                if changed:
                    print(f"\n{COLOR_YELLOW}🔄 変更を検知しました。再ビルドします...{COLOR_RESET}")
                    time.sleep(0.2) # ファイルの書き込み完了を少し待つ
                    convert(exit_on_error=False)
            except KeyboardInterrupt:
                print(f"\n{COLOR_YELLOW}監視モードを終了します。{COLOR_RESET}")
                break
            except Exception as e:
                print(f"{COLOR_RED}監視中にエラーが発生しました: {e}{COLOR_RESET}")
    else:
        try:
            convert(force_refresh=force_refresh)
        except Exception as e:
            print(f"{COLOR_RED}{COLOR_BOLD}❌ 変換失敗: {e}{COLOR_RESET}")
            sys.exit(1)