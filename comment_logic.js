// @ts-check
// 「店員コメント」機能のロジックのみを集約したファイル。
// main.js（DOM操作・状態管理）から分離することで、Jestでのユニットテストを
// アプリ本体（initializeApp()等の副作用）を起動せずに実行できるようにしている。
// ブラウザでは common.js（normalize）の後、main.js より前に <script> で読み込む。

/**
 * @typedef {{ category: string, key: string, comment: string }} CommentRow
 * comments.csv（data_master.js の const comments）1行分の形式。
 * category は "animal" | "cond"（タグ選択に連動） | "keyword"（検索語に連動）。
 */

/**
 * comments.csv の行配列から、"category:key" -> [comment, ...] の逆引きマップを作る。
 * @param {CommentRow[]} [commentsData] 省略時はグローバルの `comments`（data_master.js由来）を使う
 * @returns {Record<string, string[]>}
 */
function getCommentLookup(commentsData) {
    const rows = commentsData || (typeof comments !== 'undefined' ? comments : []);
    /** @type {Record<string, string[]>} */
    const lookup = {};
    rows.forEach(row => {
        const mapKey = `${row.category}:${row.key}`;
        if (!lookup[mapKey]) lookup[mapKey] = [];
        lookup[mapKey].push(row.comment);
    });
    return lookup;
}

/** @type {Record<string, string[]> | null} 一度作った逆引きマップのキャッシュ（グローバルの`comments`が変わらない前提） */
let commentLookupMap = null;

// 店員コメントに添えるアイコン画像。表示のたびにこの中からランダムで1枚選ばれる
const STAFF_ICON_IMAGES = [
    'images/staff_icon_brown.png',
    'images/staff_icon_pink.png'
];

// 複数タグ選択時に繋げて表示する経験談の最大数（増やしすぎると読みにくくなるため2件までに制限）
const MAX_STORE_COMMENTS = 2;

/**
 * タグ表示名から検索照合用の語を取り出す。「涙やけ (TEAR)」→ 涙やけ / TEAR、「腎臓・尿路」→ 腎臓と尿路。
 * @param {string} displayName
 * @returns {string[]}
 */
function getTagDisplaySearchTerms(displayName) {
    const name = String(displayName || '');
    /** @type {string[]} */
    const terms = [];
    const add = (raw) => {
        const t = String(raw || '').trim();
        if (t) terms.push(t);
    };
    const stripped = name.replace(/\s*\([^)]*\)\s*/g, ' ').trim();
    add(stripped);
    stripped.split(/[・\/／、]/).forEach(add);
    const parens = name.match(/\(([^)]+)\)/g) || [];
    parens.forEach(p => add(p.replace(/[()]/g, '')));
    return terms;
}

/**
 * 表示名に無いが、タグ名そのものの別名。keyword 行があっても cond 解説へ結ぶ。
 * （避妊・アレルギーのような「自動タグ用の別話題」は含めない）
 * @param {string} extraNorm
 * @returns {boolean}
 */
function isTagNameAlias(extraNorm) {
    // @ts-ignore
    return extraNorm === normalize('グレインフリー');
}

/**
 * この cond タグを検索欄から当てるときに使う語。専用keyword（避妊など）は除く。
 * @param {string} tagKey
 * @param {string} displayName
 * @param {Record<string, string[]>} keywordsMap
 * @param {Set<string>} keywordKeys
 * @returns {string[]}
 */
function getCondSearchTerms(tagKey, displayName, keywordsMap, keywordKeys) {
    const strippedNorm = normalize(String(displayName || '').replace(/\s*\([^)]*\)\s*/g, ' '));
    const terms = getTagDisplaySearchTerms(displayName);
    const extras = Array.isArray(keywordsMap[tagKey]) ? keywordsMap[tagKey] : [];
    extras.forEach(extra => {
        const extraNorm = normalize(extra);
        // 「避妊」が diet の自動タグ語でも、keywordコメントがある話題はタグ解説に寄せない
        if (keywordKeys.has(extraNorm) && strippedNorm.indexOf(extraNorm) === -1 && !isTagNameAlias(extraNorm)) return;
        terms.push(extra);
    });
    return terms;
}

/**
 * 検索欄の文字から、紐付ける cond タグ ID を返す（ボタンを押していなくても可）。
 * 表示名と rules.csv 由来の別名（tagKeywords）を見る。専用keyword（避妊など）はタグに吸い寄せない。
 * @param {string} searchVal
 * @param {Record<string, Record<string, string>>} [tagMasterData]
 * @param {Record<string, string[]>} [tagKeywordsData]
 * @param {CommentRow[]} [commentsData]
 * @returns {string[]}
 */
function findCondKeysFromSearch(searchVal, tagMasterData, tagKeywordsData, commentsData) {
    // @ts-ignore
    const q = normalize(searchVal);
    if (!q) return [];

    const master = tagMasterData || (typeof tagMaster !== 'undefined' ? tagMaster : {});
    const condMap = master && master.cond ? master.cond : {};
    const keywordsMap = tagKeywordsData || (typeof tagKeywords !== 'undefined' ? tagKeywords : {});
    const rows = commentsData || (typeof comments !== 'undefined' ? comments : []);
    const keywordKeys = new Set(
        rows.filter(row => row.category === 'keyword').map(row => normalize(row.key)).filter(Boolean)
    );

    /** @type {string[]} */
    const found = [];
    Object.keys(condMap).forEach(tagKey => {
        const terms = getCondSearchTerms(tagKey, condMap[tagKey], keywordsMap, keywordKeys);
        const hit = terms.some(term => {
            const t = normalize(term);
            return t.length >= 2 && q.indexOf(t) !== -1;
        });
        if (hit) found.push(tagKey);
    });
    return found;
}

/**
 * 選択中のcond/animalタグから、店員経験談を最大MAX_STORE_COMMENTS件ランダムに選ぶ。
 * 検索欄がタグ名（涙やけ、穀物不使用など）を含むときは、そのcondコメントも候補に含める。
 * @param {{ cond?: string[], animal?: string }} [filters] 省略時はグローバルの `activeFilters` を使う
 * @param {string} [searchVal] 検索欄の入力。省略時は検索からのタグ紐付けなし
 * @param {Record<string, Record<string, string>>} [tagMasterData]
 * @param {Record<string, string[]>} [tagKeywordsData]
 * @param {CommentRow[]} [commentsData]
 * @returns {string[]}
 */
function pickStoreComments(filters, searchVal, tagMasterData, tagKeywordsData, commentsData) {
    /** @type {{ cond?: string[], animal?: string }} */
    const activeFiltersRef = filters || (typeof activeFilters !== 'undefined' ? activeFilters : {});
    if (!commentLookupMap) commentLookupMap = getCommentLookup();
    const lookupMap = commentLookupMap;

    // タグごとに候補リストを分けて保持（同じタグから複数採用されて偏らないようにする）
    const condVals = Array.isArray(activeFiltersRef.cond) ? activeFiltersRef.cond.slice() : [];
    findCondKeysFromSearch(searchVal, tagMasterData, tagKeywordsData, commentsData).forEach(key => {
        if (condVals.indexOf(key) === -1) condVals.push(key);
    });
    let tagBuckets = condVals
        .map(val => lookupMap[`cond:${val}`])
        .filter(list => list && list.length > 0);

    // condの選択がなければ animal（犬/猫）の経験談にフォールバック
    if (tagBuckets.length === 0) {
        const animalVal = activeFiltersRef.animal;
        if (animalVal && animalVal !== 'all') {
            const list = lookupMap[`animal:${animalVal}`];
            if (list) tagBuckets = [list];
        }
    }

    if (tagBuckets.length === 0) return [];

    // タグの選ばれた順をシャッフルし、各タグから1件ずつ、最大MAX_STORE_COMMENTS件を採用
    const shuffledBuckets = [...tagBuckets].sort(() => Math.random() - 0.5);
    return shuffledBuckets.slice(0, MAX_STORE_COMMENTS).map(list => {
        return list[Math.floor(Math.random() * list.length)];
    });
}

/**
 * comments.csv の category="keyword" 行から、検索ボックスの自由入力語に一致する経験談を最大1件だけ選ぶ。
 * タグ選択（cond/animal）由来の pickStoreComments() とは独立。検索で既に cond タグ解説へ紐づいた語（涙やけ等）は除外する。
 * @param {string} searchVal 検索ボックスの入力文字列
 * @param {CommentRow[]} [commentsData] 省略時はグローバルの `comments` を使う
 * @param {Record<string, Record<string, string>>} [tagMasterData]
 * @param {Record<string, string[]>} [tagKeywordsData]
 * @returns {string[]}
 */
function pickKeywordComments(searchVal, commentsData, tagMasterData, tagKeywordsData) {
    const rows = commentsData || (typeof comments !== 'undefined' ? comments : []);
    // @ts-ignore common.js のグローバル。module.exports があると型上は見えない
    const normalizedSearch = normalize(searchVal);
    if (!normalizedSearch) return [];

    const condKeys = findCondKeysFromSearch(searchVal, tagMasterData, tagKeywordsData, rows);
    const master = tagMasterData || (typeof tagMaster !== 'undefined' ? tagMaster : {});
    const condMap = master && master.cond ? master.cond : {};
    const keywordsMap = tagKeywordsData || (typeof tagKeywords !== 'undefined' ? tagKeywords : {});
    const keywordKeys = new Set(
        rows.filter(row => row.category === 'keyword').map(row => normalize(row.key)).filter(Boolean)
    );
    const covered = new Set();
    condKeys.forEach(tagKey => {
        getCondSearchTerms(tagKey, condMap[tagKey], keywordsMap, keywordKeys).forEach(term => {
            covered.add(normalize(term));
        });
    });

    const matched = rows.filter(row => {
        if (row.category !== 'keyword') return false;
        // @ts-ignore
        const keyNorm = normalize(row.key);
        if (!keyNorm || normalizedSearch.indexOf(keyNorm) === -1) return false;
        if (covered.has(keyNorm)) return false;
        return true;
    });
    if (matched.length === 0) return [];

    return [matched[Math.floor(Math.random() * matched.length)].comment];
}

/** 検索画面の吹き出しに並べる「よく検索されているワード」の最大数 */
const MAX_POPULAR_SEARCH_WORDS = 3;

/**
 * popular_searches.csv（data_master.js の const popular_searches）から、吹き出し用の語を最大 max 件ランダムに選ぶ。
 * 空行・重複は除く。語が max 件未満ならある分だけ返す。
 * @param {{ word?: string }[]} [rows] 省略時はグローバルの `popular_searches` を使う
 * @param {number} [max]
 * @returns {string[]}
 */
function pickPopularSearchWords(rows, max) {
    const limit = typeof max === 'number' ? max : MAX_POPULAR_SEARCH_WORDS;
    const source = rows || (typeof popular_searches !== 'undefined' ? popular_searches : []);
    /** @type {string[]} */
    const words = [];
    const seen = new Set();
    source.forEach(row => {
        const word = (row && row.word ? String(row.word) : '').trim();
        if (!word) return;
        // @ts-ignore common.js のグローバル
        const key = normalize(word);
        if (!key || seen.has(key)) return;
        seen.add(key);
        words.push(word);
    });
    if (words.length <= limit) return words;
    const shuffled = [...words].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, limit);
}

/**
 * 検索画面吹き出し用の一文を作る。語が無ければ空文字（呼び出し側で吹き出しを隠す）。
 * @param {string[]} words
 * @returns {string}
 */
function formatPopularSearchHint(words) {
    if (!words || words.length === 0) return '';
    return `よく検索されているワードは${words.join('、')}です`;
}

// Node/Jest環境でのテスト用エクスポート（ブラウザでは`module`が存在しないため、この分岐は実行されない）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getCommentLookup,
        pickStoreComments,
        pickKeywordComments,
        findCondKeysFromSearch,
        getTagDisplaySearchTerms,
        pickPopularSearchWords,
        formatPopularSearchHint,
        STAFF_ICON_IMAGES,
        MAX_STORE_COMMENTS,
        MAX_POPULAR_SEARCH_WORDS
    };
}
