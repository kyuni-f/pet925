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
let db = null;
const DB_NAME = "Pet925DB";
const STORE_NAME = "products";

// IndexedDBの初期化
function initDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, parseInt(version));
        request.onupgradeneeded = (e) => {
            const db = e.target.result;
            if (db.objectStoreNames.contains(STORE_NAME)) {
                db.deleteObjectStore(STORE_NAME);
            }
            // 検索用の高速化設定：JANコードでも検索できるようにインデックスを作成
            const store = db.createObjectStore(STORE_NAME, { keyPath: "_originalIndex" });
            store.createIndex("jan", "jan", { unique: false });
        };
        request.onsuccess = (e) => {
            db = e.target.result;
            resolve(db);
        };
        request.onerror = (e) => reject(e);
    });
}

// データベースから全件取得（メモリ展開を最小限に）
function getAllFromDB() {
    return new Promise((resolve) => {
        const transaction = db.transaction([STORE_NAME], "readonly");
        const store = transaction.objectStore(STORE_NAME);
        const request = store.getAll();
        request.onsuccess = (e) => resolve(e.target.result);
    });
}

// データを保存
async function saveToDB(products) {
    const transaction = db.transaction([STORE_NAME], "readwrite");
    const store = transaction.objectStore(STORE_NAME);
    products.forEach(p => store.put(p));
    return new Promise((resolve) => {
        transaction.oncomplete = () => resolve();
    });
}

const isMulti = (cat) => categoryMaster[cat] ? categoryMaster[cat].multi : false;

// 初期化：検索用文字列の事前生成
// マスタデータの逆引きマップ（タグ名、ブランド名）
const tagLookupMap = {};
if (typeof tagMaster !== 'undefined') {
    Object.values(tagMaster).forEach(group => Object.assign(tagLookupMap, group));
}

const brandLookupMap = {};
if (typeof brands !== 'undefined') {
    brands.forEach(b => {
        brandLookupMap[normalize(b.key)] = b.name; // keyも正規化して小文字で登録
    });
}

// チャンク（分割ファイル）を処理する関数
function processChunk(data) {
    data.forEach(item => {
        // スコアリング用に各フィールドを個別に正規化して保持
        const nameNorm = normalize(item.name);
        const brandDisplayName = brandLookupMap[item.brand_id] || "";
        const brandNorm = normalize(item.brand) + " " + normalize(item.brand_id || "") + " " + normalize(brandDisplayName);
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
        await initDB();
        
        // すでにデータがあるか確認
        const existingData = await getAllFromDB();
        if (existingData.length > 0) {
            console.log("Worker: Loaded from IndexedDB");
            allProducts = existingData;
            self.postMessage({ type: 'READY', total: allProducts.length });
            return;
        }

        // データがなければダウンロードして保存
        const metaRes = await fetch(`product_data.json?v=${version}`);
        const meta = await metaRes.json();

        const chunkPromises = [];
        for (let i = 0; i < meta.chunks; i++) {
            chunkPromises.push(
                fetch(`product_data_${i}.json?v=${version}`).then(res => res.json())
            );
        }

        const allChunksData = await Promise.all(chunkPromises);
        
        // 取得したデータを順番どおりに処理（processChunkを使用して高品質なインデックスを作成）
        allChunksData.forEach((chunkData) => {
            processChunk(chunkData);
            // allProducts.length を使うことで正しい進捗をメインスレッドに通知
            self.postMessage({ type: 'PROGRESS', current: allProducts.length, total: meta.total });
        });

        // 加工済みの全データをIndexedDBに保存
        await saveToDB(allProducts);

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
    const favSet = new Set(favorites || []); // ループの外で一度だけ作成
    
    // お気に入りが空で、かつお気に入りフィルターがONの場合は即座に空の結果を返す
    if (showFavoritesOnly && favSet.size === 0) {
        self.postMessage({ matchedItems: [], totalMatchCount: 0, visibleCount: visibleCount });
        return;
    }

    let matchCount = 0;
    let allMatches = [];

    for (const item of allProducts) {
        // お気に入りフィルターの適用
        if (showFavoritesOnly) {
            if (favSet.has(item.id)) {
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
        // 全文検索の高速化：indexOfはincludesよりわずかに速い場合があります
        const fullText = item._searchFullText;
        const matchSearch = searchWords.every(word => fullText.indexOf(word) !== -1);

        if (matchSearch) {
            let score = 0;
            const w = item._weightedFields;
            // 10万件ループ内では関数の呼び出し回数を減らすため、for文を使用
            for (let j = 0; j < searchWords.length; j++) {
                const word = searchWords[j];
                if (w.name.indexOf(word) !== -1) score += 100;
                if (w.name === word) score += 500;
                if (w.brand.indexOf(word) !== -1) score += 50;
                if (w.tags.indexOf(word) !== -1) score += 20;
                if (w.keywords.indexOf(word) !== -1) score += 40;
                if (w.desc.indexOf(word) !== -1) score += 5;
            }
            item._tempScore = score;
            allMatches.push(item);
        }
    }

    matchCount = allMatches.length;

    // スコア順にソート（スコアが同じなら元のCSV順）
    // お気に入りモードや検索ワードがない場合も、元の順序を維持するためにソートを通す
    if (searchWords.length > 0 || showFavoritesOnly) {
        allMatches.sort((a, b) => {
            if ((b._tempScore || 0) !== (a._tempScore || 0)) return b._tempScore - a._tempScore;
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