const { 
    parseCSV, 
    normalizeText,
    getValidationErrors, 
    clearValidationErrors, 
    TAG_MASTER, 
    BRAND_MASTER, 
    AUTO_TAG_RULES,
    updateAllowedTags 
} = require('./convert');

describe('CSV Parser Tests', () => {
    beforeEach(() => {
        // テストごとに状態を完全にリセットする
        clearValidationErrors();
        
        // マスターデータを空にする
        Object.keys(TAG_MASTER).forEach(k => delete TAG_MASTER[k]);
        Object.keys(BRAND_MASTER).forEach(k => delete BRAND_MASTER[k]);
        AUTO_TAG_RULES.length = 0;
        
        // 基本的なテスト用データをセット
        BRAND_MASTER['nutro'] = 'ニュートロ';
        updateAllowedTags();
    });

    test('normalizeText が日本語や全角文字を正しく正規化すること', () => {
        // ひらがな -> カタカナ
        expect(normalizeText("ぬーとろ")).toBe("ヌートロ");
        // 全角英数 -> 半角
        expect(normalizeText("ＡＢＣ１２３")).toBe("abc123");
        // 混合
        expect(normalizeText("　ニュートロ wild　")).toBe("ニュートロ wild");
    });

    test('正常なCSVデータを正しくオブジェクトに変換できること', () => {
        // タグの準備
        TAG_MASTER['animal'] = { 'dog': '犬' };
        TAG_MASTER['age'] = { 'adult': '成犬' };
        updateAllowedTags();

        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
テスト商品,Nutro,dog adult,説明文,2kg,https://example.com,#,#,#,#,ラベル,プロモ,1000,1100,1050`;
        const result = parseCSV(csv);
        
        expect(result).toHaveLength(1);
        expect(result[0].name).toBe('テスト商品');
        expect(result[0].tags).toEqual(['dog', 'adult']);
        expect(getValidationErrors()).toHaveLength(0); // バリデーションエラーがないこと
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

    test('ブランド列が空の場合、商品名からブランドを自動検知できること', () => {
        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
ニュートロの犬缶,,dog,おいしい,1kg,#,#,#,#,#,,0,0,0`;
        const result = parseCSV(csv);
        
        // BRAND_MASTER['nutro'] = 'ニュートロ' に基づいて補完される
        expect(result[0].brand).toBe('Nutro');
    });

    test('AUTO_TAG_RULES に基づき、説明文からタグが自動付与されること', () => {
        // ルールの設定
        AUTO_TAG_RULES.push({ tag: 'gf', keyword: 'グレインフリー' });
        updateAllowedTags();

        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
商品A,Nutro,dog,これはグレインフリーな食事です,1kg,#,#,#,#,#,,0,0,0`;
        const result = parseCSV(csv);
        
        expect(result[0].tags).toContain('gf');
    });

    test('自動タグ付けが正規化（ひらがな・全角など）を考慮して動作すること', () => {
        // ルールはカタカナの「ラム」
        AUTO_TAG_RULES.push({ tag: 'lamb', keyword: 'ラム' });
        updateAllowedTags();

        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
テスト商品,Nutro,dog,ひらがなで「らむ肉」配合,1kg,#,#,#,#,#,,0,0,0`;
        const result = parseCSV(csv);
        
        expect(result[0].tags).toContain('lamb');
    });

    test('複数の自動タグ付けルールが同時に適用されること', () => {
        AUTO_TAG_RULES.push({ tag: 'gf', keyword: 'グレインフリー' });
        AUTO_TAG_RULES.push({ tag: 'lamb', keyword: 'ラム' });
        updateAllowedTags();

        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
テスト商品,Nutro,dog,ラム肉使用のグレインフリーフード,1kg,#,#,#,#,#,,0,0,0`;
        const result = parseCSV(csv);
        
        expect(result[0].tags).toContain('gf');
        expect(result[0].tags).toContain('lamb');
    });

    test('タグ列に入力されたキーワードに基づいて自動タグ付けが行われること', () => {
        AUTO_TAG_RULES.push({ tag: 'gf', keyword: 'grainfree' });
        updateAllowedTags();

        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
テスト商品,Nutro,grainfree,説明文にはなし,1kg,#,#,#,#,#,,0,0,0`;
        const result = parseCSV(csv);
        
        expect(result[0].tags).toContain('gf');
    });
});