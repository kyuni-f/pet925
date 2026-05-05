const fs = require('fs').promises;
const fsSync = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');
const PUBLIC_DIR = path.join(__dirname, '..', 'public');
const JS_PATH = path.join(PUBLIC_DIR, 'data.js');

// タグのマスター定義（表示名とカテゴリを管理）
let TAG_MASTER = {};
let BRAND_MASTER = {};
// 許可タグリストを動的に更新する関数
let ALLOWED_TAGS = [];
let AUTO_TAG_RULES = []; // rules.csv から読み込むルール
function updateAllowedTags() {
    // TAG_MASTER内のキーと、AUTO_TAG_RULES内のキーワードをすべて「許可された言葉」とする
    ALLOWED_TAGS = [
        // 重複を除去してフラットな配列にする
        ...new Set(Object.values(TAG_MASTER).flatMap(obj => Object.keys(obj))),
        ...AUTO_TAG_RULES.map(r => r.keyword)
    ];
}
updateAllowedTags();

let validationErrors = [];

// tags.csv があれば読み込む関数
async function loadTagsFromCSV() {
    const tagsPath = path.join(DATA_DIR, 'tags.csv');
    if (fsSync.existsSync(tagsPath)) {
        let content = await fs.readFile(tagsPath, 'utf8');
        content = content.replace(/^\uFEFF/, ''); // BOMを削除
        const lines = content.split(/\r?\n/).filter(line => line.trim() !== '' && !/^\s*(category|カテゴリ)/i.test(line));
        const newMaster = {};
        
        lines.forEach(line => {
            const [category, key, name] = line.split(',').map(s => s.trim().replace(/^"|"$/g, ''));
            if (category && key && name) {
                if (!newMaster[category]) newMaster[category] = {};
                newMaster[category][key] = name;
            }
        });
        
        if (Object.keys(newMaster).length > 0) {
            TAG_MASTER = newMaster;
            updateAllowedTags();
        }
    }
}

// brands.csv があれば読み込む関数
async function loadBrandsFromCSV() {
    const brandsPath = path.join(DATA_DIR, 'brands.csv');
    if (fsSync.existsSync(brandsPath)) {
        let content = await fs.readFile(brandsPath, 'utf8');
        content = content.replace(/^\uFEFF/, ''); // BOMを削除
        const lines = content.split(/\r?\n/).filter(line => line.trim() !== '' && !/^\s*(key|キー)/i.test(line));
        const newBrands = {};
        
        lines.forEach(line => {
            const [key, name] = line.split(',').map(s => s.trim().replace(/^"|"$/g, ''));
            if (key && name) {
                newBrands[key.toLowerCase()] = name;
            }
        });
        
        if (Object.keys(newBrands).length > 0) {
            BRAND_MASTER = newBrands;
        }
    }
}

// rules.csv があれば読み込む関数
async function loadRulesFromCSV() {
    const rulesPath = path.join(DATA_DIR, 'rules.csv');
    if (fsSync.existsSync(rulesPath)) {
        let content = await fs.readFile(rulesPath, 'utf8');
        content = content.replace(/^\uFEFF/, ''); // BOMを削除
        const lines = content.split(/\r?\n/).filter(line => line.trim() !== '' && !/^\s*(tag|タグ)/i.test(line));
        const newRules = [];
        lines.forEach(line => {
            const [tag, keyword] = line.split(',').map(s => s.trim().replace(/^"|"$/g, ''));
            if (tag && keyword) {
                newRules.push({ tag, keyword });
            }
        });
        AUTO_TAG_RULES = newRules;
        updateAllowedTags();
    }
}

// 簡易的なCSVパース関数（クォート対応）
function parseCSV(content) {
    content = content.replace(/^\uFEFF/, ''); // BOMを削除

    const rows = [];
    let currentRow = [];
    let currentField = '';
    let inQuotes = false;

    // ステートマシン方式による堅牢なパース（セル内改行・エスケープ対応）
    for (let i = 0; i < content.length; i++) {
        const char = content[i];
        const nextChar = content[i + 1];

        if (inQuotes) {
            if (char === '"' && nextChar === '"') {
                currentField += '"'; // エスケープされた二重引用符
                i++;
            } else if (char === '"') {
                inQuotes = false;
            } else {
                currentField += char;
            }
        } else {
            if (char === '"') {
                inQuotes = true;
            } else if (char === ',') {
                currentRow.push(currentField);
                currentField = '';
            } else if (char === '\r' || char === '\n') {
                currentRow.push(currentField);
                if (currentRow.some(cell => cell.trim() !== '')) {
                    rows.push(currentRow);
                }
                currentRow = [];
                currentField = '';
                if (char === '\r' && nextChar === '\n') i++; // CRLF対応
            } else {
                currentField += char;
            }
        }
    }
    if (currentField || currentRow.length > 0) {
        currentRow.push(currentField);
        rows.push(currentRow);
    }

    // 見出し行を検索（列名に name, brand, tags が含まれる行を探す）
    const headerIndex = rows.findIndex(r => 
        r.some(cell => /name/i.test(cell)) && r.some(cell => /brand/i.test(cell))
    );

    if (headerIndex === -1) throw new Error('見出し行(name,brand...)が見つかりません。');

    const headers = rows[headerIndex].map(h => h.trim().toLowerCase());
    
    return rows.slice(headerIndex + 1).map((rowValues, index) => {
        const obj = {};
        // ヘッダーの数とデータの数が合わない場合への対応
        headers.forEach((header, i) => {
            // データが存在しない列も安全に空文字として処理
            let val = (i < rowValues.length ? rowValues[i] : '').trim();

            // tags列はスペース区切りを配列に変換
            if (header === 'tags') {
                // 全角スペースも半角に変換してから分割
                // 入力ミスを防ぐため小文字に統一
                const tags = val.replace(/　/g, ' ').toLowerCase().split(/\s+/).filter(t => t);
                // タグのバリデーション（チェック）
                tags.forEach(tag => {
                    if (!ALLOWED_TAGS.includes(tag)) {
                        validationErrors.push(`行 ${index + headerIndex + 2}: "${tag}" (商品: ${obj.name || '不明'})`);
                    }
                });
                obj[header] = tags;
            } else if (header === 'brand') {
                // ブランド名の検証（小文字で比較）
                if (val) {
                    const brandKey = val.trim().toLowerCase();
                    if (!BRAND_MASTER[brandKey]) {
                        validationErrors.push(`行 ${index + headerIndex + 2}: ブランド "${val}" は brands.csv に未登録です。`);
                    }
                }
                obj[header] = val;
            } else {
                obj[header] = val;
            }
        });

        // --- ブランド名の自動検知（ブランド列が空の場合のみ、名前や説明文から推測） ---
        const checkText = (obj.name || '') + (obj.desc || '');
        if (!obj.brand) {
            for (const [key, name] of Object.entries(BRAND_MASTER)) {
                // 英語キー（nutro）または日本語名（ニュートロ）が含まれているかチェック
                if (checkText.toLowerCase().includes(key) || checkText.includes(name)) {
                    // 見つかったブランドの「本来の表記（最初の文字を大文字にするなど）」を適用
                    // ここでは brands.csv の key を元に、元データがあればそれを尊重
                    obj.brand = key.charAt(0).toUpperCase() + key.slice(1);
                    break;
                }
            }
        }

        // --- rules.csv に基づく自動タグ付け（タグ列、名前、説明文を横断チェック） ---
        AUTO_TAG_RULES.forEach(rule => {
            if (obj.tags.includes(rule.tag)) return; // すでにタグがあればスキップ

            // キーワードがタグ列に含まれているか、または名前/説明文に含まれているか
            if (obj.tags.includes(rule.keyword) || checkText.includes(rule.keyword)) {
                obj.tags.push(rule.tag);
            }
        });

        return obj;
    });
}

async function run() {
    try {
        // フォルダが存在しない場合は作成（エラー防止）
        if (!fsSync.existsSync(DATA_DIR)) {
            await fs.mkdir(DATA_DIR, { recursive: true });
        }

        let filesInDir = [];
        try {
            filesInDir = await fs.readdir(DATA_DIR);
        } catch (e) {
            throw new Error(`data フォルダを読み込めません: ${DATA_DIR}`);
        }

        // productsが含まれるCSVファイルをすべて探し、重複があれば警告を出します
        const csvCandidates = filesInDir.filter(f => {
            const name = f.trim().toLowerCase();
            return name.includes('products') && name.endsWith('.csv') && !f.startsWith('.');
        });

        // マスターファイル（.ods/.xlsx）が存在するかチェック
        const hasMasterFile = filesInDir.some(f => {
            const name = f.toLowerCase();
            return (name.endsWith('.ods') || name.endsWith('.xlsx')) && name.includes('pet925');
        });

        if (csvCandidates.length > 1) {
            console.warn('⚠️  警告: CSVファイルが複数見つかりました。');
        }

        // 最も正しい名前（products.csv）を優先
        const csvFileName = csvCandidates.find(f => f === 'products.csv') || 
                            csvCandidates.find(f => f.trim() === 'products.csv') || 
                            csvCandidates[0];

        if (!csvFileName) {
            console.error(`❌ エラー: data フォルダ内に CSVファイルが見つかりません。`);
            if (hasMasterFile) console.log('💡 ヒント: マスターファイル(.ods)から CSV を書き出してください。');
            return;
        }

        // タグ定義を読み込む（ファイルがあれば上書き）
        await loadTagsFromCSV();

        // ブランド定義を読み込む
        await loadBrandsFromCSV();

        // 自動タグ付けルールを読み込む
        await loadRulesFromCSV();

        const CSV_PATH = path.join(DATA_DIR, csvFileName);
        validationErrors = []; // エラーリストをリセット

        if (!fsSync.existsSync(CSV_PATH)) {
            console.error(`❌ エラー: ${CSV_PATH} が見つかりません。`);
            const files = await fs.readdir(DATA_DIR);
            console.log('\n--- data フォルダにあるファイル一覧 ---');
            files.forEach(f => console.log(` - ${f}`));
            
            if (hasMasterFile) {
                console.log('\n💡 ヒント: 管理用のマスターファイル（.ods/.xlsx）は見つかりました。');
                console.log('   LibreOffice Calc 等で開き、[ファイル] > [保存コピーを保存] から');
                console.log('   "products.csv" を作成（エクスポート）して、このフォルダに置いてください。');
            } else {
                console.log('\n👉 スプレッドシートを "products.csv" という名前でこのフォルダに保存してください。');
            }
            process.exit(1);
        }

        const csvContent = await fs.readFile(CSV_PATH, 'utf8');
        const stats = await fs.stat(CSV_PATH);
        const products = parseCSV(csvContent);
        
        const now = new Date().toLocaleString();
        const output = `// Last Updated: ${now}\n` +
                       `const lastUpdated = "${now}";\n` +
                       `const tagMaster = ${JSON.stringify(TAG_MASTER, null, 4)};\n` +
                       `const brandMaster = ${JSON.stringify(BRAND_MASTER, null, 4)};\n` +
                       `const productData = ${JSON.stringify(products, null, 4)};\n`;

        await fs.writeFile(JS_PATH, output);
        const fileTime = stats.mtime.toLocaleString();
        console.log('--------------------------------------------------');
        console.log(`📄 変換完了: ${csvFileName}`);

        // Geminiへのコピペ用ガイドを表示
        console.log('\n📋 Gemini用 許可リスト (データ作成時に渡してください):');
        console.log('--- [TAGS] ---');
        const tagList = Object.entries(TAG_MASTER).flatMap(([cat, tags]) => 
            Object.entries(tags).map(([key, name]) => `${key} (${name})`)
        ).join(', ');
        console.log(tagList);

        console.log('\n--- [BRANDS] ---');
        // アルファベット順に並び替えて表示
        const brandList = Object.entries(BRAND_MASTER)
            .sort((a, b) => a[0].localeCompare(b[0]))
            .map(([k, v]) => `${k} (${v})`).join(', ');
        console.log(brandList + '\n');

        if (AUTO_TAG_RULES.length > 0) {
            console.log('🤖 自動判定キーワード（これらを含めると自動タグ付けされます）:');
            console.log(AUTO_TAG_RULES.map(r => `${r.keyword} → ${r.tag}`).join(', ') + '\n');
        }

        if (validationErrors.length > 0) {
            console.warn(`⚠️  タグに ${validationErrors.length} 個の入力ミスが見つかりました：`);
            validationErrors.forEach(err => console.log(`   - ${err}`));
            console.log('--------------------------------------------------');
            console.log(`💡 上記のミスをマスターファイル(.ods)で修正してください。`);
        } else {
            console.log(`✅ 完了: ${products.length} 件の商品をすべて正常に処理しました。`);
        }
        
        console.log(`⏰ 実行時刻: ${new Date().toLocaleString()}`);
        console.log(`文書の更新: ${fileTime} (ファイル: ${csvFileName})`);
        console.log('--------------------------------------------------');
    } catch (err) {
        console.error('❌ 変換エラー:', err.message);
    }
}

// 外部（テスト）から関数を呼び出せるようにエクスポート
module.exports = { 
    parseCSV, 
    TAG_MASTER, 
    getValidationErrors: () => validationErrors, 
    clearValidationErrors: () => { validationErrors = []; } 
};

// 監視モードの判定
if (require.main === module) {
    if (process.argv.includes('--watch')) {
        console.log('👀 監視モードを起動しました。CSVの変更を待機中...');
        run(); // 初回実行
        
        let debounceTimer;
        fsSync.watch(DATA_DIR, (eventType, filename) => {
            if (filename && filename.endsWith('.csv') && !filename.startsWith('.')) {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => run(), 200); // 連続保存対策のディレイ
            }
        });
    } else {
        run();
    }
}