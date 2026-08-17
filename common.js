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

// Node/Jest環境でのテスト用エクスポート（ブラウザでは`module`が存在しないため、この分岐は実行されない）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { normalize };
}
