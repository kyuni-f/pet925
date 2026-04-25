const { parseCSV, getValidationErrors, clearValidationErrors } = require('./convert');

describe('CSV Parser Tests', () => {
    beforeEach(() => {
        // テストごとにエラーリストを空にする
        clearValidationErrors();
    });

    test('正常なCSVデータを正しくオブジェクトに変換できること', () => {
        const csv = `name,brand,tags,desc,img,amz,rak,yah,a8,label,promo
テスト商品,ブランドA,dog adult,説明文,https://example.com,#,#,#,#,ラベル,プロモ`;
        const result = parseCSV(csv);
        
        expect(result).toHaveLength(1);
        expect(result[0].name).toBe('テスト商品');
        expect(result[0].tags).toEqual(['dog', 'adult']);
    });

    test('ダブルクォーテーションで囲まれたカンマを含む値を正しく処理できること', () => {
        const csv = `name,brand,tags,desc,img,amz,rak,yah,a8,label,promo
"商品名, カンマあり",ブランドB,cat,"説明文, カンマあり",#,#,#,#,#,,`;
        const result = parseCSV(csv);
        
        expect(result[0].name).toBe('商品名, カンマあり');
        expect(result[0].desc).toBe('説明文, カンマあり');
    });

    test('許可されていないタグが含まれている場合に警告を検知できること', () => {
        const csv = `name,brand,tags,desc,img,amz,rak,yah,a8,label,promo
テスト商品,ブランドC,invalid_tag,説明,#,#,#,#,#,,`;
        parseCSV(csv);
        
        const errors = getValidationErrors();
        expect(errors.length).toBeGreaterThan(0);
        expect(errors[0]).toContain('invalid_tag');
    });

    test('空の行が含まれていても無視されること', () => {
        const csv = `name,brand,tags,desc,img,amz,rak,yah,a8,label,promo

商品A,ブランドA,dog,説明,#,#,#,#,#,,`;
        const result = parseCSV(csv);
        expect(result).toHaveLength(1);
    });
});