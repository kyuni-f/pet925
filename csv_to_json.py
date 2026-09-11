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

from pet_utils import (
    normalize_text,
    get_env_value,
    load_dict_rows,
)



# 設定
DATA_DIR = 'data'  # CSVファイルが格納されているディレクトリ
PRODUCT_CSV = os.path.join(DATA_DIR, 'products.csv')
CAT_CSV = os.path.join(DATA_DIR, 'categories.csv')
TAG_CSV = os.path.join(DATA_DIR, 'tags.csv')
RULE_CSV = os.path.join(DATA_DIR, 'rules.csv')
ALIAS_CSV = os.path.join(DATA_DIR, 'aliases.csv')

OUTPUT_JSON = 'product_data.json'
CHUNK_SIZE = 5000  # 1ファイルあたりの最大件数
OUTPUT_MASTER_JS = 'data_master.js'

# 問い合わせフォーム（Formspree）のフォームID。宛先メールは Formspree 側にだけ置き、サイトには出さない
def load_contact_config():
    raw = (get_env_value("FORMSPREE_FORM_ID") or "").strip()
    form_id = raw if re.fullmatch(r"[A-Za-z0-9]+", raw) else ""
    return {"form_id": form_id}

contact_config = load_contact_config()
FORMSPREE_FORM_ID = contact_config["form_id"]

# CSVファイル名と、それがdata_master.jsでどの変数名になるかのマッピング
# products.csv は特別扱いなのでここには含めない
SPECIFIC_MASTER_CSVS = {
    'categories.csv', 'tags.csv', 'rules.csv', 'aliases.csv'
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

BUILD_REPORT_HTML = 'build_report.html'
# 説明文の単語ではタグを提案しない。日常確認は必須欠け・矛盾・商品名の硬い一致だけ。
REVIEW_WARN_MARKERS = ('必須タグ欠け', 'タグ矛盾', '商品名に')
NAME_HIT_MIN_KW_LEN = 2


def _html_escape(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


def _strip_tag_display_name(name):
    """tags.csv の表示名から末尾の英語カッコ（例: (TEAR)）を除く。"""
    return re.sub(r'\s*[（(][^（()）]*[）)]\s*$', '', name or '').strip()


def _render_tag_badges(tag_names):
    """商品カードに実際に出るタグバッジと同じ見た目（style.cssの .tag 相当）を、
    外部CSS無しでも再現できるようインラインstyleで描画する。"""
    if not tag_names:
        return '<span class="muted">（バッジなし）</span>'
    badge_style = ('font-size:11px;color:#999;border:1px solid #eee;padding:3px 8px;'
                   'text-transform:uppercase;display:inline-block;margin:0 4px 4px 0;white-space:nowrap;')
    return ''.join(f'<span style="{badge_style}">{_html_escape(n)}</span>' for n in tag_names)


def _render_card_preview(item):
    """サイトの商品カード相当：condバッジ + 説明文。サイトを開かずに判断するための欄。"""
    badges = _render_tag_badges(item.get('current_tags') or [])
    desc = (item.get('desc') or '').strip()
    desc_html = _html_escape(desc) if desc else '<span class="muted">（説明なし）</span>'
    return f'<div class="card-preview">{badges}<div class="desc">{desc_html}</div></div>'


def _empty_review():
    return {"missing": [], "conflicts": [], "name_hits": []}


def write_build_report(errors, warnings, missing_required, tag_conflicts, name_hits,
                       product_count, exec_time_str, duration):
    """npm run build の結果を色分けHTMLレポートとして書き出す。
    products.csv / pet925_master.ods は一切書き換えず、確認用の別ファイルとして毎回上書きする。
    説明文の単語一致ではタグを提案しない（読み物・検索用の語がバッジ確認を汚さないようにする）。
    """
    other_warnings = [w for w in warnings if not any(m in w for m in REVIEW_WARN_MARKERS)]

    parts = []
    parts.append('<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">')
    parts.append('<title>pet925 ビルドレポート</title><style>')
    parts.append('''
body { font-family: -apple-system, "Hiragino Sans", Meiryo, sans-serif; margin: 24px; color: #222; }
h1 { font-size: 20px; }
h2 { font-size: 16px; margin-top: 32px; border-bottom: 2px solid #ddd; padding-bottom: 4px; }
.summary { color: #555; margin-bottom: 20px; }
table { border-collapse: collapse; width: 100%; margin-top: 10px; }
th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; font-size: 14px; vertical-align: top; }
th { background: #f0f0f0; }
tr.error td { background: #ffe0e0; }
tr.warning td { background: #fff8d6; }
.empty { color: #2a7d2a; font-weight: bold; }
code { background: #f5f5f5; padding: 1px 4px; border-radius: 3px; }
.muted { color: #bbb; }
.card-preview .desc { margin-top: 6px; color: #444; max-width: 28em; line-height: 1.45; }
''')
    parts.append('</style></head><body>')
    parts.append('<h1>pet925 ビルドレポート</h1>')
    parts.append(f'<p class="summary">実行時刻: {_html_escape(exec_time_str)} / 処理時間: {duration:.2f}秒 / '
                  f'商品件数: {product_count}件<br>'
                  'このファイルは npm run build のたびに上書きされます。products.csv や pet925_master.ods は書き換えません。'
                  'コピペしてODS側の修正に使ってください。<br>'
                  'タグの正は tags 列です。説明文の単語ではタグを提案しません。'
                  '「カード相当」はサイトの商品カードと同じ cond バッジと説明文なので、サイトを開かなくても判断できます。</p>')

    # 1. データ不備（エラー。ビルドを止める原因）
    parts.append(f'<h2>データ不備 ({len(errors)}件)</h2>')
    if errors:
        parts.append('<table><tr><th>内容</th></tr>')
        for e in errors:
            parts.append(f'<tr class="error"><td>{_html_escape(e)}</td></tr>')
        parts.append('</table>')
    else:
        parts.append('<p class="empty">✅ データ不備はありません。</p>')

    # 2. 必須タグ欠け（animal / age）
    parts.append(f'<h2>必須タグ欠け ({len(missing_required)}件)</h2>')
    if missing_required:
        parts.append('<p class="summary">犬/猫（animal）または年齢（age）が tags 列に無い商品です。'
                      'cond のお悩みバッジとは別で、フィルターの共通枠に使います。カード相当の列で説明文も確認できます。</p>')
        parts.append('<table><tr><th>JAN</th><th>商品名</th><th>カード相当（バッジ＋説明文）</th>'
                      '<th>現在の tags 列</th><th>欠け</th><th>行番号</th></tr>')
        for s in sorted(missing_required, key=lambda x: x['line']):
            parts.append('<tr class="warning">'
                          f'<td>{_html_escape(s["jan"])}</td>'
                          f'<td>{_html_escape(s["name"])}</td>'
                          f'<td>{_render_card_preview(s)}</td>'
                          f'<td><code>{_html_escape(s["all_tags"])}</code></td>'
                          f'<td>{_html_escape(s["detail"])}</td>'
                          f'<td>{s["line"]}</td></tr>')
        parts.append('</table>')
    else:
        parts.append('<p class="empty">✅ 必須タグの欠けはありません。</p>')

    # 3. タグの矛盾
    parts.append(f'<h2>タグの矛盾 ({len(tag_conflicts)}件)</h2>')
    if tag_conflicts:
        parts.append('<p class="summary">同時には付かないはずのタグが付いている商品です（例: 年齢タグが2つ以上）。'
                      '付けるなら1つに揃えてください。</p>')
        parts.append('<table><tr><th>JAN</th><th>商品名</th><th>カード相当（バッジ＋説明文）</th>'
                      '<th>現在の tags 列</th><th>内容</th><th>行番号</th></tr>')
        for s in sorted(tag_conflicts, key=lambda x: x['line']):
            parts.append('<tr class="warning">'
                          f'<td>{_html_escape(s["jan"])}</td>'
                          f'<td>{_html_escape(s["name"])}</td>'
                          f'<td>{_render_card_preview(s)}</td>'
                          f'<td><code>{_html_escape(s["all_tags"])}</code></td>'
                          f'<td>{_html_escape(s["detail"])}</td>'
                          f'<td>{s["line"]}</td></tr>')
        parts.append('</table>')
    else:
        parts.append('<p class="empty">✅ タグの矛盾はありません。</p>')

    # 4. 商品名からの硬い一致（説明文は見ない）
    parts.append(f'<h2>商品名からの硬い一致 ({len(name_hits)}件)</h2>')
    if name_hits:
        parts.append('<p class="summary">商品名に、お悩みタグの表示名または rules.csv のキーワードがあるのに、'
                      'tags 列にそのタグが無い商品です。説明文は判定に使いません（検索用の言葉が誤検知になるため）。'
                      '本当にそのお悩み向けかは目視で判断してください。JAN・商品名・提案タグはそのままODSへコピペできます。'
                      '誤検知を今後出さないときだけ、任意列 exclude_tags にその key を書いて黙らせられます（主経路ではありません）。</p>')
        parts.append('<table><tr><th>JAN</th><th>商品名</th><th>カード相当（バッジ＋説明文）</th>'
                      '<th>提案タグ (key)</th><th>提案タグ (表示名)</th><th>ヒットした語</th><th>行番号</th></tr>')
        for s in sorted(name_hits, key=lambda x: (x['tag_id'], x['line'])):
            parts.append('<tr class="warning">'
                          f'<td>{_html_escape(s["jan"])}</td>'
                          f'<td>{_html_escape(s["name"])}</td>'
                          f'<td>{_render_card_preview(s)}</td>'
                          f'<td><code>{_html_escape(s["tag_id"])}</code></td>'
                          f'<td>{_html_escape(s["tag_name"])}</td>'
                          f'<td>{_html_escape(s["keyword"])}</td>'
                          f'<td>{s["line"]}</td></tr>')
        parts.append('</table>')
    else:
        parts.append('<p class="empty">✅ 商品名からの付け忘れ提案はありません。</p>')

    # 5. その他の確認推奨（exclude_tags の未登録タグ、JAN形式、類似商品名など）
    parts.append(f'<h2>その他の確認推奨 ({len(other_warnings)}件)</h2>')
    if other_warnings:
        parts.append('<table><tr><th>内容</th></tr>')
        for w in other_warnings:
            parts.append(f'<tr class="warning"><td>{_html_escape(w)}</td></tr>')
        parts.append('</table>')
    else:
        parts.append('<p class="empty">✅ その他の確認推奨はありません。</p>')

    parts.append('</body></html>')

    with open(BUILD_REPORT_HTML, 'w', encoding='utf-8') as f:
        f.write(''.join(parts))


def _review_item(line_num, row, name, desc, tags, cond_tag_ids, tag_display_names, **extra):
    item = {
        "line": line_num,
        "jan": (row.get('jan') or '#').strip(),
        "name": name,
        "desc": desc,
        "current_tags": [tag_display_names.get(t, t) for t in tags if t in cond_tag_ids],
        "all_tags": ' '.join(tags) if tags else '（空）',
    }
    item.update(extra)
    return item


def process_row_task(line_num, row, tag_to_cat_index, allowed_tags, name_hit_lookup, alias_rules,
                     tag_display_names, cond_tag_ids, animal_tag_ids, age_tag_ids):
    """1行分の重い処理を担当するワーカー関数"""
    row_errors = []
    row_warnings = []
    review = _empty_review()
    name = row.get('name', '').strip()

    # ヘッダー行そのものがデータとして混入している場合はスキップ
    if name.lower() == 'name' or name == '商品名':
        return None, [], [], _empty_review(), None, line_num

    if not name:
        return None, [f"行 {line_num}: 商品名(name)が空です。"], [], _empty_review(), None, line_num

    # 16列構成（必須列。17列目のexclude_tagsは任意列のためここには含めない）
    expected_keys = ['name', 'brand', 'tags', 'desc', 'size', 'jan', 'img', 'amz', 'rak', 'yah', 'a8', 'label', 'promo', 'amz_p', 'rak_p', 'yah_p']
    missing_keys = [k for k in expected_keys if k not in row or row[k] is None]
    if missing_keys:
        row_errors.append(f"行 {line_num}: 列が足りません。期待される列: {len(expected_keys)}、検出された列: {len(row)}。欠落: {', '.join(missing_keys)}")

    norm_name = normalize_text(name)
    desc = row.get('desc', '').strip()

    # ブランド情報の処理 (直接入力値をIDとしても使用)
    brand_name = row.get('brand', '').strip()
    row['brand'] = brand_name
    row['brand_id'] = normalize_text(brand_name)

    tags = row.get('tags', '').replace(',', ' ').split()
    tags = [normalize_text(t) for t in tags if t]
    for t in tags:
        if t not in allowed_tags:
            row_errors.append(f"行 {line_num}: 未登録タグ '{t}' (商品: {name[:20]}...)")

    # 除外タグの読み込み（tags.csv/rules.csv と同じ英語タグID表記。例: appetite）
    # 商品名の硬い一致提案だけを黙らせる任意列。説明文一致の提案は出さないので、主経路ではない。
    exclude_tags_raw = str(row.get('exclude_tags', '#')).strip()
    excluded_tag_ids = set()
    if exclude_tags_raw and exclude_tags_raw != '#':
        excluded_tag_ids = {normalize_text(t) for t in exclude_tags_raw.replace(',', ' ').split() if t}
        for t in excluded_tag_ids:
            if t not in allowed_tags:
                row_warnings.append(f"行 {line_num}: exclude_tags に未登録タグ '{t}' が指定されています (商品: {name[:20]}...)")

    tags_set = set(tags)
    name_short = name[:20]

    # 必須タグ欠け（animal / age）。exclude_tags では黙らせない。
    if animal_tag_ids and not (tags_set & animal_tag_ids):
        expected = '/'.join(sorted(animal_tag_ids))
        detail = f"{expected} がありません"
        row_warnings.append(f"行 {line_num}: 必須タグ欠け (animal): {detail} (商品: {name_short}...)")
        review["missing"].append(_review_item(
            line_num, row, name, desc, tags, cond_tag_ids, tag_display_names, detail=detail))
    if age_tag_ids and not (tags_set & age_tag_ids):
        expected = '/'.join(sorted(age_tag_ids))
        detail = f"年齢タグ（{expected}）がありません"
        row_warnings.append(f"行 {line_num}: 必須タグ欠け (age): {detail} (商品: {name_short}...)")
        review["missing"].append(_review_item(
            line_num, row, name, desc, tags, cond_tag_ids, tag_display_names, detail=detail))

    # 年齢は categories.csv 上 single。2つ以上は矛盾。
    age_hits = [t for t in tags if t in age_tag_ids]
    if len(age_hits) > 1:
        detail = f"年齢タグが複数あります: {' '.join(age_hits)}"
        row_warnings.append(f"行 {line_num}: タグ矛盾 (age): {detail} (商品: {name_short}...)")
        review["conflicts"].append(_review_item(
            line_num, row, name, desc, tags, cond_tag_ids, tag_display_names, detail=detail))

    # 商品名だけの硬い一致（説明文は見ない）。バッジ対象の cond のみ。
    hit_tag_ids = set()
    for kw, t_id in name_hit_lookup:
        if t_id in tags_set or t_id in excluded_tag_ids or t_id in hit_tag_ids:
            continue
        if kw and kw in norm_name:
            hit_tag_ids.add(t_id)
            row_warnings.append(
                f"行 {line_num}: 商品名に '{kw}' があるためタグ '{t_id}' の付与を検討してください (商品: {name_short}...)")
            review["name_hits"].append(_review_item(
                line_num, row, name, desc, tags, cond_tag_ids, tag_display_names,
                tag_id=t_id, tag_name=tag_display_names.get(t_id, t_id), keyword=kw))

    # 3. aliases.csv に基づく検索専用の読み・別名（タグには一切影響しない）
    #    ブランド表記が英語のままでも、カタカナ/ひらがなで検索できるようにするための裏フィールド。
    #    name/brand/desc のいずれかに keyword があれば、対応する reading を search_alias に足す。
    alias_check_text = normalize_text(f"{name} {brand_name} {desc}")
    alias_hits = []
    for keyword_norm, readings in alias_rules:
        if keyword_norm and keyword_norm in alias_check_text:
            alias_hits.extend(readings)
    row['search_alias'] = ' '.join(alias_hits)

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
    return row, row_errors, row_warnings, review, norm_name, line_num

def convert(exit_on_error=True):
    print(f"--- 変換処理を開始します ---")
    start_time = time.perf_counter()
    global validation_errors, validation_warnings
    validation_errors = []
    validation_warnings = []

    # --- 重複チェック用の変数をここで確実に初期化 ---
    seen_names = {}      # 商品名重複チェック用
    seen_jans = {}       # JANコード重複チェック用
    names_by_brand = {}  # 類似商品チェック用

    # 1. カテゴリマスタの読み込み（列名ベースで読み込むため、categories.csvの列順を変更しても壊れない）
    category_master = {}
    category_order = []
    for row in load_dict_rows(CAT_CSV):
        key = (row.get('key') or '').strip()
        if not key:
            continue
        jp = (row.get('jp') or '').strip()
        en = (row.get('en') or '').strip()
        m_type = (row.get('type') or '').strip()
        category_master[key] = {"jp": jp, "en": en, "multi": m_type == 'multi'}
        category_order.append(key)

    # 2. タグマスタの読み込み（列名ベース。tags.csvの列順を変更しても壊れない）
    tag_master = {}
    allowed_tags = set()
    tag_display_names = {} # レポート表示用：タグID -> 表示名（元の大文字小文字・括弧つき）
    for row in load_dict_rows(TAG_CSV):
        cat = (row.get('category') or '').strip()
        key = (row.get('key') or '').strip()
        name = (row.get('name') or '').strip()
        if not cat or not key:
            continue
        if cat not in category_master:
            validation_errors.append(f"tags.csv 行内: カテゴリ '{cat}' は categories.csv に定義されていません。")
        if cat not in tag_master: tag_master[cat] = {}
        norm_key = normalize_text(key)
        tag_master[cat][norm_key] = name
        allowed_tags.add(norm_key)
        tag_display_names[norm_key] = name

    # タグのカテゴリ所属マップを作成（ソート用）
    tag_to_cat_index = {}
    for idx, cat_key in enumerate(category_order):
        if cat_key in tag_master:
            for t_key in tag_master[cat_key]:
                tag_to_cat_index[t_key] = idx

    # バッジ表示対象（cond カテゴリ）のタグID集合。商品カードに実際に出るのはこれだけ（main.js側の実装に合わせる）
    cond_tag_ids = set(tag_master.get('cond', {}).keys())
    animal_tag_ids = set(tag_master.get('animal', {}).keys())
    age_tag_ids = set(tag_master.get('age', {}).keys())

    # ビルド時間をバージョンとして記録
    build_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    # 4. 自動ルール（キーワード）の読み込み（列名ベース。rules.csvの列順を変更しても壊れない）
    tag_keywords = {}
    for row in load_dict_rows(RULE_CSV):
        tag = (row.get('tag') or '').strip()
        kw_str = (row.get('keywords') or '').strip()
        if tag and kw_str:
            # カンマやスペースで分割して正規化
            kws = [normalize_text(k) for k in kw_str.replace(',', ' ').split() if k]
            if tag not in tag_keywords: tag_keywords[tag] = []
            tag_keywords[tag].extend(kws)
            allowed_tags.add(normalize_text(tag))

    # 商品名だけの硬い一致用：cond タグの表示名（英語カッコ除く）と rules.csv キーワード。
    # 2文字未満（例: 歯）は誤検知が多いので使わない。長い語を先に見る。
    name_hit_map = {}
    for t_id, display in tag_display_names.items():
        if t_id not in cond_tag_ids:
            continue
        stripped = _strip_tag_display_name(display)
        norm = normalize_text(stripped)
        if norm and len(norm) >= NAME_HIT_MIN_KW_LEN:
            name_hit_map[norm] = t_id
    for t_id, kws in tag_keywords.items():
        if t_id not in cond_tag_ids:
            continue
        for kw in kws:
            if kw and len(kw) >= NAME_HIT_MIN_KW_LEN:
                name_hit_map.setdefault(kw, t_id)
    name_hit_lookup = sorted(name_hit_map.items(), key=lambda x: len(x[0]), reverse=True)

    # 4-2. 検索専用の別名（aliases.csv）の読み込み。タグ体系とは無関係で、
    #      「name/brand/desc に keyword があれば reading を検索対象に足す」だけの表。
    #      例: ブランド表記が英語(TripeDry)でもカタカナ(トライプドライ)で検索できるようにする、
    #      説明文の漢字語(納豆菌)をかな(なっとうきん)でも検索できるようにする、など。
    alias_rules = []
    for row in load_dict_rows(ALIAS_CSV):
        keyword = (row.get('keyword') or '').strip()
        reading_str = (row.get('reading') or '').strip()
        if keyword and reading_str:
            readings = [r for r in reading_str.split() if r]
            alias_rules.append((normalize_text(keyword), readings))

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
                
                data = load_dict_rows(filepath)
                if data:
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
    all_missing_required = []
    all_tag_conflicts = []
    all_name_hits = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(
            process_row_task, ln, row, tag_to_cat_index, allowed_tags, name_hit_lookup, alias_rules,
            tag_display_names, cond_tag_ids, animal_tag_ids, age_tag_ids)
                   for ln, row in all_rows_input]
        
        for future in concurrent.futures.as_completed(futures):
            res_row, res_errs, res_warns, res_review, norm_name, ln = future.result()
            validation_errors.extend(res_errs)
            validation_warnings.extend(res_warns)
            all_missing_required.extend(res_review.get("missing") or [])
            all_tag_conflicts.extend(res_review.get("conflicts") or [])
            all_name_hits.extend(res_review.get("name_hits") or [])
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
    # 画像キャッシュ参照処理: images/{jan}.ext を手動で配置しておくと自動的に採用される
    # （画像の取得自体は auto_collect_all.py の役目。ここは純粋なCSV→JSON変換+検証のみを行う）
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
    os.makedirs(cache_dir, exist_ok=True)

    print("   - 画像キャッシュ参照処理...")
    for row in products:
        jan_val = str(row.get('jan', '#')).strip().replace(" ", "").replace("-", "")

        if jan_val != '#' and len(jan_val) == 13 and jan_val.isdigit():
            for ext in ["jpg", "jpeg", "png", "webp", "gif"]:
                test_path = os.path.join(cache_dir, f"{jan_val}.{ext}")
                if os.path.exists(test_path):
                    row['img'] = f"images/{jan_val}.{ext}"
                    break

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
            # 宛先メールは書き出さず、Formspree の公開フォームIDのみ渡す（main.js が送信先URLを組み立てる）
            f.write(f"const FORMSPREE_FORM_ID = {json.dumps(FORMSPREE_FORM_ID)};\n")
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

    # 全件（省略なし）の詳細をHTMLレポートに書き出す。products.csv/ODSには一切触れない
    write_build_report(validation_errors, validation_warnings, all_missing_required, all_tag_conflicts,
                        all_name_hits, len(products), exec_time, duration)
    print(f"   - {BUILD_REPORT_HTML} (確認推奨・エラーの全件レポート)")

    # 警告（確認を促すだけでデプロイは止めない）を表示
    if validation_warnings:
        print(f"\n{COLOR_CYAN}{COLOR_BOLD}💡 {len(validation_warnings)} 個の確認推奨項目があります:{COLOR_RESET}")
        for warn in validation_warnings[:10]:
            print(f"{COLOR_CYAN}   - {warn}{COLOR_RESET}")
        if len(validation_warnings) > 10: print(f"   ...他 {len(validation_warnings)-10} 件（全件は {BUILD_REPORT_HTML} を参照）")

    if validation_errors:
        print(f"\n{COLOR_RED}{COLOR_BOLD}⚠️  {len(validation_errors)} 個のデータ不備が見つかりました:{COLOR_RESET}")
        for err in validation_errors[:10]: # 最初の10件を表示
            print(f"{COLOR_RED}   - {err}{COLOR_RESET}")
        if len(validation_errors) > 10: print(f"   ...他 {len(validation_errors)-10} 件（全件は {BUILD_REPORT_HTML} を参照）")
        # 致命的なミス（商品名空など）がある場合にデプロイを止めるなら以下を有効にする
        if exit_on_error:
            sys.exit(1)
    else:
        print(f"{COLOR_GREEN}{COLOR_BOLD}✅ すべてのデータが正常に処理されました。{COLOR_RESET}")

if __name__ == '__main__':
    if "--watch" in sys.argv:
        print(f"{COLOR_BOLD}👀 監視モードを起動しました。CSVの変更を待機中... (Ctrl+C で終了){COLOR_RESET}")
        try:
            convert(exit_on_error=False) # 初回実行
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
            convert()
        except Exception as e:
            print(f"{COLOR_RED}{COLOR_BOLD}❌ 変換失敗: {e}{COLOR_RESET}")
            sys.exit(1)