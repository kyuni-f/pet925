#!/usr/bin/env python3
"""
products.csv の画像URL（img）と公式ページURL（a8）が生きているかを確認する。

使い方:
  python3 check_links.py
  python3 check_links.py --img-only
  python3 check_links.py --a8-only

ビルド（npm run build）には組み込まない。ネット障害で公開が止まらないようにするため。
切れがあっても CSV は書き換えない。直すかどうかは目視の判断。
"""

import argparse
import json
import os
import struct
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests

from pet_utils import load_dict_rows, RAKUTEN_REQUEST_HEADERS

PRODUCT_CSV = os.path.join("data", "products.csv")

TIMEOUT = 12
MAX_WORKERS = 6
MAX_IMAGE_BYTES = 65536
TINY_IMAGE_BYTES = 1500

COLOR_RED = "\033[31m"
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}


def parse_url_list(raw):
    """img / a8 のセルからチェック対象URL（またはローカルパス）を取り出す。# と空は対象外。"""
    val = str(raw or "").strip().strip('"').strip("'")
    if not val or val == "#":
        return []
    if val.startswith("["):
        try:
            parsed = json.loads(val)
        except json.JSONDecodeError:
            return [val]
        if isinstance(parsed, list):
            urls = []
            for item in parsed:
                item_s = str(item).strip()
                if item_s and item_s != "#":
                    urls.append(item_s)
            return urls
    return [val]


def is_http_url(value):
    return value.startswith("http://") or value.startswith("https://")


def is_local_image_path(value):
    return value.startswith("images/") or value.startswith("images\\")


def jpeg_dimensions(data):
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 <= len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (
            0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
            0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
        ):
            height, width = struct.unpack(">HH", data[i + 5:i + 9])
            return width, height
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7 or marker == 0x01:
            i += 2
            continue
        if i + 4 > len(data):
            break
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        if length < 2:
            break
        i += 2 + length
    return None


def image_dimensions(data):
    """先頭バイトから PNG / GIF / JPEG / WebP の幅・高さを読む。分からなければ None。"""
    if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n"):
        width, height = struct.unpack(">II", data[16:24])
        return width, height
    if len(data) >= 10 and data[:6] in (b"GIF87a", b"GIF89a"):
        width, height = struct.unpack("<HH", data[6:10])
        return width, height
    jpeg = jpeg_dimensions(data)
    if jpeg:
        return jpeg
    if len(data) >= 30 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        kind = data[12:16]
        if kind == b"VP8X" and len(data) >= 30:
            width = 1 + int.from_bytes(data[24:27], "little")
            height = 1 + int.from_bytes(data[27:30], "little")
            return width, height
        if kind == b"VP8 " and len(data) >= 30:
            width = struct.unpack("<H", data[26:28])[0] & 0x3FFF
            height = struct.unpack("<H", data[28:30])[0] & 0x3FFF
            return width, height
    return None


def is_homepage_url(url):
    parsed = urlparse(url)
    path = (parsed.path or "/").rstrip("/")
    return path in ("", "/")


def request_headers_for(url, kind):
    host = (urlparse(url).hostname or "").lower()
    if "r10s.jp" in host or "rakuten" in host:
        return dict(RAKUTEN_REQUEST_HEADERS)
    headers = dict(BROWSER_HEADERS)
    if kind == "img":
        headers["Accept"] = "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
    else:
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    return headers


def check_local_image(path):
    if not os.path.isfile(path):
        return "broken", f"ローカルファイルが無い: {path}", 0, None
    size = os.path.getsize(path)
    if size < TINY_IMAGE_BYTES:
        return "broken", f"ファイルが小さすぎる ({size} bytes)", size, None
    with open(path, "rb") as f:
        data = f.read(MAX_IMAGE_BYTES)
    dims = image_dimensions(data)
    if dims and min(dims) <= 1:
        return "broken", f"1px画像の可能性 {dims[0]}x{dims[1]}", size, dims
    return "ok", "ローカルファイル", size, dims


def check_remote(kind, url):
    headers = request_headers_for(url, kind)
    try:
        resp = requests.get(
            url,
            headers=headers,
            timeout=TIMEOUT,
            stream=True,
            allow_redirects=True,
        )
    except requests.Timeout:
        return "broken", "タイムアウト", 0, None, url
    except requests.RequestException as exc:
        return "broken", f"接続失敗: {exc.__class__.__name__}", 0, None, url

    status = resp.status_code
    final_url = resp.url
    try:
        if kind == "img":
            chunks = []
            total = 0
            for chunk in resp.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                chunks.append(chunk)
                total += len(chunk)
                if total >= MAX_IMAGE_BYTES:
                    break
            data = b"".join(chunks)
            content_length = resp.headers.get("Content-Length")
            try:
                declared = int(content_length) if content_length else None
            except ValueError:
                declared = None
            size = declared if declared is not None else len(data)
        else:
            data = b""
            size = 0
    finally:
        resp.close()

    if status in (404, 410):
        return "broken", f"HTTP {status}", size, None, final_url
    if status in (401, 403):
        return "review", f"HTTP {status}（ボット拒否の可能性）", size, None, final_url
    if status >= 500:
        return "review", f"HTTP {status}（一時障害の可能性）", size, None, final_url
    if status >= 400:
        return "broken", f"HTTP {status}", size, None, final_url

    if kind == "img":
        if size < TINY_IMAGE_BYTES and len(data) < TINY_IMAGE_BYTES:
            return "broken", f"中身が小さすぎる ({size} bytes / 1pxプレースホルダーの可能性)", size, None, final_url
        dims = image_dimensions(data)
        if dims and min(dims) <= 1:
            return "broken", f"1px画像 {dims[0]}x{dims[1]}", size, dims, final_url
        return "ok", f"HTTP {status}", size, dims, final_url

    if not is_homepage_url(url) and is_homepage_url(final_url):
        return "review", f"HTTP {status}（トップページへリダイレクト）", size, None, final_url
    return "ok", f"HTTP {status}", size, None, final_url


def check_target(task):
    kind, url, name, jan, line_num = task
    if is_local_image_path(url) or (kind == "img" and not is_http_url(url)):
        local_path = url.replace("\\", "/") if is_local_image_path(url) else url
        level, detail, size, dims = check_local_image(local_path)
        return {
            "level": level,
            "kind": kind,
            "name": name,
            "jan": jan,
            "line": line_num,
            "url": url,
            "detail": detail,
            "size": size,
            "dims": dims,
            "final_url": url,
        }

    if not is_http_url(url):
        return {
            "level": "broken",
            "kind": kind,
            "name": name,
            "jan": jan,
            "line": line_num,
            "url": url,
            "detail": "http(s) でも images/ でもない",
            "size": 0,
            "dims": None,
            "final_url": url,
        }

    level, detail, size, dims, final_url = check_remote(kind, url)
    return {
        "level": level,
        "kind": kind,
        "name": name,
        "jan": jan,
        "line": line_num,
        "url": url,
        "detail": detail,
        "size": size,
        "dims": dims,
        "final_url": final_url,
    }


def collect_tasks(rows, check_img, check_a8):
    tasks = []
    skipped = {"img": 0, "a8": 0}
    for index, row in enumerate(rows, start=2):
        name = (row.get("name") or "").strip()
        if not name or name.lower() == "name" or name == "商品名":
            continue
        jan = (row.get("jan") or "#").strip() or "#"
        if check_img:
            urls = parse_url_list(row.get("img"))
            if not urls:
                skipped["img"] += 1
            for url in urls:
                tasks.append(("img", url, name, jan, index))
        if check_a8:
            urls = parse_url_list(row.get("a8"))
            if not urls:
                skipped["a8"] += 1
            for url in urls:
                tasks.append(("a8", url, name, jan, index))
    return tasks, skipped


def print_issue(item):
    kind_label = "画像" if item["kind"] == "img" else "公式"
    print(f"  [{kind_label}] 行 {item['line']}: {item['name']}  JAN {item['jan']}")
    print(f"           {item['url']}")
    if item["final_url"] and item["final_url"] != item["url"]:
        print(f"           → {item['final_url']}")
    extra = ""
    if item["dims"]:
        extra = f" {item['dims'][0]}x{item['dims'][1]}"
    elif item["size"]:
        extra = f" {item['size']} bytes"
    print(f"           {item['detail']}{extra}")


def main():
    parser = argparse.ArgumentParser(description="products.csv の img / a8 URL 生死チェック")
    parser.add_argument("--img-only", action="store_true", help="画像URLだけ見る")
    parser.add_argument("--a8-only", action="store_true", help="公式ページURLだけ見る")
    args = parser.parse_args()

    check_img = not args.a8_only
    check_a8 = not args.img_only
    if args.img_only and args.a8_only:
        check_img = True
        check_a8 = True

    if not os.path.exists(PRODUCT_CSV):
        print(f"{COLOR_RED}エラー: {PRODUCT_CSV} が見つかりません。{COLOR_RESET}")
        sys.exit(1)

    rows = load_dict_rows(PRODUCT_CSV)
    tasks, skipped = collect_tasks(rows, check_img, check_a8)

    targets = []
    if check_img:
        targets.append("img")
    if check_a8:
        targets.append("a8")

    print("--- リンク生死チェック ---")
    print(f"   対象列: {', '.join(targets)}")
    print(f"   商品行: {len(rows)}件 / 実際に叩くURL: {len(tasks)}件")
    if check_img:
        print(f"   未設定 img (#): {skipped['img']}件")
    if check_a8:
        print(f"   未設定 a8 (#): {skipped['a8']}件")
    print("   ※ ビルドや CSV は変更しません。切れの修正は手作業です。")

    if not tasks:
        print(f"\n{COLOR_GREEN}{COLOR_BOLD}✅ チェック対象のURLがありません（すべて未設定）。{COLOR_RESET}")
        sys.exit(0)

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(check_target, task) for task in tasks]
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda item: (item["line"], item["kind"], item["url"]))
    broken = [item for item in results if item["level"] == "broken"]
    review = [item for item in results if item["level"] == "review"]
    ok_count = sum(1 for item in results if item["level"] == "ok")

    if broken:
        print(f"\n{COLOR_RED}{COLOR_BOLD}⚠️  切れ {len(broken)} 件:{COLOR_RESET}")
        for item in broken:
            print_issue(item)

    if review:
        print(f"\n{COLOR_YELLOW}{COLOR_BOLD}💡 要確認 {len(review)} 件（ボット拒否・一時障害・トップへ飛ばされた）:{COLOR_RESET}")
        for item in review:
            print_issue(item)

    print(f"\n   結果: OK {ok_count} / 切れ {len(broken)} / 要確認 {len(review)}")
    if broken:
        print(f"{COLOR_RED}{COLOR_BOLD}❌ 切れがあります。img は URL の貼り直し or images/JAN.jpg。a8 は公式URLの確認。{COLOR_RESET}")
        print("   collect:all で全件取り直すと、手直しした説明文も戻ります。切れた JAN だけ直してください。")
        sys.exit(1)

    if review:
        print(f"{COLOR_YELLOW}切れはありません。要確認だけ目視してください。{COLOR_RESET}")
        sys.exit(0)

    print(f"{COLOR_GREEN}{COLOR_BOLD}✅ 対象URLはすべて取得できました。{COLOR_RESET}")
    sys.exit(0)


if __name__ == "__main__":
    main()
