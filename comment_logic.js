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
 * 選択中のcond/animalタグから、店員経験談を最大MAX_STORE_COMMENTS件ランダムに選ぶ。
 * @param {{ cond?: string[], animal?: string }} [filters] 省略時はグローバルの `activeFilters` を使う
 * @returns {string[]}
 */
function pickStoreComments(filters) {
    const activeFiltersRef = filters || (typeof activeFilters !== 'undefined' ? activeFilters : {});
    if (!commentLookupMap) commentLookupMap = getCommentLookup();

    // タグごとに候補リストを分けて保持（同じタグから複数採用されて偏らないようにする）
    const condVals = Array.isArray(activeFiltersRef.cond) ? activeFiltersRef.cond : [];
    let tagBuckets = condVals
        .map(val => commentLookupMap[`cond:${val}`])
        .filter(list => list && list.length > 0);

    // condの選択がなければ animal（犬/猫）の経験談にフォールバック
    if (tagBuckets.length === 0) {
        const animalVal = activeFiltersRef.animal;
        if (animalVal && animalVal !== 'all') {
            const list = commentLookupMap[`animal:${animalVal}`];
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
 * タグ選択（cond/animal）由来の pickStoreComments() とは完全に独立しており、常に「追加の1件」としてのみ使う。
 * @param {string} searchVal 検索ボックスの入力文字列
 * @param {CommentRow[]} [commentsData] 省略時はグローバルの `comments` を使う
 * @returns {string[]}
 */
function pickKeywordComments(searchVal, commentsData) {
    const rows = commentsData || (typeof comments !== 'undefined' ? comments : []);
    const normalizedSearch = normalize(searchVal);
    if (!normalizedSearch) return [];

    const matched = rows.filter(row => row.category === 'keyword' && normalizedSearch.includes(normalize(row.key)));
    if (matched.length === 0) return [];

    return [matched[Math.floor(Math.random() * matched.length)].comment];
}

// Node/Jest環境でのテスト用エクスポート（ブラウザでは`module`が存在しないため、この分岐は実行されない）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { getCommentLookup, pickStoreComments, pickKeywordComments, STAFF_ICON_IMAGES, MAX_STORE_COMMENTS };
}
