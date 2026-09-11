#!/usr/bin/env python3
"""
JANコードリストから全自動で products.csv 行を生成する統合スクリプト。

使い方:
  python3 auto_collect_all.py jan_list.csv
  python3 auto_collect_all.py jan_list.csv --img-only

ワークフロー:
  1. Product Search API v2 → 商品名・画像・メーカー名・説明文・価格を一発取得
  2. 名前は取れたが画像が無い場合、画像だけ Item Search → 兄弟SKU → Yahoo の順で補完
  3. 取得できなければ Item Search API にフォールバック（商品名ごと）
  4. GEMINI_API_KEY があれば、説明文とタグ候補（tags.csvの許可リストから選択）をAIに1回でまとめて依頼
     （--img-only ではスキップ）。AI呼び出しが無い/失敗した場合は rules.csv ベースの判定にフォールバック
     （説明文は空のまま）
  5. products.csv に追記

  --img-only: 既存行の img 列だけ更新する。名前・説明・タグは触らない。

注意:
  GEMINI_API_KEY が .env に設定されている場合、説明文とタグの自動生成が有効になります。
  設定がない場合でも、楽天APIから取得できる情報だけで products.csv は完成します（タグはrules.csvベース）。
"""

import csv
import os
import sys
import time
import re
import json
import unicodedata
import random
import requests
from difflib import SequenceMatcher
from io import StringIO

from pet_utils import (
    normalize_text,
    normalize_jan,
    get_env_value,
    load_dict_rows,
    RAKUTEN_REQUEST_HEADERS,
    RAKUTEN_PRODUCT_SEARCH_V2_URL,
    RAKUTEN_ITEM_SEARCH_URL,
    YAHOO_SHOPPING_SEARCH_URL,
)

# ─────────────────────────────────────────────
# 設定
# ─────────────────────────────────────────────
DATA_DIR = 'data'
PRODUCT_CSV = os.path.join(DATA_DIR, 'products.csv')
TAG_CSV = os.path.join(DATA_DIR, 'tags.csv')
RULE_CSV = os.path.join(DATA_DIR, 'rules.csv')

FIELD_NAMES = ['name', 'brand', 'tags', 'desc', 'size', 'jan', 'img', 'amz', 'rak', 'yah', 'a8', 'label', 'promo', 'amz_p', 'rak_p', 'yah_p']

# 既存JANが見つかった場合でも、この項目だけは自動取得結果で上書き更新する
# （amz/yah/a8/label/promo/size/amz_p/yah_p などの手動編集項目は既存値を保持する）
AUTO_UPDATE_FIELDS = ['name', 'brand', 'tags', 'desc', 'img', 'rak', 'rak_p']

WEIGHT_RE = re.compile(r'\d+(?:\.\d+)?\s*(?:kg|g)', re.I)
SHOP_JUNK_RE = re.compile(r'【[^】]*】|\[[^\]]*\]')
SIBLING_GENERIC_TOKENS = {
    normalize_text(t) for t in (
        'ロイヤルカナン', 'royalcanin', 'royal', 'canin',
        'ドッグフード', 'キャットフード', 'ドライフード', 'ドライ',
        '正規品', 'フード', '犬用', '猫用', '成犬用', '成猫用',
        '子犬用', '子猫用', '中高齢犬用', '中・高齢犬用', '中高齢猫用',
        'ジッパー付き', 'プレミアムフード', 'shn', 'lhn', 'ccn',
        '小型犬用', '超小型犬', '超小型犬~小型犬用', '超小型犬〜小型犬用',
        '生後10ヵ月齢以上', '生後10ヵ月以上', '減量したい犬用',
        '健康な尿を維持したい犬用',
    )
}

# ─────────────────────────────────────────────
# 設定読み込み（.env読み込みの実処理は pet_utils.get_env_value に共通化）
# ─────────────────────────────────────────────
RAKUTEN_APP_ID = get_env_value("RAKUTEN_APP_ID")
RAKUTEN_ACCESS_KEY = get_env_value("RAKUTEN_ACCESS_KEY")
GEMINI_API_KEY = get_env_value("GEMINI_API_KEY")
YAHOO_CLIENT_ID = get_env_value("YAHOO_CLIENT_ID")

# ─────────────────────────────────────────────
# マスターCSV読み込み（normalize_text / normalize_jan は pet_utils.py で共有）
# ─────────────────────────────────────────────
def load_rules_map():
    """rules.csv から {タグID: [キーワードリスト]} を読み込む"""
    rules = {}
    for row in load_dict_rows(RULE_CSV):
        tag = (row.get('tag') or '').strip()
        kw_str = (row.get('keywords') or '').strip()
        if tag and kw_str:
            kws = [normalize_text(k) for k in kw_str.replace(',', ' ').split() if k]
            rules[tag] = kws
    return rules

def load_allowed_tags():
    """tags.csv から許可タグセットを読み込む"""
    allowed = set()
    # rules.csv のタグも許可
    rules = load_rules_map()
    allowed.update(normalize_text(t) for t in rules.keys())
    # tags.csv の key
    for row in load_dict_rows(TAG_CSV):
        key = (row.get('key') or '').strip()
        if key:
            allowed.add(normalize_text(key))
    return allowed


def load_tag_catalog_text():
    """
    tags.csv から「key:日本語名」の一覧テキストを作る（Geminiへのタグ選択プロンプト用）。
    ここに載っているキーだけをAIに選ばせることで、tags.csvに無い野良タグが生まれるのを防ぐ。
    """
    lines = []
    for row in load_dict_rows(TAG_CSV):
        key = (row.get('key') or '').strip()
        name = (row.get('name') or '').strip()
        if key:
            lines.append(f"{normalize_text(key)}:{name}")
    return "\n".join(lines)

def clean_image_url(url):
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if not url.startswith('http'):
        return None
    return re.sub(r"\?_ex=.*$", "", url)


def is_catalog_image(url):
    return bool(url) and 'r.r10s.jp' in url


def score_image_url(url):
    if not url or not str(url).startswith('http'):
        return -1
    lower = url.lower()
    if 'r.r10s.jp' in lower:
        return 100
    if 'thumbnail.image.rakuten.co.jp' in lower:
        return 40
    if 'yimg.jp' in lower:
        return 20
    return 10


def pick_better_image(old, new):
    """既存のカタログ画像を、店画像や空値で潰さない。"""
    old = old if old and old != '#' else None
    new = new if new and new != '#' else None
    if is_catalog_image(new):
        return new
    if is_catalog_image(old):
        return old
    return new or old


def product_image_url(product):
    return clean_image_url(
        product.get("mediumImageUrl") or product.get("smallImageUrl") or product.get("imageUrl")
    )


def unwrap_product_entry(entry):
    if not isinstance(entry, dict):
        return None
    product = entry.get("Product", entry)
    return product if isinstance(product, dict) else None


def pick_product(products, jan):
    """JAN一致の製品を優先し、その中で画像があるものを選ぶ。一致が無いときは先頭のみ。"""
    parsed = [p for p in (unwrap_product_entry(e) for e in products) if p]
    if not parsed:
        return None
    exact = [p for p in parsed if str(p.get("productCode") or "") == jan]
    pool = exact or parsed[:1]
    pool.sort(key=lambda p: 1 if product_image_url(p) else 0, reverse=True)
    return pool[0]


def product_to_result(product):
    if not product:
        return None
    return {
        "name": product.get("productName") or product.get("productTitle") or product.get("title"),
        "makerName": product.get("makerName"),
        "brandName": product.get("brandName"),
        "description": product.get("productDescription") or product.get("explanation") or product.get("productCaption"),
        "catalogPrice": product.get("catalogPrice") or product.get("price"),
        "image": product_image_url(product),
    }


def extract_item_images(item):
    urls = []
    direct = clean_image_url(item.get("image_url") or item.get("imageUrl"))
    if direct:
        urls.append(direct)
    for key in ("medium_image_urls", "mediumImageUrls"):
        urls_list = item.get(key)
        if not isinstance(urls_list, list):
            continue
        for entry in urls_list:
            if isinstance(entry, dict):
                cleaned = clean_image_url(entry.get("imageUrl") or entry.get("image_url"))
            else:
                cleaned = clean_image_url(entry)
            if cleaned:
                urls.append(cleaned)
    return urls


def sibling_family_key(name):
    text = SHOP_JUNK_RE.sub(' ', name or '')
    text = WEIGHT_RE.sub(' ', text)
    text = normalize_text(text)
    tokens = [
        t for t in text.split()
        if t not in SIBLING_GENERIC_TOKENS and not t.startswith('rcdb')
    ]
    # スペース有無のゆれ（ライト ウェイト ケア vs ライトウェイトケア）を吸収
    return ''.join(tokens)


def sibling_life_stage(name):
    text = normalize_text(name or '')
    if re.search(r'パピー|子犬|幼犬|puppy', text):
        return 'puppy'
    if re.search(r'シニア|高齢|8\+|8＋|senior', text):
        return 'senior'
    if re.search(r'アダルト|成犬|成猫|adult', text):
        return 'adult'
    return ''


def find_sibling_image(jan, name, rows, min_ratio=0.82):
    """容量違いなど、同じラインのカタログ画像を借りる。"""
    key = sibling_family_key(name)
    if len(key) < 8:
        return None
    stage = sibling_life_stage(name)
    best_img = None
    best_ratio = 0
    for row in rows:
        other_jan = normalize_jan(row.get('jan', ''))
        if not other_jan or other_jan == jan:
            continue
        img = (row.get('img') or '').strip()
        if not is_catalog_image(img):
            continue
        other_key = sibling_family_key(row.get('name') or '')
        if len(other_key) < 8:
            continue
        other_stage = sibling_life_stage(row.get('name') or '')
        if stage and other_stage and stage != other_stage:
            continue
        ratio = SequenceMatcher(None, key, other_key).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_img = img
    if best_ratio >= min_ratio:
        return best_img
    return None


# ─────────────────────────────────────────────
# 楽天 Product Search API v2（全情報取得）
# ─────────────────────────────────────────────
def _get_with_retry(url, params, headers, timeout, label, jan, retries=1):
    """429 のときだけ待って1回やり直す。"""
    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    if resp.status_code == 429 and retries > 0:
        print(f"  ⚠️ {label} レート制限: JAN {jan} → 8秒待って再試行")
        time.sleep(8)
        return _get_with_retry(url, params, headers, timeout, label, jan, retries - 1)
    return resp


def _product_search_request(jan, use_product_code):
    params = {
        "applicationId": RAKUTEN_APP_ID.strip(),
        "accessKey": RAKUTEN_ACCESS_KEY.strip(),
        "format": "json",
    }
    if use_product_code:
        params["productCode"] = jan
    else:
        params["keyword"] = jan
        params["hits"] = 30
    return _get_with_retry(
        RAKUTEN_PRODUCT_SEARCH_V2_URL,
        params,
        RAKUTEN_REQUEST_HEADERS,
        10,
        "Product Search API",
        jan,
    )


def fetch_product_search_v2(jan):
    """
    楽天Product Search API (v2) から全情報を一度に取得する。
    戻り値: {
      "name": "商品名",
      "makerName": "メーカー名",
      "brandName": "ブランド名",
      "description": "商品説明文",
      "catalogPrice": 価格(数値),
      "image": "画像URL"
    } または None
    """
    if not RAKUTEN_APP_ID or not RAKUTEN_ACCESS_KEY or not jan or jan == '#':
        return None
    try:
        resp = _product_search_request(jan, use_product_code=True)
        products = []
        if resp.status_code == 200:
            data = resp.json()
            products = data.get("Products") or []
        elif resp.status_code == 429:
            print(f"  ⚠️ Product Search API レート制限: JAN {jan}")
            return None
        elif resp.status_code not in (400, 404):
            print(f"  ⚠️ Product Search API エラー {resp.status_code}: JAN {jan}")

        if not products:
            resp = _product_search_request(jan, use_product_code=False)
            if resp.status_code == 200:
                data = resp.json()
                products = data.get("Products") or []
            elif resp.status_code == 429:
                print(f"  ⚠️ Product Search API レート制限: JAN {jan}")
                return None
            elif resp.status_code != 200:
                print(f"  ⚠️ Product Search API エラー {resp.status_code}: JAN {jan}")
                return None

        if not isinstance(products, list) or not products:
            return None
        product = pick_product(products, jan)
        result = product_to_result(product)
        if result and result.get("name"):
            return result
    except Exception as e:
        print(f"  ❌ Product Search API 通信エラー: {e} (JAN: {jan})")
    return None

# ─────────────────────────────────────────────
# 楽天 Item Search API（フォールバック用）
# ─────────────────────────────────────────────
def fetch_item_search(jan):
    """
    楽天Item Search API。Product Search API で取得できなかった場合のフォールバック。
    画像ありの出品を最大10件見て、r.r10s.jp を優先する。
    戻り値: {"name": ..., "image": ..., "url": ...} または None
    """
    if not RAKUTEN_APP_ID or not RAKUTEN_ACCESS_KEY or not jan or jan == '#':
        return None
    url = RAKUTEN_ITEM_SEARCH_URL
    params = {
        "applicationId": RAKUTEN_APP_ID.strip(),
        "accessKey": RAKUTEN_ACCESS_KEY.strip(),
        "keyword": jan,
        "hits": 10,
        "imageFlag": 1,
        "format": "json",
        "formatVersion": 2
    }
    try:
        resp = _get_with_retry(
            url, params, RAKUTEN_REQUEST_HEADERS, 10, "Item Search API", jan
        )
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("items") or data.get("Items", [])
            best = None
            best_score = -1
            for entry in items:
                item = entry.get("Item") if isinstance(entry, dict) and "Item" in entry else entry
                if not isinstance(item, dict):
                    continue
                images = extract_item_images(item)
                if not images:
                    continue
                img_url = max(images, key=score_image_url)
                score = score_image_url(img_url)
                if score > best_score:
                    best_score = score
                    best = {
                        "name": item.get("itemName") or item.get("name"),
                        "image": img_url,
                        "url": item.get("itemUrl")
                    }
                    if score >= 100:
                        break
            return best
        elif resp.status_code == 429:
            print(f"  ⚠️ Item Search API レート制限: JAN {jan}")
        else:
            print(f"  ⚠️ Item Search API エラー {resp.status_code}: JAN {jan}")
    except Exception as e:
        print(f"  ❌ Item Search API 通信エラー: {e} (JAN: {jan})")
    return None


def resolve_better_image(jan, name, current_image, rows, try_item=True, try_yahoo=True):
    """
    カタログ画像が無いときだけ、Item Search → 兄弟SKU → Yahoo の順で補完する。
    商品名は変えない。
    """
    image = current_image if current_image and current_image != '#' else None
    if is_catalog_image(image):
        return image

    if try_item:
        time.sleep(1.5)
        item_data = fetch_item_search(jan)
        if item_data and item_data.get("image"):
            candidate = item_data["image"]
            if not image or score_image_url(candidate) > score_image_url(image):
                image = candidate
                print(f"    画像補完 (Item Search): {image[:50]}...")
        if is_catalog_image(image):
            return image

    sibling = find_sibling_image(jan, name, rows)
    if sibling:
        print(f"    画像補完 (兄弟SKU): {sibling[:50]}...")
        return sibling

    if try_yahoo and not image:
        yahoo_data = fetch_yahoo_shopping(jan)
        if yahoo_data and yahoo_data.get("image"):
            image = yahoo_data["image"]
            print(f"    画像補完 (Yahoo): {image[:50]}...")
    return image


def apply_sibling_images(rows):
    """書き出し前に、まだ欠けている img を兄弟SKUのカタログ画像で埋める。"""
    filled = 0
    for row in rows:
        img = (row.get('img') or '').strip()
        if img and img != '#':
            continue
        jan = normalize_jan(row.get('jan', ''))
        name = row.get('name') or ''
        sibling = find_sibling_image(jan, name, rows)
        if sibling:
            row['img'] = sibling
            filled += 1
            print(f"  🧩 兄弟SKU画像: JAN {jan} ← {sibling[:50]}...")
    return filled

# ─────────────────────────────────────────────
# Yahoo!ショッピング API（フォールバック用）
# ─────────────────────────────────────────────
def fetch_yahoo_shopping(jan):
    """Yahoo!ショッピングAPIから商品名と画像を取得"""
    if not YAHOO_CLIENT_ID or not jan or jan == '#':
        return None
    url = YAHOO_SHOPPING_SEARCH_URL
    params = {"appid": YAHOO_CLIENT_ID.strip(), "jan_code": jan, "results": 1}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            hits = data.get("hits", [])
            if hits and isinstance(hits, list):
                first = hits[0]
                if isinstance(first, dict):
                    img_obj = first.get("image", {})
                    img_url = img_obj.get("medium") or img_obj.get("small")
                    if img_url:
                        img_url = img_url.replace("/i/c/", "/i/g/").replace("/i/d/", "/i/g/")
                    return {
                        "name": first.get("name"),
                        "image": clean_image_url(img_url),
                        "url": first.get("url")
                    }
    except Exception as e:
        pass  # フォールバックなのでエラーは表示しない
    return None

# ─────────────────────────────────────────────
# Gemini API で説明文とタグ候補をまとめて自動生成
# ─────────────────────────────────────────────
def generate_description_and_tags_via_gemini(product_name, maker_name, raw_description, jan, tag_catalog_text):
    """
    Gemini API を1回だけ呼び、「60字程度の説明文」と「タグ候補（tags.csvの許可リストから選択）」を
    同時にJSON形式で生成する。
    以前は説明文生成(このAPI呼び出し)とタグ判定(rules.csvの完全一致)を別処理にしていたが、
    ①API呼び出しが2回に増えてレート制限に近づく ②rules.csvの完全一致はメーカー名表記の揺れに弱い、
    という理由から1回のAI呼び出しに統合した。
    戻り値: {"description": "...", "tags": [...]} または None（失敗時。呼び出し元でルールベースにフォールバックする）
    """
    if not GEMINI_API_KEY:
        return None

    model_name = "gemini-2.5-flash"
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"

    # 元ネタがある場合はそれをプロンプトに含める
    source_text = f"\n【参考: 商品説明の元ネタ】\n{raw_description[:500]}" if raw_description else ""

    prompt = f"""あなたはペットフード比較サイトのデータ作成アシスタントです。
以下の商品について、(1)特徴・おすすめポイントの説明文 と (2)当てはまるタグ を判定してください。

【商品名】{product_name}
【メーカー】{maker_name or "不明"}【JANコード】{jan}{source_text}

【説明文のルール】
- 商品の特徴を具体的に（例：主原料、対応年齢、健康ケア）
- 「どんな悩みを持つ犬・猫におすすめか」というユーザー視点を含める
- 60文字程度（50〜70字）に収める
- 宣伝文句や誇張表現は避ける

【タグのルール】
- 下記の「タグ一覧」に載っているキーだけを使うこと。一覧に無いタグは絶対に作らないこと
- 商品名・メーカー名・説明文の元ネタから、当てはまるものだけを選ぶこと
- 動物種（dog/cat。両方向けなら両方）と、年齢（all_ages/puppy/adult/senior のいずれか1つ）は必ず含めること

【タグ一覧（key:日本語名）】
{tag_catalog_text}

【出力形式】
説明や前置き、Markdownのコードブロック記号（```）は一切付けず、次のJSON形式のみを1行で出力してください。
{{"description": "説明文をここに", "tags": ["key1", "key2"]}}"""

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            res_data = resp.json()
            if "candidates" in res_data and len(res_data["candidates"]) > 0:
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                cleaned = text.replace("```json", "").replace("```", "").strip()
                # 応答の前後に余計な文章が付くことがあるので、最初の { から最後の } までを抜き出す
                start = cleaned.find('{')
                end = cleaned.rfind('}')
                if start == -1 or end == -1 or end < start:
                    print(f"  ⚠️ Gemini応答がJSON形式ではありません: {cleaned[:80]}...")
                    return None
                parsed = json.loads(cleaned[start:end + 1])

                desc = str(parsed.get("description") or "").strip()
                if len(desc) > 80:
                    desc = desc[:77] + "..."

                raw_tags = parsed.get("tags") or []
                tags = [normalize_text(t) for t in raw_tags if isinstance(t, str) and t.strip()]
                return {"description": desc, "tags": tags}
        else:
            print(f"  ⚠️ Gemini API エラー {resp.status_code}")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  ⚠️ Gemini応答のJSON解析に失敗: {e}")
    except Exception as e:
        print(f"  ⚠️ Gemini API エラー: {e}")
    return None


def resolve_description_and_tags(product_name, maker_name, raw_description, jan, rules_map, allowed_tags, tag_catalog_text):
    """
    説明文とタグを決定する。GEMINI_API_KEYがあればAIに1回で両方頼み、
    失敗した場合やキー未設定の場合は rules.csv ベースの判定にフォールバックする
    （説明文が無くても products.csv は完成する、という既存の方針を維持）。
    """
    if GEMINI_API_KEY:
        print(f"  🤖 Geminiで説明文とタグを生成中...")
        ai_result = generate_description_and_tags_via_gemini(product_name, maker_name, raw_description, jan, tag_catalog_text)
        time.sleep(2)  # Gemini API レート制限対策（呼び出し回数は以前と変わらず1回のまま）
        if ai_result:
            tags = sorted({t for t in ai_result["tags"] if t in allowed_tags})
            if tags:
                if ai_result["description"]:
                    print(f"    ✅ 説明文生成: {ai_result['description'][:40]}...")
                print(f"    ✅ AIによるタグ判定: {' '.join(tags)}")
                return ai_result["description"], tags
            print(f"  ⚠️ Geminiのタグ候補が空/未登録タグのみだったため、ルールベース判定にフォールバックします")
        else:
            print(f"  ⚠️ Gemini呼び出しに失敗したため、ルールベース判定にフォールバックします")

    # フォールバック: rules.csv + 正規表現ベースの判定（説明文は生成できないので空のまま）
    tags = auto_assign_tags(product_name, maker_name, rules_map, allowed_tags)
    print(f"  🏷️ タグ（ルールベース）: {' '.join(tags)}")
    return "", tags

# ─────────────────────────────────────────────
# タグ自動判定
# ─────────────────────────────────────────────
def auto_assign_tags(product_name, maker_name, rules_map, allowed_tags):
    """
    rules.csv のルールと商品名から自動でタグを判定する。
    戻り値: ["dog", "adult", "gf", ...] のリスト
    """
    tags = set()
    check_text = normalize_text(f"{maker_name or ''} {product_name or ''}")

    # 1. rules.csv のキーワードマッチング
    for tag_id, keywords in rules_map.items():
        for kw in keywords:
            if kw in check_text:
                tags.add(normalize_text(tag_id))
                break

    # 2. 年齢判定
    name_lower = (product_name or "").lower()
    if re.search(r'子[犬猫]|パピー|puppy|子いぬ|子ねこ|り乳|幼犬|幼猫', name_lower):
        tags.add('puppy')
    elif re.search(r'シニア|senior|老[犬猫]|高齢', name_lower):
        tags.add('senior')
    elif re.search(r'成[犬猫]|adult|1歳|2歳|3歳|4歳|5歳|6歳', name_lower):
        tags.add('adult')
    else:
        # 「全年齢」「全齢」がなければall_agesにしない（デフォルトはadultと判断）
        if re.search(r'全年齢|全齢|all.?ages|オールステージ', name_lower):
            tags.add('all_ages')
        else:
            tags.add('adult')

    # 3. 動物種判定
    if re.search(r'[犬]|dog', name_lower):
        tags.add('dog')
    if re.search(r'[猫]|cat', name_lower):
        tags.add('cat')
    # dog も cat もなければ両方つける（汎用フード）
    if 'dog' not in tags and 'cat' not in tags:
        tags.add('dog')
        tags.add('cat')

    # 許可タグのみフィルタ
    return sorted([t for t in tags if t in allowed_tags])

def merge_into_existing(existing_row, new_data, fieldnames):
    """
    既存行に対して、AUTO_UPDATE_FIELDS の項目だけ新データで上書きする。
    新データの値が '#' や空文字の場合は既存値を維持する。
    手動編集項目（amz/yah/a8/label/promo/size/amz_p/yah_p など）は変更しない。
    """
    for field in AUTO_UPDATE_FIELDS:
        new_val = new_data.get(field)
        if new_val is not None and new_val != '#' and str(new_val).strip() != '':
            existing_row[field] = new_val
    # jan は変わらないはずだが念のため保持
    existing_row['jan'] = new_data.get('jan', existing_row.get('jan'))
    # fieldnames に存在しないキーが無いことを保証
    for f in fieldnames:
        if f not in existing_row:
            existing_row[f] = '#'
    return existing_row

# ─────────────────────────────────────────────
# メイン処理
# ─────────────────────────────────────────────

def fill_images_only(jans, existing_row_index, existing_rows):
    """既存行の img だけ更新する。名前・説明・タグは触らない。"""
    updated_count = 0
    api_calls = 0
    for idx, jan in enumerate(jans):
        if jan not in existing_row_index:
            print(f"⏭️ --img-only は既存行のみ対象のためスキップ: JAN {jan}")
            continue

        row = existing_row_index[jan]
        old_img = (row.get('img') or '').strip()
        name = row.get('name') or ''
        if is_catalog_image(old_img):
            print(f"⏭️ カタログ画像済みのためスキップ: JAN {jan}")
            continue

        print(f"\n{'─'*50}")
        print(f"[{idx+1}/{len(jans)}] JAN: {jan} （画像のみ） {name[:40]}")

        if not old_img or old_img == '#':
            sibling = find_sibling_image(jan, name, existing_rows)
            if sibling:
                row['img'] = sibling
                updated_count += 1
                print(f"  🧩 兄弟SKU画像を採用（APIスキップ）")
                continue

        if api_calls > 0:
            wait = 3.0 + random.uniform(0.5, 2.0)
            print(f"\n⏳ {wait:.0f}秒待機（レート制限回避）...")
            time.sleep(wait)
        api_calls += 1

        resolved = None
        prod_data = fetch_product_search_v2(jan)
        if prod_data and prod_data.get("image"):
            resolved = prod_data["image"]
            print(f"  ✅ Product Search 画像: {resolved[:50]}...")
        elif prod_data and prod_data.get("name"):
            print(f"  ℹ️ Product Search: 名前あり・画像なし → 画像だけ補完")
            if not name:
                name = prod_data["name"]

        resolved = resolve_better_image(jan, name, resolved, existing_rows)
        final = pick_better_image(old_img, resolved)
        if final and final != '#' and final != old_img:
            row['img'] = final
            updated_count += 1
            print(f"  ✅ img 更新")
        else:
            print(f"  ⏭️ 画像は更新しませんでした")
    return updated_count


def main(jan_list_path, img_only=False):
    if not os.path.exists(jan_list_path):
        print(f"エラー: JANコードリスト '{jan_list_path}' が見つかりません。")
        sys.exit(1)

    print(f"{'='*60}")
    print("pet925 全自動データ収集スクリプト")
    print(f"{'='*60}")

    # 設定チェック
    if not RAKUTEN_APP_ID or not RAKUTEN_ACCESS_KEY:
        print("❌ エラー: 楽天APIの設定が不足しています（RAKUTEN_APP_ID, RAKUTEN_ACCESS_KEY）")
        print("   .env ファイルまたは環境変数を確認してください。")
        sys.exit(1)

    print(f"🔑 楽天API: 設定済み")
    if GEMINI_API_KEY:
        print(f"🔑 Gemini API: 設定済み（説明文自動生成が有効）")
    else:
        print(f"⚠️ Gemini API: 未設定（説明文は自動生成されません。商品名のみで行きます）")

    # 各種データ読み込み
    rules_map = load_rules_map()
    allowed_tags = load_allowed_tags()
    tag_catalog_text = load_tag_catalog_text()

    print(f"\n📋 タグルール: {len(rules_map)}件")
    print(f"📋 許可タグ: {len(allowed_tags)}件")

    # ── 既存 products.csv 読み込み ──
    existing_rows = []
    existing_jans = set()
    fieldnames = FIELD_NAMES
    if os.path.exists(PRODUCT_CSV) and os.path.getsize(PRODUCT_CSV) > 0:
        with open(PRODUCT_CSV, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or fieldnames
            for row in reader:
                jan = normalize_jan(row.get('jan', ''))
                if jan and jan != '#':
                    existing_jans.add(jan)
                existing_rows.append(row)
    print(f"\n📂 既存 products.csv: {len(existing_rows)}行 ({len(existing_jans)}件のJAN)")

    # JAN → 既存行 のインデックス（更新用マージに使用）
    existing_row_index = {}
    for row in existing_rows:
        jan_key = normalize_jan(row.get('jan', ''))
        if jan_key and jan_key != '#':
            existing_row_index[jan_key] = row

    # ── JANリスト読み込み ──
    new_jans = []
    update_jans = []
    seen_in_list = set()
    with open(jan_list_path, 'r', encoding='utf-8-sig', newline='') as f:
        for i, row in enumerate(csv.reader(f)):
            if not row: continue
            jan = normalize_jan(row[0])
            if jan and jan != 'Undefined' and jan.isdigit() and len(jan) == 13:
                jan13 = jan
                if jan13 in seen_in_list:
                    print(f"⏭️ 入力ファイル内で重複のためスキップ: JAN {jan13}")
                    continue
                seen_in_list.add(jan13)
                if jan13 in existing_jans:
                    update_jans.append(jan13)
                    print(f"🔄 更新対象: JAN {jan13}")
                else:
                    new_jans.append(jan13)
            else:
                print(f"⚠️ 無効な行 {i+1}: '{row[0]}'")

    all_jans = new_jans + update_jans

    if not all_jans:
        print("\n✅ 処理対象のJANコードはありません。処理を終了します。")
        return

    print(f"\n{'='*60}")
    print(f"🆕 新規JANコード: {len(new_jans)}件 / 🔄 更新JANコード: {len(update_jans)}件 を処理します")
    print(f"{'='*60}")

    def write_products_csv(collected_count=0, updated_count=0):
        existing_rows.sort(key=lambda r: (0, normalize_jan(r.get('jan', '#'))) if r.get('jan', '#') != '#' and r['jan'].isdigit() else (1, r.get('name', '')))
        with open(PRODUCT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_rows)
        print(f"\n✅ products.csv を更新しました（全{len(existing_rows)}行、新規{collected_count}件・更新{updated_count}件）")
        print(f"💡 内容を確認するには ODS で開くか、以下のコマンドを実行:")
        print(f"   python3 csv_to_json.py")
        print(f"💡 手動で微調整したい場合は pet925_master.ods の products シートに貼り付けてください")

    if img_only:
        print("🖼 画像のみ更新モード（名前・説明・タグは変更しません）")
        updated_count = fill_images_only(all_jans, existing_row_index, existing_rows)
        sibling_filled = apply_sibling_images(existing_rows)
        print(f"\n{'='*60}")
        print(f"完了: img 更新 {updated_count}件 / 兄弟SKU補完 {sibling_filled}件")
        if updated_count or sibling_filled:
            write_products_csv(updated_count=updated_count + sibling_filled)
        else:
            print("画像の更新はありませんでした。")
        return

    # ── 各JANを処理 ──
    collected = []
    updated = []
    success_count = 0
    update_jans_set = set(update_jans)

    for idx, jan in enumerate(all_jans):
        if idx > 0:
            wait = 3.0 + random.uniform(0.5, 2.0)
            print(f"\n⏳ {wait:.0f}秒待機（レート制限回避）...")
            time.sleep(wait)

        is_update = jan in update_jans_set
        print(f"\n{'─'*50}")
        print(f"[{idx+1}/{len(all_jans)}] JAN: {jan} {'（更新）' if is_update else '（新規）'}")


        # Step 1: Product Search API v2（一発取得）
        prod_data = fetch_product_search_v2(jan)
        if prod_data and prod_data.get("name"):
            product_name = prod_data["name"]
            maker_name = prod_data.get("makerName") or prod_data.get("brandName") or ""
            raw_desc = prod_data.get("description") or ""
            catalog_price = prod_data.get("catalogPrice")
            image_url = prod_data.get("image")

            print(f"  ✅ Product Search API: {product_name[:40]}...")
            if maker_name:
                print(f"    メーカー: {maker_name}")
            if catalog_price:
                print(f"    価格: {catalog_price}円")
            if image_url:
                print(f"    画像: {image_url[:50]}...")
            else:
                print(f"    画像なし → 画像だけフォールバック")

            old_img = existing_row_index[jan].get('img') if is_update else None
            image_url = resolve_better_image(jan, product_name, image_url, existing_rows)
            image_url = pick_better_image(old_img, image_url)

            # Step 2+3: 説明文とタグをGeminiに1回でまとめて頼む（失敗時はルールベースにフォールバック）
            description, tags = resolve_description_and_tags(
                product_name, maker_name, raw_desc, jan, rules_map, allowed_tags, tag_catalog_text
            )

            # Step 4: ブランド名（APIのメーカー名をそのまま。空なら空欄）
            brand_display = maker_name or ""

            # Step 5: 価格
            price_str = str(catalog_price) if catalog_price and catalog_price > 0 else "0"

            # Step 6: 結果を保存
            new_row = {f: '#' for f in fieldnames}
            new_row['jan'] = jan
            new_row['name'] = product_name
            new_row['brand'] = brand_display
            new_row['tags'] = ' '.join(tags)
            new_row['desc'] = description
            new_row['img'] = image_url or '#'
            new_row['rak'] = '#'  # 表示時に商品名で検索URLを生成させる
            new_row['rak_p'] = price_str

            if is_update:
                merged = merge_into_existing(existing_row_index[jan], new_row, fieldnames)
                updated.append(merged)
            else:
                collected.append(new_row)
            success_count += 1
            continue


        # Step 1-b: Item Search API（フォールバック）
        print(f"  [フォールバック] Item Search API を試行...")
        item_data = fetch_item_search(jan)
        if item_data and item_data.get("name"):
            product_name = item_data["name"]
            image_url = item_data.get("image")
            item_url = item_data.get("url")

            print(f"  ✅ Item Search API: {product_name[:40]}...")

            old_img = existing_row_index[jan].get('img') if is_update else None
            image_url = resolve_better_image(jan, product_name, image_url, existing_rows, try_item=False, try_yahoo=True)
            image_url = pick_better_image(old_img, image_url)

            # 説明文とタグをGeminiに1回でまとめて頼む（元ネタなし。失敗時はルールベースにフォールバック）
            description, tags = resolve_description_and_tags(
                product_name, "", "", jan, rules_map, allowed_tags, tag_catalog_text
            )

            new_row = {f: '#' for f in fieldnames}
            new_row['jan'] = jan
            new_row['name'] = product_name
            new_row['brand'] = ''
            new_row['tags'] = ' '.join(tags)
            new_row['desc'] = description
            new_row['img'] = image_url or '#'
            new_row['rak'] = item_url or '#'  # 実商品URLがあれば使用、なければ表示時に商品名で生成
            new_row['rak_p'] = '0'

            if is_update:
                merged = merge_into_existing(existing_row_index[jan], new_row, fieldnames)
                updated.append(merged)
            else:
                collected.append(new_row)
            success_count += 1
            continue


        # Step 1-c: Yahoo! ショッピング（最終フォールバック）
        print(f"  [最終フォールバック] Yahoo!ショッピングAPI を試行...")
        yahoo_data = fetch_yahoo_shopping(jan)
        if yahoo_data and yahoo_data.get("name"):
            product_name = yahoo_data["name"]
            image_url = yahoo_data.get("image")

            print(f"  ✅ Yahoo! Shopping: {product_name[:40]}...")

            old_img = existing_row_index[jan].get('img') if is_update else None
            image_url = resolve_better_image(jan, product_name, image_url, existing_rows, try_item=False, try_yahoo=False)
            image_url = pick_better_image(old_img, image_url)

            description, tags = resolve_description_and_tags(
                product_name, "", "", jan, rules_map, allowed_tags, tag_catalog_text
            )

            new_row = {f: '#' for f in fieldnames}
            new_row['jan'] = jan
            new_row['name'] = product_name
            new_row['brand'] = ''
            new_row['tags'] = ' '.join(tags)
            new_row['desc'] = description
            new_row['img'] = image_url or '#'
            new_row['yah'] = '#'  # 表示時に商品名で検索URLを生成させる
            new_row['rak_p'] = '0'

            if is_update:
                merged = merge_into_existing(existing_row_index[jan], new_row, fieldnames)
                updated.append(merged)
            else:
                collected.append(new_row)
            success_count += 1
            continue

        print(f"  ❌ 全API失敗: JAN={jan}")

    # ── products.csv に追記・更新 ──
    print(f"\n{'='*60}")
    print(f"完了: {success_count}/{len(all_jans)}件取得成功（新規 {len(collected)}件 / 更新 {len(updated)}件）")

    if collected or updated:
        # 新規行を既存行リストに追加
        # （updated の内容は existing_row_index 経由で existing_rows 内のオブジェクトを
        #   直接書き換えているため、既に existing_rows に反映済み）
        for item in collected:
            jan = item.get('jan', '')
            if jan:
                existing_rows.append(item)

        sibling_filled = apply_sibling_images(existing_rows)
        if sibling_filled:
            print(f"🧩 書き出し前の兄弟SKU補完: {sibling_filled}件")

        write_products_csv(collected_count=len(collected), updated_count=len(updated))
    else:
        print("どのAPIからもデータを取得できませんでした。")
        print("JANコードが正しいか確認してください。")


if __name__ == '__main__':
    flags = {a for a in sys.argv[1:] if a.startswith('--')}
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    unknown = flags - {'--img-only'}
    if unknown:
        print(f"不明なオプション: {' '.join(sorted(unknown))}")
        sys.exit(1)
    if not args:
        print("使用法: python3 auto_collect_all.py [JANリストCSV] [--img-only]")
        print("")
        print("JANリストCSVの形式: 1列目に13桁のJANコードを並べたファイル")
        print("例: python3 auto_collect_all.py jan_list.csv")
        print("例: python3 auto_collect_all.py jan_list.csv --img-only")
        sys.exit(1)
    main(args[0], img_only='--img-only' in flags)