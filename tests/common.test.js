const {
    normalize,
    isKindCategory,
    getDefaultKindCategory,
    itemMatchesKind,
    sortFilterCategories
} = require('../common.js');

describe('normalize()', () => {
    test('全角スペースを半角スペースに変換する', () => {
        // ひらがなはカタカナへ変換されるため、期待値もカタカナで書く
        expect(normalize('ねこ　まんま')).toBe('ネコ マンマ');
    });

    test('ひらがなとカタカナの表記ゆれを同一視する', () => {
        expect(normalize('ねこ')).toBe(normalize('ネコ'));
        expect(normalize('ねこ')).toBe('ネコ');
    });

    test('全角英数字をNFKC正規化で半角に変換する', () => {
        expect(normalize('ＡＢＣ１２３')).toBe('abc123');
    });

    test('大文字・小文字を区別しない', () => {
        expect(normalize('Nutro')).toBe(normalize('nutro'));
    });

    test('前後の空白を取り除く', () => {
        expect(normalize('  心臓  ')).toBe(normalize('心臓'));
        expect(normalize('  心臓  ')).toBe('心臓');
    });

    test('空文字・null・undefinedは空文字を返す', () => {
        expect(normalize('')).toBe('');
        expect(normalize(null)).toBe('');
        expect(normalize(undefined)).toBe('');
    });

    test('数値など文字列以外が渡されても文字列化して処理する', () => {
        expect(normalize(123)).toBe('123');
    });
});

describe('種類枠 (kind)', () => {
    const tagMaster = {
        animal: { dog: '犬', cat: '猫' },
        age: { adult: '成犬' },
        cond: { gf: '穀物不使用', tear: '涙やけ' },
        care: { dental: 'デンタル' },
        out: { leash: 'リード' }
    };

    test('animal / age 以外が種類枠', () => {
        expect(isKindCategory('animal')).toBe(false);
        expect(isKindCategory('age')).toBe(false);
        expect(isKindCategory('cond')).toBe(true);
        expect(isKindCategory('care')).toBe(true);
    });

    test('デフォルト種類枠は cond', () => {
        expect(getDefaultKindCategory(tagMaster)).toBe('cond');
    });

    test('種類タグが無い商品はお悩み（フード）に出す', () => {
        expect(itemMatchesKind(['dog', 'adult'], 'cond', tagMaster)).toBe(true);
        expect(itemMatchesKind(['dog', 'adult'], 'care', tagMaster)).toBe(false);
    });

    test('ケアタグがある商品はお悩みに出さない', () => {
        expect(itemMatchesKind(['dog', 'dental'], 'cond', tagMaster)).toBe(false);
        expect(itemMatchesKind(['dog', 'dental'], 'care', tagMaster)).toBe(true);
    });

    test('枠の並びは categories の行順、未登録は末尾', () => {
        const categoryMaster = { animal: {}, age: {}, cond: {}, care: {} };
        expect(sortFilterCategories(tagMaster, categoryMaster)).toEqual([
            'animal', 'age', 'cond', 'care', 'out'
        ]);
    });
});
