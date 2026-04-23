const fs = require('fs');
const path = require('path');

const CSV_PATH = path.join(__dirname, 'products.csv');
const JS_PATH = path.join(__dirname, 'data.js');

// 簡易的なCSVパース関数（クォート対応）
function parseCSV(content) {
    const lines = content.trim().split('\n');
    const headers = lines[0].split(',');
    
    return lines.slice(1).map(line => {
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
            // tags列はスペース区切りを配列に変換
            if (header === 'tags') {
                obj[header] = val.split(' ').filter(t => t);
            } else {
                obj[header] = val;
            }
        });
        return obj;
    });
}

const csvContent = fs.readFileSync(CSV_PATH, 'utf8');
const products = parseCSV(csvContent);
const output = `const productData = ${JSON.stringify(products, null, 4)};\n`;

fs.writeFileSync(JS_PATH, output);
console.log('✅ data.js を更新しました！');