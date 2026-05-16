const fs = require('fs').promises;
const fsSync = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');
const PUBLIC_DIR = path.join(__dirname, '..'); // data.jsの出力先をルートディレクトリに設定
const JS_PATH = path.join(PUBLIC_DIR, 'data.js');

// ひらがなをカタカナに変換し、小文字に統一する正規化関数（Node.js用）
function normalizeText(str) {
    if (!str) return "";
    return str
        .normalize('NFKC') // Unicode正規化 (全角英数・記号の半角化を含む)
        .replace(/[\u3041-\u3096]/g, m => String.fromCharCode(m.charCodeAt(0) + 0x60)) // ひらがな -> カタカナ
        .toLowerCase()
        .trim();
}

// タグのマスター定義（表示名とカテゴリを管理）
let TAG_MASTER = {};
let BRAND_MASTER = {};
// 許可タグリストを動的に更新する関数
let ALLOWED_TAGS = [];
let AUTO_TAG_RULES = []; // rules.csv から読み込むルール
function updateAllowedTags() {
    // 重複を除去して、すべてのカテゴリのタグID、自動タグ用のID、キーワードを許可リストにする
    ALLOWED_TAGS = [...new Set([
        ...new Set(Object.values(TAG_MASTER).flatMap(obj => Object.keys(obj))),
        ...AUTO_TAG_RULES.map(r => r.tag),
        ...AUTO_TAG_RULES.map(r => r.keyword)
    ])];
}
updateAllowedTags();

let validationErrors = [];

// 設定ファイルを読み込むための汎用関数
async function loadSettingsCSV(fileName, callback) {
    const filePath = path.join(DATA_DIR, fileName);
    if (fsSync.existsSync(filePath)) {
        const content = await fs.readFile(filePath, 'utf8');
        // parseCSVの第2引数に false を渡し、ヘッダーの解析をスキップして生の行データを得る
        const rows = parseCSV(content, false); 
        if (rows.length > 0) {
            callback(rows);
        }
    }
}

async function loadTagsFromCSV() {
    await loadSettingsCSV('tags.csv', (rows) => {
        const newMaster = {};
        rows.forEach(row => {
            // ヘッダー行や空行をスキップ
            if (row.length < 3 || /category|カテゴリ/i.test(row[0])) return;
            const [rawCategory, key, name] = row.map(s => s.trim());
            const category = rawCategory.toLowerCase(); // カテゴリ名を小文字に統一して判定ミスを防ぐ
            if (category && key && name) {
                if (!newMaster[category]) newMaster[category] = {};
                newMaster[category][key] = name;
             }
        });
        if (Object.keys(newMaster).length > 0) {
            // カテゴリ名とタグキーを正規化・並び替えて保存
            const categoryOrder = ['animal', 'age', 'cond'];
            const sortedMaster = {};

            // 1. 指定された順序（種類 -> 年齢 -> こだわり）に従って配置
            categoryOrder.forEach(cat => {
                if (newMaster[cat]) {
                    sortedMaster[cat] = {};
                    Object.keys(newMaster[cat]).sort().forEach(key => {
                        sortedMaster[cat][normalizeText(key)] = newMaster[cat][key];
                    });
                }
            });

            // 2. それ以外のカテゴリがあれば最後に追加
            Object.keys(newMaster).forEach(cat => {
                if (!categoryOrder.includes(cat)) {
                    sortedMaster[cat] = {};
                    Object.keys(newMaster[cat]).sort().forEach(key => {
                        sortedMaster[cat][normalizeText(key)] = newMaster[cat][key];
                    });
                }
            });

            TAG_MASTER = sortedMaster;
            updateAllowedTags();
        }
    });
}

// brands.csv があれば読み込む関数
async function loadBrandsFromCSV() {
    await loadSettingsCSV('brands.csv', (rows) => { 
        const newBrands = {};
        rows.forEach(row => {
            if (row.length < 2 || /key|キー/i.test(row[0])) return;
            const [key, name] = row.map(s => s.trim());
            if (key && name) {
                // キーを正規化して登録
                newBrands[normalizeText(key)] = name;
            }
        });
        if (Object.keys(newBrands).length > 0) {
            // キー（ブランドID）をアルファベット順に並び替えて保存
            const sortedBrands = {};
            Object.keys(newBrands).sort().forEach(key => {
                sortedBrands[key] = newBrands[key];
            });
            BRAND_MASTER = sortedBrands;
        }
    });
}

// rules.csv があれば読み込む関数
async function loadRulesFromCSV() {
    await loadSettingsCSV('rules.csv', (rows) => { 
        const newRules = [];
        rows.forEach(row => {
            if (row.length < 2 || /tag|タグ/i.test(row[0])) return;
            const tag = row[0].trim();
            const keywordsPart = row[1].trim();
            if (tag && keywordsPart) {
                // スペルミスや表記揺れを吸収するため、スペース、カンマ、読点で分割
                const keywords = keywordsPart.split(/[\s,，、/]+/).filter(k => k);
                keywords.forEach(keyword => {
                    newRules.push({ tag, keyword: normalizeText(keyword) });
                });
            }
        });
        AUTO_TAG_RULES = newRules;
        updateAllowedTags();
    });
}

// 簡易的なCSVパース関数（クォート対応）
function parseCSV(content, useHeaderMap = true) {
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
    // 解析終了時に引用符が閉じていない場合は異常
    if (inQuotes) {
        validationErrors.push('CSV解析エラー: 閉じられていない引用符 (") が検出されました。データが壊れている可能性があります。');
    }
    if (currentField || currentRow.length > 0) {
        currentRow.push(currentField);
        rows.push(currentRow);
    }

    if (!useHeaderMap) return rows;

    // 見出し行を検索（列名に name, brand, tags が含まれる行を探す）
    const headerIndex = rows.findIndex(r => 
        r.some(cell => /name/i.test(cell)) && r.some(cell => /brand/i.test(cell))
    );

    if (headerIndex === -1) {
        throw new Error(
            'スプレッドシートの「見出し行」が見つかりません。\n' +
            '👉 [解決策]: 1行目または2行目に "name" や "brand" という列名があるか確認してください。\n' +
            '   (大文字・小文字はどちらでも大丈夫です)'
        );
    }

    const headers = rows[headerIndex].map(h => h.trim().toLowerCase());
    
    return rows.slice(headerIndex + 1).map((rowValues, index) => {
        const obj = {};
        // --- 列数の不一致チェック ---
        if (rowValues.length !== headers.length) {
            validationErrors.push(`行 ${index + headerIndex + 2}: 列数が一致しません (期待: ${headers.length}, 実際: ${rowValues.length}) 商品: ${rowValues[0] || '不明'}`);
        }

        // ヘッダーの数とデータの数が合わない場合への対応
        headers.forEach((header, i) => {
            // データが存在しない列も安全に空文字として処理
            let val = (i < rowValues.length ? rowValues[i] : '').trim();

            // tags列はスペース区切りを配列に変換
            if (header === 'tags') {
                // 分割と同時にすべて正規化を適用
                const tags = [...new Set(
                    val.replace(/　/g, ' ')
                       .split(/\s+/)
                       .filter(t => t)
                       .map(t => normalizeText(t))
                )];

                // 商品カード内のタグの並び順も「種類 -> 年齢 -> お悩み・こだわり」に固定する
                tags.sort((a, b) => {
                    const getOrder = (tag) => {
                        // TAG_MASTERの定義順序に従って重みを付ける
                        if (TAG_MASTER.animal && TAG_MASTER.animal[tag]) return 1;
                        if (TAG_MASTER.age && TAG_MASTER.age[tag]) return 2;
                        if (TAG_MASTER.cond && TAG_MASTER.cond[tag]) return 3;
                        return 4;
                    };
                    return getOrder(a) - getOrder(b);
                });

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
                    const brandKey = normalizeText(val);
                    // ブランドIDを保持（検索用）
                    obj['brand_id'] = brandKey;
                    if (!BRAND_MASTER[brandKey]) {
                        validationErrors.push(`行 ${index + headerIndex + 2}: ブランド "${val}" は brands.csv に未登録です。`);
                    }
                }
                obj[header] = val;
            } else if (header.endsWith('_p')) {
                // --- 価格バリデーション（数値のみか） ---
                if (val && !/^\d+$/.test(val)) {
                    validationErrors.push(`行 ${index + headerIndex + 2}: 価格列 "${header}" に数値以外が含まれています: "${val}"`);
                }
                obj[header] = val;
            } else {
                obj[header] = val;
            }
        });

        // --- 必須項目チェック ---
        if (!obj.name) {
            validationErrors.push(`行 ${index + headerIndex + 2}: 商品名(name)が空です。`);
        }

        // --- ブランド名の自動検知（ブランド列が空の場合のみ、名前や説明文から推測） ---
        const rawCheckText = (obj.name || '') + (obj.desc || '');
        const checkText = normalizeText(rawCheckText); // 判定対象を正規化

        if (!obj.brand) {
            for (const [key, name] of Object.entries(BRAND_MASTER)) {
                // キー（正規化済み）または日本語名（正規化して比較）が含まれているか
                if (checkText.includes(normalizeText(key)) || checkText.includes(normalizeText(name))) {
                    // brands.csv で定義した表示名（name）を採用する
                    obj.brand_id = key;
                    obj.brand = name;
                    break;
                }
            }
        }

        // --- rules.csv に基づく自動タグ付け（タグ列、名前、説明文を横断チェック） ---
        AUTO_TAG_RULES.forEach(rule => {
            if (obj.tags.includes(rule.tag)) return; // すでにタグがあればスキップ

            // キーワードがタグ列に含まれているか、または名前/説明文に含まれているか
            // タグ列の中身も正規化して比較
            if (obj.tags.some(t => normalizeText(t) === rule.keyword) || checkText.includes(rule.keyword)) {
                obj.tags.push(rule.tag);
            }
        });

        return obj;
    });
}

async function run() {
    const isCI = process.env.GITHUB_ACTIONS === 'true';
    try {
        // フォルダが存在しない場合は作成（エラー防止）
        if (!fsSync.existsSync(DATA_DIR)) {
            await fs.mkdir(DATA_DIR, { recursive: true });
        }
        validationErrors = []; // 実行ごとにエラーリストをリセット

        const files = await fs.readdir(DATA_DIR);
        const csvFiles = files.filter(f => f.toLowerCase().includes('products') && f.endsWith('.csv'));
        const csvFileName = csvFiles[0] || 'products.csv';
        const hasMasterFile = files.some(f => f.endsWith('.ods'));

        // 出力先（ルートディレクトリ）の存在チェック
        if (!fsSync.existsSync(PUBLIC_DIR)) {
            throw new Error(
                `出力先のフォルダが見つかりません: ${PUBLIC_DIR}\n` +
                `👉 [解決策]: プロジェクトのルートディレクトリ（index.htmlがある場所）で実行してください。`
            );
        }

        const CSV_PATH = path.join(DATA_DIR, csvFileName);
        if (!fsSync.existsSync(CSV_PATH)) {
            console.log('\n--- 📁 フォルダ内の状態 ---');
            files.forEach(f => console.log(` - ${f}`));
            
            throw new Error(
                `${csvFileName} が見つかりません。\n` +
                (hasMasterFile 
                    ? '👉 [解決策]: マスターファイル(.ods)からCSV形式で「products.csv」を書き出し直してください。' 
                    : '👉 [解決策]: スプレッドシートを「products.csv」という名前で data フォルダに保存してください。')
            );
        }

        // 設定ファイルと商品データを読み込む
        await loadTagsFromCSV();
        await loadBrandsFromCSV();
        await loadRulesFromCSV();

        const stats = await fs.stat(CSV_PATH);
        const csvContent = await fs.readFile(CSV_PATH, 'utf8');
        const products = parseCSV(csvContent);

        // タグIDごとのキーワード（エイリアス）をまとめる
        const tagKeywordsMap = {};
        AUTO_TAG_RULES.forEach(r => {
            if (!tagKeywordsMap[r.tag]) tagKeywordsMap[r.tag] = [];
            tagKeywordsMap[r.tag].push(r.keyword);
        });
        
        const output = `const tagMaster = ${JSON.stringify(TAG_MASTER, null, 4)};\n` +
                       `const brandMaster = ${JSON.stringify(BRAND_MASTER, null, 4)};\n` +
                       `const tagKeywords = ${JSON.stringify(tagKeywordsMap, null, 4)};\n` +
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
        console.log('\n**************************************************');
        console.log('❌ エラーが発生しました');
        console.log('**************************************************');
        console.log(`内容: ${err.message}`);

        if (err.stack && err.stack.includes('ReferenceError')) {
            console.log('\n👉 [エンジニア用ヒント]: プログラム内の変数名が間違っている可能性があります。最近書き換えた箇所を確認してください。');
        }

        if (isCI) {
            console.log('\n🌐 [GitHub Actions ヒント]:');
            console.log('   - data/products.csv などのファイルが正しく push されているか確認してください。');
            console.log(`::error title=ビルド失敗::${err.message.replace(/\n/g, ' ')}`);
            process.exit(1);
        }

        console.log('**************************************************\n');
    }
}

// 外部（テスト）から関数を呼び出せるようにエクスポート
module.exports = { 
    parseCSV, 
    normalizeText,
    TAG_MASTER,
    BRAND_MASTER,
    AUTO_TAG_RULES,
    updateAllowedTags,
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