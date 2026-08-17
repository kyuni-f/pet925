const { normalize } = require('../common.js');

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
