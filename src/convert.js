const fs = require('fs').promises;
const fsSync = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');
const PUBLIC_DIR = path.join(__dirname, '..', 'public');
const JS_PATH = path.join(PUBLIC_DIR, 'data.js');

// タグのマスター定義（表示名とカテゴリを管理）
const TAG_MASTER = {
    animal: {
        dog: '犬 (DOG)',
        cat: '猫 (CAT)'
    },
    age: {
        all_ages: '全年齢用 (ALL AGES)',
        puppy: '子犬・子猫 (PUPPY)',
        adult: '成犬・成猫 (ADULT)',
        senior: 'シニア (SENIOR)'
    },
    pref: {
        dry: 'ドライ (DRY)',
        wet: 'ウェット (WET)',
        freeze_dried: 'フリーズドライ (FD)',
        lamb: 'ラム肉 (LAMB)',
        fish: '魚 (FISH)',
        gf: '穀物不使用 (GF)'
    },
    cond: {
        tear: '涙やけ (TEAR)',
        diet: '体重管理 (WEIGHT)',
        kidney: '腎臓・尿路 (KIDNEY)',
        skin: '皮膚ケア (SKIN)',
        joint: '関節ケア (JOINT)',
        tooth: '歯の健康 (TOOTH)',
        appetite: '食いつき (APPETITE)'
    }
};

// 魚の種類として認めるタグ（これらを入れると自動的に「魚」フィルタに反映されます）
const FISH_TAG_ALIASES = ['salmon', 'tuna', 'bonito', 'mackerel', 'whitefish', 'cod', 'sardine'];

// バリデーション用にキーだけの配列を作成
const ALLOWED_TAGS = [...Object.values(TAG_MASTER).flatMap(obj => Object.keys(obj)), ...FISH_TAG_ALIASES];

let validationErrors = [];

// 簡易的なCSVパース関数（クォート対応）
function parseCSV(content) {
    // 改行コード（CRLF/LF）に対応し、空行を除外
    const lines = content.split(/\r?\n/).filter(line => line.trim() !== '');
    
    // 「name,brand」で始まる行（見出し行）を探す
    // より確実に、カンマの数なども考慮した正規表現で探すように強化
    // 見出し行をより柔軟に探す（前後の空白を許容）
    const headerIndex = lines.findIndex(l => /^\s*(?:"?name"?,"?brand"?,"?tags"?)/i.test(l));
    if (headerIndex === -1) throw new Error('見出し行(name,brand...)が見つかりません。');

    // 許可リストが混入していないか簡易チェック
    if (lines.some(l => /^(dog|cat)/i.test(l.trim()))) {
        console.log('💡 ヒント: CSV内に許可リストが混入している可能性がありますが、自動でデータ行のみを抽出します。');
    }

    // 引用符内のカンマを無視してヘッダーを分割
    const headers = lines[headerIndex].split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/)
        .map(h => h.trim().replace(/^"|"$/g, ''));
    
    return lines.slice(headerIndex + 1).map((line, index) => {
        // データ行も同様のルールで分割。空の列も正確に配列に入れる。
        const rawValues = line.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/);

        const obj = {};
        headers.forEach((header, i) => {
            // データが存在しない列も安全に処理（空文字をセット）
            let val = (rawValues[i] !== undefined ? rawValues[i] : '').replace(/^\s+|\s+$/g, '');
            // クォートで囲まれている場合は除去
            val = val.replace(/^"|"$/g, '').trim();

            // tags列はスペース区切りを配列に変換
            if (header === 'tags') {
                // 全角スペースも半角に変換してから分割
                const tags = val.replace(/　/g, ' ').split(/\s+/).filter(t => t);
                // タグのバリデーション（チェック）
                tags.forEach(tag => {
                    if (!ALLOWED_TAGS.includes(tag)) {
                        validationErrors.push(`行 ${index + headerIndex + 2}: "${tag}" (商品: ${obj.name || '不明'})`);
                    }
                });

                // 魚種タグが含まれている場合、フィルタリング用に 'fish' を自動付与
                if (tags.some(t => FISH_TAG_ALIASES.includes(t)) && !tags.includes('fish')) {
                    tags.push('fish');
                }
                obj[header] = tags;
            } else {
                obj[header] = val;
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
        
        const output = `// Last Updated: ${new Date().toLocaleString()}\n` +
                       `const tagMaster = ${JSON.stringify(TAG_MASTER, null, 4)};\n` +
                       `const productData = ${JSON.stringify(products, null, 4)};\n`;

        await fs.writeFile(JS_PATH, output);
        const fileTime = stats.mtime.toLocaleString();
        console.log('--------------------------------------------------');
        console.log(`📄 変換完了: ${csvFileName}`);
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
            if (filename && filename.includes('products') && filename.endsWith('.csv') && !filename.startsWith('.')) {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => run(), 200); // 連続保存対策のディレイ
            }
        });
    } else {
        run();
    }
}