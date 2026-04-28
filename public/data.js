// Last Updated: 2026/4/28 13:34:33
const tagMaster = {
    "animal": {
        "dog": "犬 (DOG)",
        "cat": "猫 (CAT)"
    },
    "cond": {
        "tear": "涙やけ (TEAR)",
        "gf": "穀物不使用 (GF)",
        "diet": "体重管理 (WEIGHT)",
        "kidney": "腎臓・尿路 (KIDNEY)",
        "senior": "シニア (SENIOR)",
        "adult": "成犬用 (ADULT)",
        "skin": "皮膚ケア (SKIN)",
        "lamb": "ラム肉 (LAMB)",
        "venison": "鹿肉 (VENISON)",
        "joint": "関節ケア (JOINT)",
        "tooth": "歯の健康 (TOOTH)",
        "appetite": "食いつき (APPETITE)"
    }
};
const productData = [
    {
        "name": "ナチュラル チョイス 成犬用 ラム＆玄米 (皮膚被毛・涙やけケア・お悩み別)",
        "brand": "Nutro",
        "tags": [
            "dog",
            "adult",
            "skin",
            "lamb",
            "tear"
        ],
        "desc": "高品質なラム肉を使用。食物アレルギーに配慮し、健康な皮膚・被毛の維持をサポートします。",
        "img": "https://unsplash.com",
        "amz": "#",
        "rak": "#",
        "yah": "#",
        "a8": "#",
        "label": "人気No.1",
        "promo": "",
        "amz_p": "1200",
        "rak_p": "1150",
        "yah_p": "1300"
    },
    {
        "name": "ナチュラル チョイス 減量用 全犬種用 (体重管理・ダイエット・低カロリー)",
        "brand": "Nutro",
        "tags": [
            "dog",
            "adult",
            "diet",
            "lamb"
        ],
        "desc": "低カロリー・低脂質設計。肥満が気になる愛犬の健康的な減量をサポートします。",
        "img": "https://unsplash.com",
        "amz": "#",
        "rak": "#",
        "yah": "#",
        "a8": "#",
        "label": "",
        "promo": "",
        "amz_p": "2500",
        "rak_p": "2600",
        "yah_p": "2400"
    },
    {
        "name": "ワイルド レシピ 鹿肉 (穀物不使用・成犬用・高タンパク・アレルギーケア)",
        "brand": "Nutro",
        "tags": [
            "dog",
            "adult",
            "gf",
            "tear",
            "venison"
        ],
        "desc": "野生の食性に近い高タンパク・穀物不使用レシピ。鹿肉を使用し、アレルギーや涙やけにも配慮。",
        "img": "https://unsplash.com",
        "amz": "#",
        "rak": "#",
        "yah": "#",
        "a8": "#",
        "label": "高タンパク",
        "promo": "",
        "amz_p": "4200",
        "rak_p": "4100",
        "yah_p": "4150"
    },
    {
        "name": "シュプレモ 成犬用 (全犬種用・涙やけ・栄養バランス・ホリスティック)",
        "brand": "Supremo",
        "tags": [
            "dog",
            "adult",
            "tear"
        ],
        "desc": "17種類の厳選された自然素材をブレンド。栄養バランスに優れ、健康な体づくりを支えます。",
        "img": "https://unsplash.com",
        "amz": "#",
        "rak": "#",
        "yah": "#",
        "a8": "#",
        "label": "Editor's Choice",
        "promo": "",
        "amz_p": "3000",
        "rak_p": "3100",
        "yah_p": "2900"
    },
    {
        "name": "シュプレモ 湖畔のレシピ ラム (穀物不使用・成犬用・涙やけケア・アレルギー)",
        "brand": "Supremo",
        "tags": [
            "dog",
            "adult",
            "gf",
            "lamb",
            "tear"
        ],
        "desc": "ラム肉を第一主原料に使用。穀物不使用で消化に優しく、目元の健康（涙やけ）が気になる子にも。",
        "img": "https://unsplash.com",
        "amz": "#",
        "rak": "#",
        "yah": "#",
        "a8": "#",
        "label": "",
        "promo": "",
        "amz_p": "3500",
        "rak_p": "3400",
        "yah_p": "3600"
    },
    {
        "name": "シュプレモ エイジングケア (シニア犬用・高齢犬・関節ケア・健康維持)",
        "brand": "Supremo",
        "tags": [
            "dog",
            "senior",
            "joint",
            "tear"
        ],
        "desc": "シニア期の健康維持に配慮。関節の健康を守る栄養素と、高い消化性を兼ね備えています。",
        "img": "https://unsplash.com",
        "amz": "#",
        "rak": "#",
        "yah": "#",
        "a8": "#",
        "label": "",
        "promo": "",
        "amz_p": "4000",
        "rak_p": "4050",
        "yah_p": "3950"
    },
    {
        "name": "ロイヤルカナン ミニ デンタル ケア (小型犬用・歯垢・歯石・歯の健康)",
        "brand": "Royal Canin",
        "tags": [
            "dog",
            "adult",
            "tooth"
        ],
        "desc": "歯垢・歯石が気になる小型犬用。独自の粒形状で、噛むことで歯の汚れを落とします。",
        "img": "https://unsplash.com",
        "amz": "#",
        "rak": "#",
        "yah": "#",
        "a8": "#",
        "label": "",
        "promo": "",
        "amz_p": "1500",
        "rak_p": "1550",
        "yah_p": "1450"
    },
    {
        "name": "ロイヤルカナン ダーマコンフォート (皮膚被毛・涙やけ・アレルギー配慮)",
        "brand": "Royal Canin",
        "tags": [
            "dog",
            "adult",
            "skin",
            "tear"
        ],
        "desc": "皮膚が敏感な犬用。オメガ3・6脂肪酸を配合し、健康な皮膚の状態を維持します。",
        "img": "https://unsplash.com",
        "amz": "#",
        "rak": "#",
        "yah": "#",
        "a8": "#",
        "label": "",
        "promo": "公式サイト限定特典あり",
        "amz_p": "2800",
        "rak_p": "2750",
        "yah_p": "2900"
    },
    {
        "name": "ロイヤルカナン ユリナリー ケア (猫用・尿路健康・結石予防・腎臓)",
        "brand": "Royal Canin",
        "tags": [
            "cat",
            "adult",
            "kidney"
        ],
        "desc": "健康な尿を維持したい猫用。ミネラルバランスを調整し、尿路結石の形成を抑制します。",
        "img": "https://unsplash.com",
        "amz": "#",
        "rak": "#",
        "yah": "#",
        "a8": "#",
        "label": "",
        "promo": "",
        "amz_p": "2000",
        "rak_p": "2100",
        "yah_p": "1950"
    },
    {
        "name": "シーバ デュオ まぐろ味セレクション (猫用・食いつき・おやつ・偏食)",
        "brand": "Sheba",
        "tags": [
            "cat",
            "adult",
            "appetite"
        ],
        "desc": "外はカリカリ、中はクリーミー。食欲にムラがある猫ちゃんも喜ぶ贅沢な味わいです。",
        "img": "https://unsplash.com",
        "amz": "#",
        "rak": "#",
        "yah": "#",
        "a8": "#",
        "label": "",
        "promo": "",
        "amz_p": "800",
        "rak_p": "750",
        "yah_p": "850"
    }
];
