#!/usr/bin/env python3
"""
商品説明文だけを作り直すローカルツール。

使い方:
  python3 desc_helper.py
  または npm run desc:helper

ブラウザで http://127.0.0.1:8765 が開きます。
CSV の商品名を貼り、任意で公式 URL またはブックマークレットの本文を添えて生成します。
結果はクリップボードへコピーするだけで、products.csv は自動更新しません。
"""
import ipaddress
import json
import os
import re
import socket
import sys
import webbrowser
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests

from pet_utils import get_env_value, load_dict_rows

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(BASE_DIR, "desc_helper.html")
INSTRUCTIONS_PATH = os.path.join(BASE_DIR, "docs", "AI_INSTRUCTIONS.md")
PRODUCT_CSV = os.path.join(BASE_DIR, "data", "products.csv")
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
FACT_CHAR_LIMIT = 1800
FETCH_BYTE_LIMIT = 200_000
GEMINI_MODEL = "gemini-2.5-flash"

GEMINI_API_KEY = get_env_value("GEMINI_API_KEY")

DESC_RULES_FALLBACK = """
- 説明文 (desc): 商品の特徴を60文字程度で具体的にまとめてください。メーカーのこだわりや、「どんな悩みを持つ犬・猫におすすめか」というユーザー視点を必ず含めてください。
- 検索最適化 (SEO): ユーザーが検索しそうな単語を自然な文章の中に含め、機械的な羅列ではなく読み物としての品質を維持してください。
- 出力は説明文1つだけ。CSV・見出し・引用符・解説は不要。
- 参考テキストは事実確認用。フレーズのコピーも一文ずつの言い換えも禁止。
- 確認できない効果や宣伝文句は書かない。
- 50〜70字程度。
- 良い説明文の例: すり身のサーモンを第一主原料に使用。肉食の祖先が食べていた食事を再現した高タンパク・穀物不使用のフードです。
""".strip()

HELPER_ORIGIN = f"http://{HOST}:{DEFAULT_PORT}"


def normalize_name(value):
    if value is None:
        return ""
    return str(value).strip().strip('"').strip("'").strip()


def find_product_row(name):
    target = normalize_name(name)
    if not target:
        return None
    for row in load_dict_rows(PRODUCT_CSV):
        if normalize_name(row.get("name")) == target:
            return row
    return None


def load_desc_rules():
    if not os.path.exists(INSTRUCTIONS_PATH):
        return DESC_RULES_FALLBACK
    with open(INSTRUCTIONS_PATH, "r", encoding="utf-8") as f:
        text = f.read()
    sections = re.split(r"\n(?=## )", text)
    parts = []
    for sec in sections:
        heading = sec.split("\n", 1)[0]
        if heading.startswith("## 3."):
            kept = [
                line for line in sec.splitlines()
                if any(key in line for key in ("説明文", "検索最適化", "SEO"))
            ]
            if kept:
                parts.append("\n".join(kept))
        elif heading.startswith("## 9."):
            parts.append(sec.strip())
    return "\n\n".join(parts) if parts else DESC_RULES_FALLBACK


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_facts(raw_html, limit=FACT_CHAR_LIMIT):
    parser = _VisibleText()
    try:
        parser.feed(raw_html)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", raw_html)
        return re.sub(r"\s+", " ", text).strip()[:limit]
    text = re.sub(r"\s+", " ", "".join(parser.parts)).strip()
    return text[:limit]


def _host_is_public(hostname, port):
    if not hostname:
        return False
    lowered = hostname.lower().rstrip(".")
    if lowered in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return False
    try:
        infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False
    if not infos:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if not ip.is_global:
            return False
    return True


def is_public_http_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.username or parsed.password:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return _host_is_public(parsed.hostname, port)


def fetch_url_facts(url):
    current = url.strip()
    for _ in range(3):
        if not is_public_http_url(current):
            raise ValueError("このURLは取得できません。公開サイトの http(s) アドレスを指定してください。")
        resp = requests.get(
            current,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; pet925-desc-helper/1.0)"},
            allow_redirects=False,
            stream=True,
        )
        if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("Location")
            resp.close()
            if not location:
                raise ValueError("リダイレクト先がありません。")
            current = urljoin(current, location)
            continue
        resp.raise_for_status()
        chunks = []
        total = 0
        for chunk in resp.iter_content(8192):
            total += len(chunk)
            if total > FETCH_BYTE_LIMIT:
                break
            chunks.append(chunk)
        raw = b"".join(chunks).decode(resp.encoding or "utf-8", errors="replace")
        return html_to_facts(raw)
    raise ValueError("リダイレクトが多すぎます。")


def clean_desc(text):
    text = text.replace("```", "").strip()
    text = re.sub(r"^説明文[:：]\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip().strip('"').strip("'")
    return text


def generate_desc(name, facts, product_row):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY が .env にありません。")

    brand = ""
    tags = ""
    current_desc = ""
    if product_row:
        brand = (product_row.get("brand") or "").strip()
        tags = (product_row.get("tags") or "").strip()
        current_desc = (product_row.get("desc") or "").strip()

    fact_block = facts.strip() if facts else "（参考テキストなし。商品名とCSV属性だけから書き、確認できない効果は書かない）"
    current_note = current_desc if current_desc else "（なし）"

    prompt = f"""あなたはペットフード比較サイト「pet925」のデータ作成アシスタントです。
次の品質ルールにだけ従って、説明文（desc）を1つ出力してください。
CSV・タグ・価格・URL の生成ルールは無視してください。

{load_desc_rules()}

【商品名】{name}
【CSV上のブランド】{brand or "不明"}
【CSV上のタグ（事実のヒント。タグ名を説明文に並べない）】{tags or "なし"}
【CSVの現在の説明文（改善対象。コピーするな）】{current_note}
【参考事実（原文を使うな）】
{fact_block}

説明文だけを出力すること。
"""

    api_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = requests.post(api_url, json=payload, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini API エラー ({resp.status_code}): {resp.text[:300]}")
    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini から説明文を受け取れませんでした。")
    text = candidates[0]["content"]["parts"][0]["text"]
    desc = clean_desc(text)
    if not desc:
        raise RuntimeError("生成結果が空でした。")
    return desc


def send_json(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def load_html():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    return html.replace("__HELPER_ORIGIN__", HELPER_ORIGIN)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/desc_helper.html"):
            body = load_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/lookup":
            qs = parse_qs(parsed.query)
            name = unquote((qs.get("name") or [""])[0])
            row = find_product_row(name)
            if not row:
                send_json(self, 200, {"matched": False})
                return
            a8 = (row.get("a8") or "").strip()
            send_json(self, 200, {
                "matched": True,
                "current_desc": (row.get("desc") or "").strip(),
                "brand": (row.get("brand") or "").strip(),
                "tags": (row.get("tags") or "").strip(),
                "a8": a8 if a8 not in ("", "#") else "",
            })
            return
        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/desc":
            self.send_error(404, "Not Found")
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > 100_000:
            send_json(self, 400, {"error": "リクエストが大きすぎます。"})
            return
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            send_json(self, 400, {"error": "JSON を解析できません。"})
            return

        name = normalize_name(payload.get("name"))
        url = (payload.get("url") or "").strip()
        source_text = (payload.get("source_text") or "").strip()
        if not name:
            send_json(self, 400, {"error": "商品名を貼ってください。"})
            return

        row = find_product_row(name)
        facts = html_to_facts(source_text) if source_text else ""
        fact_source = "bookmarklet" if facts else None
        if not facts and url:
            try:
                facts = fetch_url_facts(url)
                fact_source = "url"
            except Exception as e:
                send_json(self, 400, {"error": f"参考URLの取得に失敗しました: {e}"})
                return

        try:
            desc = generate_desc(name, facts, row)
        except Exception as e:
            send_json(self, 500, {"error": str(e)})
            return

        send_json(self, 200, {
            "desc": desc,
            "matched": bool(row),
            "current_desc": (row.get("desc") or "").strip() if row else "",
            "fact_source": fact_source,
        })


def find_free_port(start=DEFAULT_PORT):
    for port in range(start, start + 10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((HOST, port))
                return port
            except OSError:
                continue
    raise RuntimeError("空きポートが見つかりませんでした。")


def main():
    global HELPER_ORIGIN
    if not os.path.exists(HTML_PATH):
        print(f"❌ {HTML_PATH} が見つかりません。")
        sys.exit(1)
    port = find_free_port()
    HELPER_ORIGIN = f"http://{HOST}:{port}"
    server = ThreadingHTTPServer((HOST, port), Handler)
    print(f"📝 説明文ツール: {HELPER_ORIGIN}/")
    if not GEMINI_API_KEY:
        print("⚠️  GEMINI_API_KEY が未設定です。.env に追加してください。")
    print("終了するには Ctrl+C")
    try:
        webbrowser.open(HELPER_ORIGIN + "/")
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止しました。")
        server.server_close()


if __name__ == "__main__":
    main()
