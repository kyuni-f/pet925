const { parseCSV, getValidationErrors, clearValidationErrors, TAG_MASTER, BRAND_MASTER, updateAllowedTags } = require('./convert');

describe('CSV Parser Tests', () => {
    beforeEach(() => {
        // テストごとにエラーリストを空にする
        clearValidationErrors();
    });

    test('正常なCSVデータを正しくオブジェクトに変換できること', () => {
        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
テスト商品,ブランドA,dog adult,説明文,2kg,https://example.com,#,#,#,#,ラベル,プロモ,1000,1100,1050`;
        const result = parseCSV(csv);
        
        expect(result).toHaveLength(1);
        expect(result[0].name).toBe('テスト商品');
        expect(result[0].tags).toEqual(['dog', 'adult']);
        expect(result[0].size).toBe('2kg');
    });

    test('useHeaderMap: false の場合、ヘッダーを無視して生の配列を返すこと', () => {
        const csv = `col1,col2\nval1,val2`;
        const result = parseCSV(csv, false);
        
        expect(result).toEqual([['col1', 'col2'], ['val1', 'val2']]);
    });

    test('ダブルクォーテーションで囲まれたカンマを含む値を正しく処理できること', () => {
        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
"商品名, カンマあり",ブランドB,cat,"説明文, カンマあり",500g,#,#,#,#,#,,0,0,0`;
        const result = parseCSV(csv);
        
        expect(result[0].name).toBe('商品名, カンマあり');
        expect(result[0].desc).toBe('説明文, カンマあり');
    });

    test('許可されていないタグが含まれている場合に警告を検知できること', () => {
        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
テスト商品,ブランドC,invalid_tag,説明,1kg,#,#,#,#,#,,0,0,0`;
        parseCSV(csv);
        
        const errors = getValidationErrors();
        expect(errors.some(e => e.includes('invalid_tag'))).toBe(true);
    });

    test('未登録のブランドが含まれている場合に警告を検知できること', () => {
        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
テスト商品,UnknownBrand,dog,説明,1kg,#,#,#,#,#,,0,0,0`;
        parseCSV(csv);
        
        const errors = getValidationErrors();
        expect(errors.some(e => e.includes('UnknownBrand'))).toBe(true);
    });

    test('見出し行（name, brand）が存在しない場合にエラーを投げること', () => {
        const csv = `id,value,info\n1,test,data`;
        
        expect(() => parseCSV(csv)).toThrow('「見出し行」が見つかりません');
    });

    test('空の行が含まれていても無視されること', () => {
        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p

商品A,ブランドA,dog,説明,1kg,#,#,#,#,#,,0,0,0`;
        const result = parseCSV(csv);
        expect(result).toHaveLength(1);
    });
});