// comment_logic.js は共通スコープの `normalize` と `comments`（data_master.js由来）を前提にしているため、
// ブラウザでの読み込み順（data_master.js -> common.js -> comment_logic.js）と同じ状態を
// テスト側で用意してから require する。
const sampleComments = [
    { category: 'animal', key: 'dog', comment: '犬コメントA' },
    { category: 'animal', key: 'cat', comment: '猫コメントA' },
    { category: 'cond', key: 'tear', comment: '涙やけコメントA' },
    { category: 'cond', key: 'tear', comment: '涙やけコメントB' },
    { category: 'cond', key: 'skin', comment: '皮膚コメントA' },
    { category: 'keyword', key: '心臓', comment: '心臓コメント' },
    { category: 'keyword', key: '納豆菌', comment: '納豆菌コメント' },
];

global.normalize = require('../common.js').normalize;
// pickStoreComments() は内部で getCommentLookup() を引数なしで呼ぶため、
// グローバルの `comments` も用意しておく（明示的に引数を渡すpickKeywordComments()のテストでは使われない）
global.comments = sampleComments;
const { getCommentLookup, pickStoreComments, pickKeywordComments, pickPopularSearchWords, formatPopularSearchHint } = require('../comment_logic.js');

describe('getCommentLookup()', () => {
    test('category:key をキーにしたコメント配列のマップを作る', () => {
        const lookup = getCommentLookup(sampleComments);
        expect(lookup['animal:dog']).toEqual(['犬コメントA']);
        expect(lookup['cond:tear']).toEqual(['涙やけコメントA', '涙やけコメントB']);
        expect(lookup['keyword:心臓']).toEqual(['心臓コメント']);
    });

    test('空配列を渡すと空のマップを返す', () => {
        expect(getCommentLookup([])).toEqual({});
    });
});

describe('pickStoreComments()', () => {
    test('condタグが選択されていれば、そのタグのコメントを返す', () => {
        const result = pickStoreComments({ cond: ['skin'], animal: 'all' });
        expect(result).toEqual(['皮膚コメントA']);
    });

    test('condが未選択でanimalが選択されていれば、animalのコメントにフォールバックする', () => {
        const result = pickStoreComments({ cond: [], animal: 'dog' });
        expect(result).toEqual(['犬コメントA']);
    });

    test('condもanimalも未選択なら空配列を返す', () => {
        const result = pickStoreComments({ cond: [], animal: 'all' });
        expect(result).toEqual([]);
    });

    test('該当するコメントがないタグを選んだ場合は空配列を返す', () => {
        const result = pickStoreComments({ cond: ['unknown_tag'], animal: 'all' });
        expect(result).toEqual([]);
    });

    test('最大MAX_STORE_COMMENTS(2)件までしか返さない', () => {
        // 3つ以上condタグを選んでも、返るのは最大2件
        const result = pickStoreComments({ cond: ['tear', 'skin', 'unknown_tag'], animal: 'all' });
        expect(result.length).toBeLessThanOrEqual(2);
    });
});

describe('pickKeywordComments()', () => {
    test('完全一致する単語で該当コメントを返す', () => {
        expect(pickKeywordComments('心臓', sampleComments)).toEqual(['心臓コメント']);
    });

    test('文中に埋め込まれた単語でも部分一致で反応する', () => {
        expect(pickKeywordComments('うちの子は心臓が弱くて', sampleComments)).toEqual(['心臓コメント']);
    });

    test('無関係な単語では何も返さない', () => {
        expect(pickKeywordComments('チキン', sampleComments)).toEqual([]);
    });

    test('空文字では何も返さない', () => {
        expect(pickKeywordComments('', sampleComments)).toEqual([]);
    });

    test('category="keyword"以外の行（cond/animal）には反応しない', () => {
        expect(pickKeywordComments('dog', sampleComments)).toEqual([]);
        expect(pickKeywordComments('tear', sampleComments)).toEqual([]);
    });
});

describe('pickPopularSearchWords()', () => {
    test('空なら空配列を返す', () => {
        expect(pickPopularSearchWords([])).toEqual([]);
    });

    test('空の word と重複は除き、3件未満ならある分だけ返す', () => {
        const rows = [
            { word: '心臓' },
            { word: '  ' },
            { word: '納豆菌' },
            { word: '心臓' },
        ];
        const result = pickPopularSearchWords(rows);
        expect(result.sort()).toEqual(['心臓', '納豆菌']);
    });

    test('3件を超えるときは最大3件だけ返す', () => {
        const rows = [
            { word: '心臓' },
            { word: '納豆菌' },
            { word: '涙やけ' },
            { word: 'ラム肉' },
        ];
        const result = pickPopularSearchWords(rows);
        expect(result).toHaveLength(3);
        result.forEach(word => {
            expect(['心臓', '納豆菌', '涙やけ', 'ラム肉']).toContain(word);
        });
    });
});

describe('formatPopularSearchHint()', () => {
    test('語が無ければ空文字を返す', () => {
        expect(formatPopularSearchHint([])).toBe('');
    });

    test('3語を読点でつなぐ', () => {
        expect(formatPopularSearchHint(['心臓', '納豆菌', '涙やけ']))
            .toBe('よく検索されているワードは心臓、納豆菌、涙やけです');
    });

    test('1語でも文として成立する', () => {
        expect(formatPopularSearchHint(['心臓'])).toBe('よく検索されているワードは心臓です');
    });
});
