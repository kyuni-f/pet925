// マスタデータを読み込む
importScripts('data_master.js'); 

// 正規化ロジック (index.htmlと共通)
const normalize = (str) => {
    if (!str) return "";
    return str
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
        const brandJP = (typeof brandMaster !== 'undefined' && item.brand_id) ? brandMaster[item.brand_id] : "";
        const searchParts = [
            normalize(item.name),
            normalize(item.brand),
            normalize(item.brand_id || ""),
            normalize(brandJP || ""),
            normalize(item.desc),
            normalize(item.size || "")
        ];
        item._tagSet = new Set(item.tags);
        item._tagSet.forEach(t => {
            searchParts.push(normalize(t));
            if (tagLookupMap[t]) searchParts.push(normalize(tagLookupMap[t]));
            const aliases = (typeof tagKeywords !== 'undefined') ? tagKeywords[t] : null;
            if (aliases) aliases.forEach(a => searchParts.push(normalize(a)));
        });
        item._searchFullText = searchParts.filter(part => part !== "").join(' ');
        allProducts.push(item);
    });
}

// JSONデータを非同期で取得
async function initWorker() {
    try {
        const response = await fetch('product_data.json');
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

    const { searchWords, activeFilters, visibleCount } = e.data;
    const catsToCheck = Object.keys(tagMaster);
    
    let matchCount = 0;
    const matchedItems = [];

    for (const item of allProducts) {
        // フィルタリング
        const matchFilters = catsToCheck.every(cat => {
            if (!tagMaster[cat]) return true;
            const filterVal = activeFilters[cat];
            const itemTags = item._tagSet;
            if (!isMulti(cat)) {
                return filterVal === 'all' || itemTags.has(filterVal);
            }
            return filterVal.length === 0 || filterVal.every(t => itemTags.has(t));
        });

        if (!matchFilters) continue;

        // キーワード検索
        const matchSearch = searchWords.every(word => item._searchFullText.includes(word));

        if (matchSearch) {
            matchCount++;
            // 描画に必要な分だけ（visibleCountまで）を返すことで通信量を削減
            if (matchCount <= visibleCount) {
                matchedItems.push(item);
            }
        }
    }

    // 結果をメインスレッドに返却
    self.postMessage({
        matchedItems: matchedItems,
        totalMatchCount: matchCount,
        visibleCount: visibleCount
    });
};