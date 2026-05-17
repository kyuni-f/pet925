const { 
    parseCSV, 
    normalizeText,
    getValidationErrors, 
    clearValidationErrors, 
    TAG_MASTER, 
    BRAND_MASTER, 
    CATEGORY_MASTER,
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
        Object.keys(CATEGORY_MASTER).forEach(k => delete CATEGORY_MASTER[k]);
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
        BRAND_MASTER['nutro'] = 'ニュートロ';
        updateAllowedTags();

        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
テスト商品,nutro,dog adult,説明文,2kg,https://example.com,#,#,#,#,ラベル,プロモ,1000,1100,1050`;
        const result = parseCSV(csv);
        
        expect(result).toHaveLength(1);
        expect(result[0].name).toBe('テスト商品');
        expect(result[0].brand).toBe('nutro'); // 入力の値が維持されること
        expect(result[0].size).toBe('2kg');
        expect(result[0].tags).toEqual(['dog', 'adult']);
        expect(getValidationErrors()).toHaveLength(0);
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

    test('引用符が閉じられていない場合にエラーを検知すること', () => {
        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
"閉じていない引用符,Nutro,dog,desc,1kg,#,#,#,#,#,,0,0,0`;
        parseCSV(csv);
        const errors = getValidationErrors();
        expect(errors.some(e => e.includes('閉じられていない引用符'))).toBe(true);
    });

    test('列数が一致しない行がある場合に警告を出すこと', () => {
        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
列が足りない商品,Nutro,dog`;
        parseCSV(csv);
        const errors = getValidationErrors();
        expect(errors.some(e => e.includes('列数が一致しません'))).toBe(true);
    });

    test('価格列に数値以外が入っている場合に警告を出すこと', () => {
        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
テスト商品,Nutro,dog,説明,1kg,#,#,#,#,#,,0,1200円,1,0`;
        parseCSV(csv);
        const errors = getValidationErrors();
        expect(errors.some(e => e.includes('数値以外が含まれています'))).toBe(true);
    });

    test('商品名(name)が空の場合に警告を出すこと', () => {
        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
,Nutro,dog,説明,1kg,#,#,#,#,#,,0,0,0`;
        parseCSV(csv);
        const errors = getValidationErrors();
        expect(errors.some(e => e.includes('商品名(name)が空です'))).toBe(true);
    });

    test('商品ごとのタグが「種類 -> 年齢 -> こだわり」の順に自動で並び替えられること', () => {
        // カテゴリの定義順序をセット（これが並び順のマスターになる）
        CATEGORY_MASTER['animal'] = { jp: '種類', multi: false };
        CATEGORY_MASTER['age'] = { jp: '年齢', multi: false };
        CATEGORY_MASTER['cond'] = { jp: 'こだわり', multi: true };

        // 各カテゴリに属するタグの準備
        TAG_MASTER['animal'] = { 'dog': '犬' };
        TAG_MASTER['age'] = { 'adult': '成犬' };
        TAG_MASTER['cond'] = { 'gf': '穀物不使用' };
        updateAllowedTags();

        // 入力は「こだわり(gf) -> 年齢(adult) -> 種類(dog)」のバラバラな順番
        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
テスト商品,Nutro,gf adult dog,説明,1kg,#,#,#,#,#,,0,0,0`;
        const result = parseCSV(csv);

        // 期待される順番: dog (animal=1) -> adult (age=2) -> gf (cond=3)
        expect(result[0].tags).toEqual(['dog', 'adult', 'gf']);
    });

    test('タグの重複が自動的に排除されること', () => {
        TAG_MASTER['animal'] = { 'dog': '犬' };
        updateAllowedTags();
        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
重複タグ商品,Nutro,dog dog dog,説明,1kg,#,#,#,#,#,,0,0,0`;
        const result = parseCSV(csv);
        expect(result[0].tags).toEqual(['dog']);
    });

    test('ブランド列が空の場合、商品名からブランドを自動検知できること', () => {
        BRAND_MASTER['nutro'] = 'ニュートロ';
        const csv = `name,brand,tags,desc,size,img,amz,rak,yah,a8,label,promo,amz_p,rak_p,yah_p
ニュートロの犬缶,,dog,おいしい,1kg,#,#,#,#,#,,0,0,0`;
        const result = parseCSV(csv);
        
        expect(result[0].brand).toBe('ニュートロ');
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