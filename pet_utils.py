"""
pet925プロジェクトの複数のPythonスクリプト（csv_to_json.py / auto_collect_all.py）から
共通で利用するユーティリティ集。

「いつ実行するか」に依存しない純粋な処理（文字列正規化、.env読み込み、CSV読み込み、
楽天/Yahoo APIリクエストの共通定数）をここに集約し、スクリプト間のコピペ重複を防ぐ。
"""
import csv
import os
import re
import unicodedata

# ─────────────────────────────────────────────
# 文字列・JANコードの正規化
# ─────────────────────────────────────────────

def normalize_text(s):
    """JS版のnormalizeと動作を合わせる（NFKC正規化 + ひらがなをカタカナへ変換）"""
    if not s:
        return ""
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
    return re.sub(r'\s+', ' ', s).strip()  # 連続する空白を1つに統合


def normalize_jan(jan_str):
    """
    JANコードを半角数字のみに正規化する。
    14桁（先頭に0が付くEAN-14形式など）の場合は、先頭13桁のJANコードに切り詰める。
    """
    jan = unicodedata.normalize('NFKC', str(jan_str)).strip().replace(" ", "").replace("-", "")
    if jan.isdigit() and len(jan) == 14:
        return jan[:13]
    return jan


# ─────────────────────────────────────────────
# .envファイル読み込み（環境変数を優先しつつ、.envファイルの値で補完・上書き）
# ─────────────────────────────────────────────

_ENV_FILE_CACHE = None


def _read_env_file():
    """.envファイルを1度だけ読み込み、key→valueの辞書にキャッシュして返す"""
    global _ENV_FILE_CACHE
    if _ENV_FILE_CACHE is not None:
        return _ENV_FILE_CACHE
    values = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.split('#')[0].strip()
                if not line or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip("'").strip('"')
    _ENV_FILE_CACHE = values
    return values


def get_env_value(primary_key, *alias_keys):
    """
    設定値を取得する共通ヘルパー。
    ターミナル環境変数(os.getenv)をベースにしつつ、.envファイルに同名キー（別名含む）が
    あればそちらを優先して返す。
    """
    value = os.getenv(primary_key)
    env_file = _read_env_file()
    for key in (primary_key,) + alias_keys:
        if key in env_file:
            value = env_file[key]
    return value


# ─────────────────────────────────────────────
# CSV読み込み（ヘッダー名ベースで読み込み、列の並び順変更に強くする）
# ─────────────────────────────────────────────

def load_dict_rows(path):
    """
    ヘッダー行付きCSVを csv.DictReader で読み込み、辞書のリストとして返す。
    列の「並び順」ではなく「列名」でアクセスするため、CSVの列順を入れ替えても壊れない。
    ファイルが存在しない場合は空リストを返す。
    """
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8-sig', errors='replace', newline='') as f:
        reader = csv.DictReader(f)
        return [row for row in reader if row]


# ─────────────────────────────────────────────
# 楽天/Yahoo APIリクエストの共通定数
# ─────────────────────────────────────────────

RAKUTEN_REGISTERED_DOMAIN = "https://kyuni-f.github.io/pet925/"
RAKUTEN_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": RAKUTEN_REGISTERED_DOMAIN,
    "Referer": RAKUTEN_REGISTERED_DOMAIN,  # 末尾が "//" にならないよう、二重スラッシュを修正
}

# 楽天商品検索API（マイクロサービス版 Product Search）: 白バックのきれいな公式カタログ画像を取得できる
RAKUTEN_PRODUCT_SEARCH_V2_URL = "https://openapi.rakuten.co.jp/ichibaproduct/api/Product/Search/20250801"
# 楽天商品検索API（マイクロサービス版 IchibaItem Search）: 店舗の出品情報を検索する
RAKUTEN_ITEM_SEARCH_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260401"
# Yahoo!ショッピング商品検索API
YAHOO_SHOPPING_SEARCH_URL = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
