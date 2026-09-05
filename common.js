// @ts-check
// main.js（メインスレッド）と search_worker.js（Webワーカー）の両方から読み込まれる共通ロジック。
// 2箇所に同じ実装をコピーしていると修正漏れが起きるため、正規化ロジックのみここに集約する。

/**
 * 検索キーワードの正規化（全角半角・ひらがなカタカナの揺れを吸収）。
 * 例: "　ﾈｺ" と "猫" は別物として比較されるが、"ネコ" と "ねこ" は同一視される。
 * @param {string} str 正規化前の文字列
 * @returns {string} 正規化後の文字列（NFKC正規化・カタカナ統一・小文字化・前後空白除去済み）
 */
const normalize = (str) => {
    if (!str) return "";
    return String(str)
        .replace(/　/g, ' ')
        .normalize('NFKC')
        .replace(/[\u3041-\u3096]/g, m => String.fromCharCode(m.charCodeAt(0) + 0x60))
        .toLowerCase()
        .trim();
};

/** 種類・年齢。開閉しても絞り込みの種類は変わらない */
const SHARED_FILTER_CATEGORIES = ['animal', 'age'];

/**
 * お悩み / ケア / お出かけのような「種類枠」かどうか。
 * animal / age 以外は種類枠（同時に1つだけ開く）。
 * @param {string} cat カテゴリキー
 * @returns {boolean}
 */
const isKindCategory = (cat) => !!cat && SHARED_FILTER_CATEGORIES.indexOf(cat) === -1;

/**
 * tagMaster にある種類枠のキー一覧。
 * @param {Record<string, Record<string, string>>} [tagMaster]
 * @returns {string[]}
 */
const getKindCategories = (tagMaster) => Object.keys(tagMaster || {}).filter(isKindCategory);

/**
 * デフォルトの種類枠。お悩み(cond)があればそれ、なければ種類枠の先頭。
 * @param {Record<string, Record<string, string>>} [tagMaster]
 * @returns {string}
 */
const getDefaultKindCategory = (tagMaster) => {
    const kinds = getKindCategories(tagMaster);
    if (kinds.indexOf('cond') !== -1) return 'cond';
    return kinds[0] || '';
};

/**
 * 種類枠の絞り込み。デフォルト枠では、どの種類枠のタグも無い商品をフードとして通す。
 * @param {string[]} itemTags 商品のタグ
 * @param {string} activeKind 開いている種類枠
 * @param {Record<string, Record<string, string>>} tagMaster
 * @returns {boolean}
 */
const itemMatchesKind = (itemTags, activeKind, tagMaster) => {
    if (!activeKind) return true;
    const tags = itemTags || [];
    const kindCats = getKindCategories(tagMaster);
    /**
     * @param {string} cat
     * @returns {boolean}
     */
    const hasTagInCat = (cat) => {
        const keys = tagMaster && tagMaster[cat] ? Object.keys(tagMaster[cat]) : [];
        return keys.some((t) => tags.indexOf(t) !== -1);
    };
    const hasActive = hasTagInCat(activeKind);
    if (activeKind === getDefaultKindCategory(tagMaster)) {
        return hasActive || !kindCats.some((c) => hasTagInCat(c));
    }
    return hasActive;
};

/**
 * フィルター枠の表示順。categories.csv の行順、未登録は末尾。
 * @param {Record<string, unknown>} [tagMaster]
 * @param {Record<string, unknown>} [categoryMaster]
 * @returns {string[]}
 */
const sortFilterCategories = (tagMaster, categoryMaster) => {
    const cats = Object.keys(tagMaster || {});
    const order = Object.keys(categoryMaster || {});
    return cats.slice().sort((a, b) => {
        const ia = order.indexOf(a);
        const ib = order.indexOf(b);
        return (ia === -1 ? 1000 : ia) - (ib === -1 ? 1000 : ib);
    });
};

// Node/Jest環境でのテスト用エクスポート（ブラウザでは`module`が存在しないため、この分岐は実行されない）
// @ts-ignore Node の module。ブラウザの型定義には無い（#78 と同じ）
if (typeof module !== 'undefined' && module.exports) {
    // @ts-ignore
    module.exports = {
        normalize,
        isKindCategory,
        getKindCategories,
        getDefaultKindCategory,
        itemMatchesKind,
        sortFilterCategories
    };
}
