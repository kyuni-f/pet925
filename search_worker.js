// Worker起動時のURLからバージョンを取得
const urlParams = new URLSearchParams(self.location.search);
const version = urlParams.get('v') || Date.now();

// マスタデータを読み込む
importScripts('data_master.js?v=' + version); 

// 正規化ロジック (index.htmlと共通)
const normalize = (str) => {
    if (!str) return "";
    return String(str)
        .replace(/　/g, ' ')
        .normalize('NFKC')
        .replace(/[\u3041-\u3096]/g, m => String.fromCharCode(m.charCodeAt(0) + 0x60))
        .toLowerCase()
        .trim();
};

let allProducts = [];

const isMulti = (cat) => categoryMaster[cat] ? categoryMaster[cat].multi : false;

// 初期化：検索用文字列の事前生成
const tagLookupMap = {};
if (typeof tagMaster !== 'undefined') {
    Object.values(tagMaster).forEach(group => Object.assign(tagLookupMap, group));
}

// チャンク（分割ファイル）を処理する関数
function processChunk(data) {
    data.forEach(item => {
        // スコアリング用に各フィールドを個別に正規化して保持
        const nameNorm = normalize(item.name);
        const brandNorm = normalize(item.brand) + " " + normalize(item.brand_id || "");
        const descNorm = normalize(item.desc);
        const keywordsNorm = normalize(item._keywords || "");
        
        let tagsNorm = "";
        // セットを毎回作らず、検索時も配列のincludesを使用（タグ数が少なければこちらの方が速い）
        item.tags.forEach(t => {
            tagsNorm += normalize(t) + " ";
            if (tagLookupMap[t]) tagsNorm += normalize(tagLookupMap[t]) + " ";
            const aliases = (typeof tagKeywords !== 'undefined') ? tagKeywords[t] : null;
            if (aliases) aliases.forEach(a => tagsNorm += normalize(a) + " ");
        });

        // 検索用の重み付けフィールド
        item._weightedFields = {
            name: nameNorm,
            brand: brandNorm,
            tags: tagsNorm.trim(),
            keywords: keywordsNorm,
            desc: descNorm
        };

        // 高速フィルタリング用の全文テキスト（AND検索用）
        item._searchFullText = [
            nameNorm, 
            brandNorm, 
            tagsNorm, 
            descNorm, 
            normalize(item.size || ""), 
            keywordsNorm
        ].join(' ');

        item._originalIndex = allProducts.length; // 元の順序を保持
        allProducts.push(item);
    });
}

// JSONデータを非同期で取得
async function initWorker() {
    try {
        // ビルド時のバージョンを使用してJSONを取得
        const response = await fetch('product_data.json?v=' + version);
        const productData = await response.json();

        processChunk(productData);

        // 初期ロード完了を通知
        self.postMessage({ type: 'READY', total: allProducts.length });
    } catch (e) {
        console.error("Worker data load failed:", e);
    }
}

initWorker();

// メインスレッドからの検索リクエスト待機
self.onmessage = function(e) {
    if (e.data.type === 'LOAD_CHUNK') {
        // ここで追加ファイルを読み込むロジックを追加可能
        return;
    }

    const { searchWords, activeFilters, visibleCount, showFavoritesOnly, favorites } = e.data;
    const catsToCheck = Object.keys(tagMaster);
    
    let matchCount = 0;
    let allMatches = [];
    // 検索ごとに1回だけSetを作成（ループ内での生成を避ける）
    const favSet = new Set(favorites);

    for (const item of allProducts) {
        // お気に入りフィルターの適用
        if (showFavoritesOnly) {
            if (favSet.has(item.name)) {
                // お気に入りモード時は他のフィルタやスコアを無視してリストに追加
                item._tempScore = 0;
                allMatches.push(item);
            }
            continue; // お気に入り表示時は以下の標準検索ロジックをスキップ
        }

        // フィルタリング
        const matchFilters = catsToCheck.every(cat => {
            if (!tagMaster[cat]) return true;
            const filterVal = activeFilters[cat];
            const itemTags = item.tags;
            if (!isMulti(cat)) {
                return filterVal === 'all' || itemTags.includes(filterVal);
            }
            return filterVal.length === 0 || filterVal.every(t => itemTags.includes(t));
        });

        if (!matchFilters) continue;

        // キーワード検索
        const matchSearch = searchWords.every(word => item._searchFullText.includes(word));

        if (matchSearch) {
            let score = 0;
            // 検索ワードが含まれている場所によって加点
            searchWords.forEach(word => {
                if (item._weightedFields.name.includes(word)) score += 100;
                // 商品名と完全に一致する場合はさらにボーナス
                if (item._weightedFields.name === word) score += 500;
                if (item._weightedFields.brand.includes(word)) score += 50;
                if (item._weightedFields.tags.includes(word)) score += 20;
                if (item._weightedFields.keywords.includes(word)) score += 10;
                if (item._weightedFields.desc.includes(word)) score += 5;
            });
            item._tempScore = score;
            allMatches.push(item);
        }
    }

    matchCount = allMatches.length;

    // スコア順にソート（スコアが同じなら元のCSV順）
    if (searchWords.length > 0) {
        allMatches.sort((a, b) => {
            if (b._tempScore !== a._tempScore) return b._tempScore - a._tempScore;
            return a._originalIndex - b._originalIndex;
        });
    }

    // 必要な件数分だけ切り出す
    const matchedItems = allMatches.slice(0, visibleCount);

    // 結果をメインスレッドに返却
    self.postMessage({
        matchedItems: matchedItems,
        totalMatchCount: matchCount,
        visibleCount: visibleCount // フロントエンド側での管理用
    });
};