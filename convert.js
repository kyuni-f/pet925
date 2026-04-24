const fs = require('fs');
const path = require('path');

const filesInDir = fs.readdirSync(__dirname);
// 'products.csv ' のように末尾にスペースが入っていても自動で検知できるようにします
const csvFileName = filesInDir.find(f => f.trim() === 'products.csv') || 'products.csv';
const CSV_PATH = path.join(__dirname, csvFileName);
const JS_PATH = path.join(__dirname, 'data.js');

// 許可されているタグのリスト（index.htmlのフィルターと連動するもの）
const ALLOWED_TAGS = [
    'dog', 'cat', 'tear', 'gf', 'diet', 'kidney', 'senior',
    'adult', 'skin', 'lamb', 'venison', 'joint', 'tooth', 'appetite'
];

// 簡易的なCSVパース関数（クォート対応）
function parseCSV(content) {
    // 改行コード（CRLF/LF）に対応し、空行を除外
    const lines = content.split(/\r?\n/).filter(line => line.trim() !== '');
    
    // 「name,brand」で始まる行（見出し行）を探す
    // より確実に、カンマの数なども考慮した正規表現で探すように強化
    const headerIndex = lines.findIndex(l => /^(?:"?name"?,"?brand"?,"?tags"?)/.test(l));
    if (headerIndex === -1) throw new Error('見出し行(name,brand...)が見つかりません。');

    const headers = lines[headerIndex].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
    
    return lines.slice(headerIndex + 1).map((line, index) => {
        const values = [];
        let current = '';
        let inQuotes = false;

        for (let char of line) {
            if (char === '"') inQuotes = !inQuotes;
            else if (char === ',' && !inQuotes) {
                values.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }
        values.push(current.trim());

        const obj = {};
        headers.forEach((header, i) => {
            let val = values[i] || '';
            // クォートで囲まれている場合は除去
            val = val.replace(/^"|"$/g, '').trim();

            // tags列はスペース区切りを配列に変換
            if (header === 'tags') {
                // 全角スペースも半角に変換してから分割
                const tags = val.replace(/　/g, ' ').split(/\s+/).filter(t => t);
                // タグのバリデーション（チェック）
                tags.forEach(tag => {
                    if (!ALLOWED_TAGS.includes(tag)) {
                        console.warn(`⚠️  警告: [行 ${index + headerIndex + 2}] 未定義のタグがあります: "${tag}" (商品: ${obj.name || '不明'})`);
                    }
                });
                obj[header] = tags;
            } else {
                obj[header] = val;
            }
        });
        return obj;
    });
}

try {
    // ファイルが存在するか事前にチェック
    if (!fs.existsSync(CSV_PATH)) {
        console.error(`❌ エラー: CSVファイルが見つかりません。`);
        console.error(`期待されている場所: ${CSV_PATH}`);

        // フォルダ内のファイル一覧を表示して、ユーザーが間違いに気づけるようにする
        const files = fs.readdirSync(__dirname);
        console.log('\n--- 現在のフォルダにあるファイル一覧 ---');
        files.forEach(f => console.log(` - ${f}`));
        
        console.error('\n👉 上記の一覧に "products.csv" はありますか？');
        console.error('拡張子が .csv.txt や .csv.csv になっていないか確認してください。');
        process.exit(1);
    }

    const csvContent = fs.readFileSync(CSV_PATH, 'utf8');
    const products = parseCSV(csvContent);
    
    // 更新日時を追加することで、ブラウザのコンソールで更新を確認しやすくします
    const output = `// Last Updated: ${new Date().toLocaleString()}\n` +
                   `const productData = ${JSON.stringify(products, null, 4)};\n`;

    fs.writeFileSync(JS_PATH, output);
    console.log('--------------------------------------------------');
    console.log(`✅ 完了: ${products.length} 件の商品を処理しました。`);
    console.log(`⏰ 更新時刻: ${new Date().toLocaleString()}`);
    console.log('👉 index.html を [Ctrl + F5] でリロードしてください。');
    console.log('--------------------------------------------------');
} catch (err) {
    console.error('❌ 変換エラー:', err.message);
}