// --- 状態管理 ---

// マスターデータが存在しない場合の空オブジェクト初期化（エラー防止）
if (typeof categoryMaster === 'undefined') window.categoryMaster = {};
if (typeof tagMaster === 'undefined') window.tagMaster = {};
if (typeof tagKeywords === 'undefined') window.tagKeywords = {}; // tagKeywordsはrules.csvから生成

// --- アフィリエイト設定（ご自身のIDに書き換えてください） ---
// もしもアフィリエイトでAmazon, 楽天, Yahoo!ショッピングを一括管理
const AFFILIATE_CONFIG = {
    shopAid: {
        amazon: "",     // Amazonの提携が取り消されたため空に
        rakuten: "", // 楽天の提携が取り消されたため空に
        yahoo: ""    // Yahooの提携が取り消されたため空に
    },
    shopPid: {
        amazon: "",     // Amazonの提携が取り消されたため空に
        rakuten: "",  // 楽天の提携が取り消されたため空に
        yahoo: ""   // Yahooの提携が取り消されたため空に
    },
    shopPcid: {
        amazon: "",     // Amazonの提携が取り消されたため空に
        rakuten: "",   // 楽天の提携が取り消されたため空に
        yahoo: ""    // Yahooの提携が取り消されたため空に
    },
    shopPlid: {
        amazon: "",     // Amazonの提携が取り消されたため空に
        rakuten: "",   // 楽天の提携が取り消されたため空に
        yahoo: ""   // Yahooの提携が取り消されたため空に
    },
    // 楽天の画像サーバー(cabinet)で使用するショップ名
    // 多くのペットフードはここを "petline" や自身の提携ショップ名に設定することで画像を自動取得できます
    rakutenImageShop: "petline" 
};

let activeFilters = {}; 
let searchInputDebounceTimer = null; // 検索入力専用のデバウンスタイマー
let analyticsDebounceTimer = null; // アナリティクス送信用のデバウンスタイマー
let currentTotalMatchCount = 0; // 最新の検索結果件数を保持
let tagLookupMap = {}; 
let brandLookupMap = {}; // ブランドのkeyから表示名へのマップ
let favorites = JSON.parse(localStorage.getItem('pet925_favs') || '[]');
let visibleChipsInResults = new Set(); // 結果画面で表示し続けるチップのキー管理
let showFavoritesOnly = false;
let searchWorker = null; 
let isWorkerReady = false; 

// カテゴリの表示順序を定義（この順序で画面に並びます）
const CATEGORY_PRIORITY = ['animal', 'age', 'cond'];

let visibleCount = 20; 
const PAGE_SIZE = 20;  

function loadMore() { // 「さらに表示」ボタン：表示件数を増やして再描画
    visibleCount += PAGE_SIZE;
    trackEvent('Navigation', 'load_more', visibleCount);
    render(false);
}

function updateFavoriteButtonUI() { // お気に入りボタン（検索・結果両方）の件数バッジを更新
    const favCount = favorites.length;

    // 結果画面のお気に入りボタン
    const favFilterBtnResults = document.getElementById('fav-filter-btn');
    if (favFilterBtnResults) {
        favFilterBtnResults.classList.toggle('active', showFavoritesOnly);
        favFilterBtnResults.innerHTML = `お気に入り <span style="color:#ff4757">❤</span> <span style="margin-left:5px; opacity:0.8; font-size:0.9em;">(${favCount})</span>`;
    }
    // 検索画面のお気に入りボタン
    const favFilterBtnSearch = document.getElementById('fav-filter-btn-search-screen');
    if (favFilterBtnSearch) {
        favFilterBtnSearch.classList.toggle('active', showFavoritesOnly);
        favFilterBtnSearch.innerHTML = `お気に入り <span style="color:#ff4757">❤</span> <span style="margin-left:5px; opacity:0.8; font-size:0.9em;">(${favCount})</span>`;
    }
}

function showResults() { // 検索画面から結果画面へ切り替え
    document.body.classList.add('state-results');
    window.scrollTo({ top: 0, behavior: 'auto' });
    
    // 結果画面に入る瞬間のフィルター状態を「表示対象」として登録
    visibleChipsInResults.clear();
    for (const [cat, val] of Object.entries(activeFilters)) {
        const values = Array.isArray(val) ? val : (val !== 'all' ? [val] : []);
        values.forEach(v => visibleChipsInResults.add(`${cat}:${v}`));
    }
    const searchVal = document.getElementById('search-input').value.trim();
    if (searchVal) visibleChipsInResults.add(`q:${searchVal}`);

    trackEvent('Navigation', 'show_results', 'click');
    render(false);
}

function backToSearch() { // 結果画面から検索画面へ戻る
    document.body.classList.remove('state-results');
    window.scrollTo({ top: 0, behavior: 'auto' });
    // 検索画面に戻る際、お気に入りフィルターが有効であれば解除する
    if (showFavoritesOnly) {
        showFavoritesOnly = false;
    }
    // 検索入力欄が空でフィルターも適用されていない場合、URLからクエリパラメータをクリアする
    const searchVal = document.getElementById('search-input').value.trim();
    const hasActiveFilters = Object.values(activeFilters).some(val => (Array.isArray(val) && val.length > 0) || (typeof val === 'string' && val !== 'all'));
    if (!searchVal && !hasActiveFilters) {
        history.replaceState(null, '', window.location.pathname);
    }
    render(false);
}

const isMulti = (cat) => categoryMaster[cat] ? categoryMaster[cat].multi : false;
const getDefaultFilterValue = (cat) => isMulti(cat) ? [] : "all";

const getTagLookup = () => { // タグのIDから日本語名を取得するための逆引きマップを作成
    const lookup = {};
    if (typeof tagMaster !== 'undefined') {
        Object.values(tagMaster).forEach(group => {
            Object.assign(lookup, group);
        });
    }
    return lookup;
};

function toggleFavorite(id, nameForLog) { // お気に入りの登録・解除を切り替え（ID管理）
    const index = favorites.indexOf(id);
    if (index > -1) {
        favorites.splice(index, 1);
        trackEvent('Favorites', 'remove', nameForLog);
    } else {
        favorites.push(id);
        trackEvent('Favorites', 'add', nameForLog);
    }
    localStorage.setItem('pet925_favs', JSON.stringify(favorites));
    updateFavoriteButtonUI();
    render(false);
}

function clearAllFavorites() { // お気に入り一括解除の確認モーダルを表示
    if (favorites.length === 0) return;
    document.getElementById('fav-modal-overlay').style.display = 'flex';
}

function closeFavModal() { // お気に入り一括解除の確認モーダルを閉じる
    document.getElementById('fav-modal-overlay').style.display = 'none';
}

function executeClearAllFavorites() { // お気に入りを実際にすべて削除
    favorites.length = 0; // 配列の中身を空にする（再代入によるエラーを防止）
    localStorage.setItem('pet925_favs', JSON.stringify(favorites));
    updateFavoriteButtonUI();
    trackEvent('Favorites', 'clear_all', 'all');
    closeFavModal();
    // 全削除した後は「お気に入りフィルター」を解除して通常表示に戻す
    showFavoritesOnly = false;
    render(false);
}

function openImageModal(src, alt) { // 商品画像の拡大モーダルを開く
    const overlay = document.getElementById('image-modal-overlay');
    const img = document.getElementById('modal-expanded-img');
    img.src = src;
    img.alt = alt;
    overlay.style.display = 'flex';
    trackEvent('UI', 'image_expand', alt);
}

function closeImageModal() { // 商品画像の拡大モーダルを閉じる
    document.getElementById('image-modal-overlay').style.display = 'none';
}

function openLegalModal() {
    const overlay = document.getElementById('legal-modal-overlay');
    if (overlay) overlay.style.display = 'flex';
    trackEvent('UI', 'legal_open', 'click');
}

function closeLegalModal() { // 規約モーダルを閉じる
    const overlay = document.getElementById('legal-modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

function getMoshimoUrl(shopKey, targetUrl) {
    // IDを文字列として取得し、念のため余計な空白を削除（.trim()）
    const aid = String(AFFILIATE_CONFIG.shopAid[shopKey] || '').trim();
    const pid = String(AFFILIATE_CONFIG.shopPid[shopKey] || '').trim();
    const pcid = String(AFFILIATE_CONFIG.shopPcid[shopKey] || '').trim();
    const plid = String(AFFILIATE_CONFIG.shopPlid?.[shopKey] || '').trim();

    if (!aid || !pid || !pcid) return targetUrl; // IDが不足していればそのままのURLを返す
    
    let moshimoUrl = `https://af.moshimo.com/af/c/click?a_id=${aid}&p_id=${pid}&pc_id=${pcid}`;
    if (plid) moshimoUrl += `&pl_id=${plid}`;
    moshimoUrl += `&url=${encodeURIComponent(targetUrl)}`;
    
    return moshimoUrl;
}

function toggleFavFilter() { // 「お気に入り商品のみ表示」モードを切り替え
    showFavoritesOnly = !showFavoritesOnly;
    updateFavoriteButtonUI();
    // お気に入りボタンを押した時、もし検索画面にいたら結果画面へ切り替える
    if (showFavoritesOnly && !document.body.classList.contains('state-results')) {
        showResults();
    }
    render(false);
}

function toggleDescription(button) {
    const parentP = button.closest('p');
    const shortDesc = parentP.querySelector('.short-desc');
    const fullDesc = parentP.querySelector('.full-desc');
    if (shortDesc.style.display === 'none') {
        shortDesc.style.display = 'inline';
        fullDesc.style.display = 'none';
        button.textContent = '続きを読む';
    } else {
        shortDesc.style.display = 'none';
        fullDesc.style.display = 'inline';
        button.textContent = '閉じる';
    }
}

function trackEvent(category, action, label, extraParams = {}) { // Google Analytics (GA4) にイベントを送信
    if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
        console.log(`[Analytics] ${category} > ${action}: ${label}`);
    }
    if (window.gtag) {
        const eventName = (category + '_' + action).toLowerCase();
        gtag('event', eventName, Object.assign({
            'item_label': label
        }, extraParams));
    }
}

function updateURLAndGA4() { // URLパラメータの更新とページビューの計測
    const params = new URLSearchParams();
    const searchVal = document.getElementById('search-input').value.trim();
    if (searchVal) params.set('q', searchVal);

    for (const cat in activeFilters) {
        const val = activeFilters[cat];
        if (Array.isArray(val) && val.length > 0) {
            params.set(cat, val.join(','));
        } else if (typeof val === 'string' && val !== 'all') {
            params.set(cat, val);
        }
    }

    const newRelativePathQuery = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
    history.replaceState(null, '', newRelativePathQuery);
    
    // アナリティクス送信をデバウンス（入力停止から2秒後に送信）
    clearTimeout(analyticsDebounceTimer);
    analyticsDebounceTimer = setTimeout(() => {
        const currentSearchVal = document.getElementById('search-input').value.trim();
        if (currentSearchVal) {
            // 0件だった場合の記録（2秒待つことで、入力途中の送信を抑制しつつ、確定した0件を拾う）
            if (currentTotalMatchCount === 0 && !showFavoritesOnly) {
                const filterInfo = Object.entries(activeFilters)
                    .filter(([_, val]) => (Array.isArray(val) && val.length > 0) || (typeof val === 'string' && val !== 'all'))
                    .map(([cat, val]) => `${cat}:${val}`).join(', ');
                // search_term を明示的に渡すことで、GA4の検索レポートで集計しやすくします
                trackEvent('Search', 'no_results', currentSearchVal, { 
                    'search_term': currentSearchVal,
                    'active_filters_custom': filterInfo 
                });
            } else {
                trackEvent('Search', 'success', currentSearchVal, {
                    'search_term': currentSearchVal
                });
            }
        }

        if (window.gtag) {
            gtag('event', 'page_view', {
                page_location: window.location.href,
                page_path: window.location.pathname + window.location.search,
                page_title: document.title
            });
        }
    }, 2000); // 2秒に延長して、より確実に入力停止を待つ
}

const normalize = (str) => { // 検索キーワードの正規化（全角半角・ひらがなカタカナの揺れを吸収）
    if (!str) return "";
    return String(str)
        .replace(/　/g, ' ')
        .normalize('NFKC')
        .replace(/[\u3041-\u3096]/g, m => String.fromCharCode(m.charCodeAt(0) + 0x60))
        .toLowerCase()
        .trim();
};

function initFilters() { // URLのパラメータからフィルター状態を初期化
    if (typeof tagMaster === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    if (params.has('q')) {
        document.getElementById('search-input').value = params.get('q');
    }
    const cats = Object.keys(tagMaster);
    for (const cat of cats) {
        if (params.has(cat)) {
            const val = params.get(cat);
            activeFilters[cat] = isMulti(cat) ? val.split(',') : val;
        } else {
            activeFilters[cat] = getDefaultFilterValue(cat);
        }
    }
}

function toggleFilter(btn) { // フィルターボタンの選択・解除を切り替え
    const category = btn.getAttribute('data-cat');
    const value = btn.getAttribute('data-val');

    if (!isMulti(category)) {
        const isActive = btn.classList.contains('active');
        const allBtn = btn.parentElement.querySelector('[data-val="all"]');
        if (isActive && value !== 'all') {
            btn.classList.remove('active');
            activeFilters[category] = getDefaultFilterValue(category);
            allBtn.classList.add('active');
        } else {
            btn.parentElement.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeFilters[category] = value;
        }
    } else {
        if (value === 'all') {
            activeFilters[category] = [];
            btn.parentElement.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        } else {
            const allBtn = btn.parentElement.querySelector('[data-val="all"]');
            if (activeFilters[category].includes(value)) {
                activeFilters[category] = activeFilters[category].filter(v => v !== value);
                btn.classList.remove('active');
            } else {
                activeFilters[category].push(value);
                btn.classList.add('active');
            }
            if (activeFilters[category].length === 0) allBtn.classList.add('active');
            else allBtn.classList.remove('active');
        }
    }

    // 解除直後の金枠残存を確実に防ぐため、非同期でフォーカスを強制解除
    setTimeout(() => btn.blur(), 50);

    trackEvent('Filter', 'select_tag', `${category}:${value}`);
    visibleCount = PAGE_SIZE;
    render(false);
}

function handleSearchInput() { // 検索入力時のデバウンス処理（入力停止から800ms後に実行）
    clearTimeout(searchInputDebounceTimer);
    searchInputDebounceTimer = setTimeout(() => {
        render(true);
    }, 800);
}

// Enterキーが押された時の処理：キーボードを閉じ、即座に検索
function handleSearchKeydown(event) {
    if (event.key === 'Enter') {
        event.target.blur(); // フォーカスを外してキーボードを閉じる
        clearTimeout(searchInputDebounceTimer); // 待機中のタイマーをキャンセル
        render(true); // 即座に検索実行
    }
}

function toggleGroupCollapse(header) { // カテゴリグループの開閉切り替え
    const group = header.parentElement;
    group.classList.toggle('collapsed');
}

function clearAllFilters() {
    // クリックした「CLEAR ALL」ボタン自体のフォーカス枠を消す
    const activeEl = document.activeElement;
    if (activeEl && activeEl.tagName === 'BUTTON') {
        activeEl.blur();
    }
    for (const cat in activeFilters) {
        activeFilters[cat] = (typeof tagMaster !== 'undefined' && tagMaster[cat]) ? getDefaultFilterValue(cat) : "all";
    }
    document.getElementById('search-input').value = '';
    document.querySelectorAll('.filter-btn').forEach(btn => {
        if (btn.getAttribute('data-val') === 'all') btn.classList.add('active');
        else btn.classList.remove('active');
    });
    trackEvent('Filter', 'clear_all', 'all');
    visibleCount = PAGE_SIZE;
    render(false);
}

function renderFilters() { // フィルターボタン一覧を画面に描画
    if (typeof tagMaster === 'undefined') return;
    const navContainer = document.getElementById('filter-nav-container');
    navContainer.innerHTML = '';

    // 表示順序に基づいてカテゴリをソートしてレンダリング
    const sortedCategories = Object.keys(tagMaster).sort((a, b) => {
        return CATEGORY_PRIORITY.indexOf(a) - CATEGORY_PRIORITY.indexOf(b);
    });

    for (const category of sortedCategories) {
        const tags = tagMaster[category];
        const groupDiv = document.createElement('div');
        groupDiv.className = 'filter-group';
        const catInfo = categoryMaster[category] || { jp: category, en: category.toUpperCase(), multi: false };
        if (catInfo.multi) groupDiv.setAttribute('data-multiselect', 'true');
        const isAllActive = catInfo.multi ? (!activeFilters[category] || activeFilters[category].length === 0) : (activeFilters[category] === 'all');
        const allActiveClass = isAllActive ? 'active' : '';
        let html = `<div class="group-header" onclick="toggleGroupCollapse(this)"><span class="group-label-jp">${catInfo.jp}</span><span class="group-label-en">${catInfo.en}</span>${catInfo.multi ? '<span class="multi-badge">複数選択可</span>' : ''}<span class="collapse-icon">▲</span></div><div class="filter-wrap-box" id="filter-${category}"><button class="filter-btn ${allActiveClass}" data-cat="${category}" data-val="all" onclick="toggleFilter(this)"><span class="btn-jp">すべて</span></button>`;
        for (const [tagKey, tagName] of Object.entries(tags)) {
            const isActive = Array.isArray(activeFilters[category]) ? activeFilters[category].includes(tagKey) : activeFilters[category] === tagKey;
            const parts = tagName.match(/(.+)\s*\((.+)\)/);
            const labelHtml = parts 
                ? `<span class="btn-jp">${parts[1]}</span><span class="btn-en">${parts[2]}</span>`
                : `<span class="btn-jp">${tagName}</span>`;
            html += `<button class="filter-btn ${isActive ? 'active' : ''}" data-cat="${category}" data-val="${tagKey}" onclick="toggleFilter(this)">${labelHtml}</button>`;
        }
        html += `</div>`;
        groupDiv.innerHTML = html;
        navContainer.appendChild(groupDiv);
    }
}

function renderActiveChips() { // 結果画面の「現在選択中の条件（チップ）」を描画
    const container = document.getElementById('active-chips-container');
    const searchVal = document.getElementById('search-input').value.trim();
    container.innerHTML = '';
    let hasActive = false;

    // 結果画面での「一時調整チップ」を一つずつ描画
    visibleChipsInResults.forEach(chipKey => {
        const [cat, val] = chipKey.split(':');
        let isActive = false;
        let label = '';
        let onClickAction = null;

        if (cat === 'q') {
            isActive = (searchVal === val);
            label = val;
            onClickAction = () => { document.getElementById('search-input').value = isActive ? '' : val; render(true); };
        } else {
            const currentVal = activeFilters[cat];
            isActive = Array.isArray(currentVal) ? currentVal.includes(val) : currentVal === val;
            label = tagLookupMap[val] || val;
            onClickAction = () => removeSingleFilter(cat, val);
        }

        const chipEl = document.createElement('div');
        chipEl.className = `chip ${isActive ? '' : 'is-off'}`;
        chipEl.innerHTML = `${label} <span class="chip-close">×</span>`;
        chipEl.onclick = onClickAction;
        container.appendChild(chipEl);
        hasActive = true;
    });

    if (hasActive) {
        const clearBtn = document.createElement('button');
        clearBtn.className = 'clear-all';
        clearBtn.textContent = 'CLEAR ALL ×';
        clearBtn.onclick = clearAllFilters;
        container.appendChild(clearBtn);
    }

    // 表示・非表示の制御だけに専念させる
    const clearFavBtn = document.getElementById('clear-fav-btn');
    if (clearFavBtn) {
        clearFavBtn.style.display = (favorites.length > 0 && showFavoritesOnly) ? 'block' : 'none';
    }
}

function removeSingleFilter(cat, val) { // 特定のフィルターを解除
    const btn = document.querySelector(`.filter-btn[data-cat="${cat}"][data-val="${val}"]`);
    if (btn) toggleFilter(btn);
}

function getSearchUrl(shop, brand, name, fallbackUrl, jan) { // モールごとの検索・アフィリエイトURLを生成
    // JANコードが13桁の有効な数値なら、検索精度を最大化するために最優先で使用
    const searchVal = (jan && jan !== '#' && jan.length === 13) ? jan : `${brand} ${name}`;
    const q = encodeURIComponent(searchVal);

    // CSVにURLがあればそれを使用、なければ検索URLを生成
    let targetShopUrl = (fallbackUrl && fallbackUrl !== '#') ? fallbackUrl : '';

    if (shop === 'amz') {
        return `https://www.amazon.co.jp/s?k=${q}&s=price-asc-rank`; // アフィリエイトIDを削除
    }
    if (shop === 'rak') {
        if (!targetShopUrl) targetShopUrl = `https://search.rakuten.co.jp/search/mall/${q}/?s=2`;
        return getMoshimoUrl('rakuten', targetShopUrl);
    }
    if (shop === 'yah') {
        if (!targetShopUrl) targetShopUrl = `https://shopping.yahoo.co.jp/search?p=${q}&ss_first=1&X=2`;
        return getMoshimoUrl('yahoo', targetShopUrl);
    }
    return '#';
}

function getProductImageSrc(item, defaultImg) { // 商品画像のURLを決定（JANコードによる自動生成対応）
    // 1. CSVに画像URLが直接指定されている場合は最優先で使用
    if (item.img && item.img !== "#") return item.img;
    
    // 2. 画像がなく、JANコード(13桁)がある場合は楽天の画像サーバーURLを合成
    if (item.jan && item.jan !== "#" && item.jan.length === 13) {
        const shop = AFFILIATE_CONFIG.rakutenImageShop || "petline";
        return `https://thumbnail.image.rakuten.co.jp/@0_mall/${shop}/cabinet/jan/${item.jan}.jpg`;
    }
    
    // 3. いずれもない場合はデフォルトの「No Image」SVGを返す
    return defaultImg;
}

window.render = function(isTyping = false) { // 検索Workerへの依頼とUI更新の実行
    if (!searchWorker || !isWorkerReady) return;
    if (isTyping) visibleCount = PAGE_SIZE;
    const searchWords = document.getElementById('search-input').value.replace(/　/g, ' ').trim().split(/\s+/).filter(w => w !== '').map(w => normalize(w));
    renderActiveChips();
    updateFavoriteButtonUI();

    // Workerへの命令とURL更新を即座に実行（入力のデバウンスはhandleSearchInput側で制御済み）
    searchWorker.postMessage({ searchWords, activeFilters, visibleCount, showFavoritesOnly, favorites });
    updateURLAndGA4();
}

function handleWorkerResults(data) { // Web Workerからの検索結果を受け取って画面に表示
    if (data.type === 'PROGRESS') {
        const btn = document.getElementById('main-submit-btn');
        const percent = Math.round((data.current / data.total) * 100);
        if (btn) btn.textContent = `データを読み込み中... ${percent}%`;
        return;
    }
    if (data.type === 'READY') {
        isWorkerReady = true;
        const btn = document.getElementById('main-submit-btn');
        if (btn) btn.textContent = `全${data.total}件を表示`;
        render();
        return;
    }

    const { matchedItems, totalMatchCount, visibleCount: currentVisibleCount } = data;
    const list = document.getElementById('product-list');
    const loadMoreArea = document.getElementById('load-more-area');
    const submitBtn = document.getElementById('main-submit-btn');

    if (list) list.innerHTML = "";
    if (loadMoreArea) loadMoreArea.innerHTML = "";

    if (submitBtn) submitBtn.textContent = `${totalMatchCount}件を表示`;
    currentTotalMatchCount = totalMatchCount; // 送信用に件数を保存

    if (totalMatchCount === 0) {
        if (list) list.innerHTML = `<div class="no-results">NO PRODUCTS FOUND<br>条件に合う商品が見つかりませんでした</div>`;
        return;
    }

    const defaultImg = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 380'%3E%3Crect width='400' height='380' fill='%23ffffff'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='20' letter-spacing='2' fill='%23bbb'%3ENO IMAGE%3C/text%3E%3C/svg%3E";

    matchedItems.forEach(item => {
        const card = document.createElement('div');
        card.className = 'product-card';

        // brandLookupMap を使用して正式名称を取得
        const displayBrandName = brandLookupMap[item.brand_id] || item.brand;
        let productName = item.name;
        // 商品名の先頭にブランド名が入っている場合、重複を避けるために削る
        if (displayBrandName && productName.startsWith(displayBrandName)) {
            productName = productName.replace(displayBrandName, '').trim();
        }

        let descHtml = `<p class="${(item.desc || "").length > 100 ? 'description is-long' : 'description'}">${item.desc || ""}</p>`;
        const fullDesc = item.desc || "";
        const TRUNCATE_LENGTH = 150; // 説明文を切り詰める長さ

        if (fullDesc.length > TRUNCATE_LENGTH) {
            const displayDesc = fullDesc.substring(0, TRUNCATE_LENGTH) + '...';
            descHtml = `<p class="${(item.desc || "").length > 100 ? 'description is-long' : 'description'}">
                            <span class="short-desc">${displayDesc}</span>
                            <span class="full-desc" style="display:none;">${fullDesc}</span>
                            <button class="read-more-btn" onclick="toggleDescription(this)">続きを読む</button>
                        </p>`;
        }

        const imageSrc = getProductImageSrc(item, defaultImg);
        const isFav = favorites.includes(item.id);
        const favTooltip = isFav ? 'お気に入りから削除' : 'お気に入りに追加';
        card.innerHTML = `<div class="img-container">${item.label ? `<div class="featured-badge">${item.label}</div>` : ''}<img src="${imageSrc}" alt="${item.name}" onerror="this.src='${defaultImg}'" loading="lazy" decoding="async" onclick="openImageModal(this.src, '${item.name.replace(/'/g, "\\'")}')" style="cursor: zoom-in"></div><button class="card-fav-btn ${isFav ? 'active' : ''}" onclick="toggleFavorite('${item.id}', '${item.name.replace(/'/g, "\\'")}')" data-tooltip="${favTooltip}" aria-label="${favTooltip}">${isFav ? '❤' : '♡'}</button><div class="card-content"><span class="brand-badge">${displayBrandName}</span><div class="${productName.length > 45 ? 'product-name is-long' : 'product-name'}">${productName}</div>${descHtml}<div class="tag-list">${item.tags.filter(t => tagMaster.cond && tagMaster.cond[t]).map(t => `<span class="tag">${tagLookupMap[t] || t}</span>`).join('')}</div><div class="shop-links">` +
            `<a href="${getSearchUrl('amz', item.brand, item.name, item.amz, item.jan)}" class="btn-shop btn-amz" target="_blank" onclick="trackEvent('Search', 'click', 'Amazon:Search')">Amazonで検索</a>` +
            `<a href="${getSearchUrl('rak', item.brand, item.name, item.rak, item.jan)}" class="btn-shop btn-rak" target="_blank" onclick="trackEvent('Search', 'click', 'Rakuten:Search')">楽天市場で検索</a>` +
            `<a href="${getSearchUrl('yah', item.brand, item.name, item.yah, item.jan)}" class="btn-shop btn-yah" target="_blank" onclick="trackEvent('Search', 'click', 'Yahoo:Search')">Yahoo!ショッピングで検索</a>` +
            `${item.a8 && item.a8 !== '#' ? `<a href="${item.a8}" class="btn-shop btn-a8" target="_blank" onclick="trackEvent('Search', 'click', 'A8:Search')">公式/他で検索</a>` : ''}` +
            `</div></div>`;
        if (list) list.appendChild(card);
    });

    let footerHtml = '';
    if (totalMatchCount > currentVisibleCount) {
        footerHtml += `<button class="btn-load-more" onclick="loadMore()">さらに表示 (${totalMatchCount - currentVisibleCount}件)</button>`;
    }
    if (loadMoreArea) loadMoreArea.innerHTML = footerHtml;
}

function initializeApp() { // アプリ全体の初期化処理
    // --- 簡易的なドメインロック（疑似サイト対策） ---
    const authorizedDomains = ['kyuni-f.github.io', 'localhost', '127.0.0.1'];
    const currentHostname = window.location.hostname;
    
    if (currentHostname && !authorizedDomains.includes(currentHostname)) {
        console.warn("Unauthorized domain detected.");
        // 警告を表示する、または本家へリダイレクトさせる（必要に応じて有効化）
        // alert("このサイトは公式な pet925 ではありません。公式ページへ移動します。");
        // window.location.href = "https://kyuni-f.github.io/pet925/";
    }

    if (typeof tagMaster === 'undefined') return;
    tagLookupMap = getTagLookup();
    console.log("%cSTOP!", "color: red; font-size: 40px; font-weight: bold; -webkit-text-stroke: 1px black;");
    console.log("このサイトのコンテンツおよびデータの無断転載・複製を固く禁じます。");

    // brandLookupMapの初期化
    if (typeof brands !== 'undefined') {
        brands.forEach(b => {
            brandLookupMap[normalize(b.key)] = b.name; // keyも正規化して小文字で登録
        });
    }

    // --- スクロール監視：トップに戻るボタンの表示制御 ---
    const backToTopBtn = document.getElementById('floating-back-to-top');
    const clearFavBtn = document.getElementById('clear-fav-btn');

    if (backToTopBtn) {
        // クリックイベントは初期化時に一度だけ設定すればOK
        backToTopBtn.onclick = () => window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    if (clearFavBtn) {
        // お気に入り一括削除のイベントもここで一度だけ設定
        clearFavBtn.onclick = clearAllFavorites;
    }

    window.addEventListener('scroll', () => {
        if (!backToTopBtn) return;
        // 結果表示モードかつ、500px以上スクロールした場合に表示
        if (window.scrollY > 500 && document.body.classList.contains('state-results')) {
            backToTopBtn.classList.add('visible');
        } else {
            backToTopBtn.classList.remove('visible');
        }
    });
    
    const version = (typeof siteVersion !== 'undefined') ? siteVersion : Date.now();
    searchWorker = new Worker('search_worker.js?v=' + version);
    searchWorker.onmessage = (e) => handleWorkerResults(e.data);
    searchWorker.onerror = (err) => {
        console.error("Worker Error:", err);
        if (document.getElementById('main-submit-btn')) document.getElementById('main-submit-btn').textContent = "エラー: データの読み込みに失敗しました";
    };
    initFilters();
    renderFilters();
    updateFavoriteButtonUI(); // 初期表示時のお気に入りボタンの状態を更新
}

// すでに読み込みが終わっている場合は即実行、そうでなければイベントを待つ
if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}