const tagMaster = {
    "animal": {
        "cat": "猫 (CAT)",
        "dog": "犬 (DOG)"
    },
    "age": {
        "adult": "成犬・成猫 (ADULT)",
        "all_ages": "全年齢用 (ALL AGES)",
        "puppy": "子犬・子猫 (PUPPY)",
        "senior": "シニア (SENIOR)"
    },
    "cond": {
        "appetite": "食いつき (APPETITE)",
        "diet": "体重管理 (WEIGHT)",
        "digestive": "消化器ケア (DIGESTIVE)",
        "gf": "穀物不使用 (GF)",
        "joint": "関節ケア (JOINT)",
        "kidney": "腎臓・尿路 (KIDNEY)",
        "lamb": "ラム肉 (LAMB)",
        "skin": "皮膚ケア (SKIN)",
        "tear": "涙やけ (TEAR)",
        "tooth": "歯の健康 (TOOTH)"
    }
};
const categoryMaster = {
    "type": {
        "jp": "カテゴリー",
        "en": "Category",
        "multi": false
    },
    "animal": {
        "jp": "種類",
        "en": "Animal",
        "multi": false
    },
    "age": {
        "jp": "年齢",
        "en": "Age",
        "multi": false
    },
    "cond": {
        "jp": "こだわり・お悩み",
        "en": "Preference",
        "multi": true
    }
};
const brandMaster = {
    "nutro": "ニュートロ",
    "royal canin": "ロイヤルカナン",
    "sheba": "シーバ",
    "supremo": "シュプレモ"
};
const tagKeywords = {
    "gf": ["grain_free", "grainfree", "グレインフリー", "穀物不使用"],
    "digestive": ["胃腸", "消化", "オナカ", "digestive", "オ腹"],
    "diet": ["体重", "肥満", "ダイエット", "減量"],
    "lamb": ["ラム肉", "lamb"]
};