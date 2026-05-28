// --- 状態管理 ---

// マスターデータが存在しない場合の空オブジェクト初期化（エラー防止）
if (typeof categoryMaster === 'undefined') window.categoryMaster = {};
if (typeof tagMaster === 'undefined') window.tagMaster = {};
if (typeof brandMaster === 'undefined') window.brandMaster = {};
if (typeof tagKeywords === 'undefined') window.tagKeywords = {};

let activeFilters = {}; 
let searchTrackTimer = null;
let tagLookupMap = {}; 
let favorites = JSON.parse(localStorage.getItem('pet925_favs') || '[]');
let showFavoritesOnly = false;
let searchWorker = null; 
let isWorkerReady = false;

let visibleCount = 30; 
const PAGE_SIZE = 30;  

function loadMore() {
    visibleCount += PAGE_SIZE;
    render(false);
}

function showResults() {
    document.body.classList.add('state-results');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    trackEvent('Navigation', 'show_results', 'click');
}

function backToSearch() {
    document.body.classList.remove('state-results');
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

const isMulti = (cat) => categoryMaster[cat] ? categoryMaster[cat].multi : false;
const getDefaultFilterValue = (cat) => isMulti(cat) ? [] : "all";

const getTagLookup = () => {
    const lookup = {};
    if (typeof tagMaster !== 'undefined') {
        Object.values(tagMaster).forEach(group => Object.assign(lookup, group));
    }
    return lookup;
};

function toggleFavorite(name) {
    const index = favorites.indexOf(name);
    if (index > -1) {
        favorites.splice(index, 1);
    } else {
        favorites.push(name);
    }
    localStorage.setItem('pet925_favs', JSON.stringify(favorites));
    render(false);
}

function clearAllFavorites() {
    if (favorites.length === 0) return;
    document.getElementById('fav-modal-overlay').style.display = 'flex';
}

function closeFavModal() {
    document.getElementById('fav-modal-overlay').style.display = 'none';
}

function executeClearAllFavorites() {
    favorites = [];
    localStorage.setItem('pet925_favs', JSON.stringify(favorites));
    trackEvent('Favorites', 'clear_all', 'all');
    closeFavModal();
    render(false);
}

function toggleFavFilter() {
    showFavoritesOnly = !showFavoritesOnly;
    document.getElementById('fav-filter-btn').classList.toggle('active', showFavoritesOnly);
    render(false);
}

function trackEvent(category, action, label) {
    if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
        console.log(`[Analytics] ${category} > ${action}: ${label}`);
    }
    if (window.gtag) {
        const eventName = (category + '_' + action).toLowerCase();
        gtag('event', eventName, {
            'item_label': label
        });
    }
}

function updateURL() {
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
    
    if (window.gtag) {
        if (searchVal) {
            gtag('event', 'search', {
                'search_term': searchVal
            });
        }
        gtag('event', 'page_view', {
            page_location: window.location.href,
            page_path: window.location.pathname + window.location.search,
            page_title: document.title
        });
    }
}

const normalize = (str) => {
    if (!str) return "";
    return String(str)
        .replace(/　/g, ' ')
        .normalize('NFKC')
        .replace(/[\u3041-\u3096]/g, m => String.fromCharCode(m.charCodeAt(0) + 0x60))
        .toLowerCase()
        .trim();
};

function initFilters() {
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

function toggleFilter(btn) {
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
    trackEvent('Filter', 'select_tag', `${category}:${value}`);
    updateURL();
    visibleCount = PAGE_SIZE;
    render(false);
}

function toggleGroupCollapse(header) {
    const group = header.parentElement;
    group.classList.toggle('collapsed');
}

function clearAllFilters() {
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
    updateURL();
    render(false);
}

function renderFilters() {
    if (typeof tagMaster === 'undefined') return;
    const navContainer = document.getElementById('filter-nav-container');
    navContainer.innerHTML = '';
    for (const [category, tags] of Object.entries(tagMaster)) {
        const groupDiv = document.createElement('div');
        groupDiv.className = 'filter-group';
        const catInfo = categoryMaster[category] || { jp: category, en: category.toUpperCase(), multi: false };
        if (catInfo.multi) groupDiv.setAttribute('data-multiselect', 'true');
        const isAllActive = catInfo.multi ? (!activeFilters[category] || activeFilters[category].length === 0) : (activeFilters[category] === 'all');
        const allActiveClass = isAllActive ? 'active' : '';
        let html = `<div class="group-header" onclick="toggleGroupCollapse(this)"><span class="group-label-jp">${catInfo.jp}</span><span class="group-label-en">${catInfo.en}</span>${catInfo.multi ? '<span class="multi-badge">複数選択可</span>' : ''}<span class="collapse-icon">▲</span></div><div class="filter-wrap-box" id="filter-${category}"><button class="filter-btn ${allActiveClass}" data-cat="${category}" data-val="all" onclick="toggleFilter(this)">すべて</button>`;
        for (const [tagKey, tagName] of Object.entries(tags)) {
            const isActive = Array.isArray(activeFilters[category]) ? activeFilters[category].includes(tagKey) : activeFilters[category] === tagKey;
            html += `<button class="filter-btn ${isActive ? 'active' : ''}" data-cat="${category}" data-val="${tagKey}" onclick="toggleFilter(this)">${tagName}</button>`;
        }
        html += `</div>`;
        groupDiv.innerHTML = html;
        navContainer.appendChild(groupDiv);
    }
}

function renderActiveChips() {
    const container = document.getElementById('active-chips-container');
    const searchVal = document.getElementById('search-input').value.trim();
    let chipsHtml = '';
    let hasActive = false;
    if (searchVal) {
        chipsHtml += `<div class="chip" onclick="document.getElementById('search-input').value='';render(true);">${searchVal} <span class="chip-close">×</span></div>`;
        hasActive = true;
    }
    const clearFavBtn = document.getElementById('clear-fav-btn');
    if (clearFavBtn) clearFavBtn.style.display = (favorites.length > 0) ? 'block' : 'none';
    const favBtn = document.getElementById('fav-filter-btn');
    if (favBtn) favBtn.innerHTML = `お気に入り <span style="color:#ff4757">❤</span> <span style="margin-left:5px; opacity:0.8; font-size:0.9em;">(${favorites.length})</span>`;
    for (const [cat, val] of Object.entries(activeFilters)) {
        const values = Array.isArray(val) ? val : (val !== 'all' ? [val] : []);
        values.forEach(v => {
            chipsHtml += `<div class="chip" onclick="removeSingleFilter('${cat}', '${v}')">${tagLookupMap[v] || v} <span class="chip-close">×</span></div>`;
            hasActive = true;
        });
    }
    container.innerHTML = hasActive ? `<span class="active-chips-label">ACTIVE:</span>` + chipsHtml + `<button class="clear-all" onclick="clearAllFilters()">CLEAR ALL ×</button>` : '';
}

function removeSingleFilter(cat, val) {
    const btn = document.querySelector(`.filter-btn[data-cat="${cat}"][data-val="${val}"]`);
    if (btn) toggleFilter(btn);
}

function getSearchUrl(shop, brand, name, fallbackUrl) {
    if (fallbackUrl && fallbackUrl !== '#') return fallbackUrl;
    const q = encodeURIComponent(`${brand} ${name}`);
    if (shop === 'amz') return `https://www.amazon.co.jp/s?k=${q}&s=price-asc-rank`;
    if (shop === 'rak') return `https://search.rakuten.co.jp/search/mall/${q}/?s=2`;
    if (shop === 'yah') return `https://shopping.yahoo.co.jp/search?p=${q}&ss_first=1&X=2`;
    return '#';
}

function render(isTyping = false) {
    if (!searchWorker || !isWorkerReady) return;
    if (isTyping) visibleCount = PAGE_SIZE;
    const searchWords = document.getElementById('search-input').value.replace(/　/g, ' ').trim().split(/\s+/).filter(w => w !== '').map(w => normalize(w));
    renderActiveChips();
    searchWorker.postMessage({ searchWords, activeFilters, visibleCount, showFavoritesOnly, favorites });
    clearTimeout(searchTrackTimer);
    searchTrackTimer = setTimeout(() => { if (isTyping) updateURL(); }, 800);
}

function handleWorkerResults(data) {
    if (data.type === 'READY') {
        isWorkerReady = true;
        if (document.getElementById('main-submit-btn')) document.getElementById('main-submit-btn').textContent = `準備完了（${data.total}件）`;
        render();
        return;
    }
    const { matchedItems, totalMatchCount, visibleCount: currentVisibleCount } = data;
    const list = document.getElementById('product-list');
    const loadMoreArea = document.getElementById('load-more-area');
    list.innerHTML = "";
    loadMoreArea.innerHTML = "";
    const defaultImg = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 380'%3E%3Crect width='400' height='380' fill='%23f4f4f4'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='sans-serif' font-size='14' fill='%23bbb'%3Eno image%3C/text%3E%3C/svg%3E";
    matchedItems.forEach(item => {
        const card = document.createElement('div');
        card.className = 'product-card';
        const isFav = favorites.includes(item.name);
        card.innerHTML = `<div class="img-container">${item.label ? `<div class="featured-badge">${item.label}</div>` : ''}<img src="${(!item.img || item.img === "#") ? defaultImg : item.img}" alt="${item.name}" onerror="this.src='${defaultImg}'" loading="lazy" decoding="async"><button class="card-fav-btn ${isFav ? 'active' : ''}" onclick="toggleFavorite('${item.name.replace(/'/g, "\\'")}')">${isFav ? '❤' : '♡'}</button></div><div class="card-content"><span class="brand-badge">${item.brand}</span><div class="${item.name.length > 45 ? 'product-name is-long' : 'product-name'}">${item.name}</div><p class="${(item.desc || "").length > 100 ? 'description is-long' : 'description'}">${item.desc || ""}</p><div class="tag-list">${item.tags.filter(t => tagMaster.cond && tagMaster.cond[t]).map(t => `<span class="tag">${tagLookupMap[t] || t}</span>`).join('')}</div><div class="shop-links"><a href="${getSearchUrl('amz', item.brand, item.name, item.amz)}" class="btn-shop btn-amz" target="_blank">Amazon</a><a href="${getSearchUrl('rak', item.brand, item.name, item.rak)}" class="btn-shop btn-rak" target="_blank">楽天</a><a href="${getSearchUrl('yah', item.brand, item.name, item.yah)}" class="btn-shop btn-yah" target="_blank">Yahoo!</a></div></div>`;
        list.appendChild(card);
    });
    const submitBtn = document.getElementById('main-submit-btn');
    if (submitBtn) submitBtn.textContent = `${totalMatchCount}件を表示`;
    if (totalMatchCount > currentVisibleCount) loadMoreArea.innerHTML = `<button class="btn-load-more" onclick="loadMore()">さらに表示 (${totalMatchCount - currentVisibleCount}件)</button>`;
    if (totalMatchCount === 0) list.innerHTML = `<div class="no-results">NO PRODUCTS FOUND<br>条件に合う商品が見つかりませんでした</div>`;
}

window.addEventListener('DOMContentLoaded', () => {
    if (typeof tagMaster === 'undefined') return;
    tagLookupMap = getTagLookup();
    console.log("%cSTOP!", "color: red; font-size: 40px; font-weight: bold;");
    const version = (typeof siteVersion !== 'undefined') ? siteVersion : Date.now();
    searchWorker = new Worker('search_worker.js?v=' + version);
    searchWorker.onmessage = (e) => handleWorkerResults(e.data);
    initFilters();
    renderFilters();
});