// main.js（メインスレッド）と search_worker.js（Webワーカー）の両方から読み込まれる共通ロジック。
// 2箇所に同じ実装をコピーしていると修正漏れが起きるため、正規化ロジックのみここに集約する。

// 検索キーワードの正規化（全角半角・ひらがなカタカナの揺れを吸収）
const normalize = (str) => {
    if (!str) return "";
    return String(str)
        .replace(/　/g, ' ')
        .normalize('NFKC')
        .replace(/[\u3041-\u3096]/g, m => String.fromCharCode(m.charCodeAt(0) + 0x60))
        .toLowerCase()
        .trim();
};
