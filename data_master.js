const siteVersion = '20260809020456';
const tagMaster = {
    "animal": {
        "dog": "犬 (DOG)",
        "cat": "猫 (CAT)"
    },
    "age": {
        "all_ages": "全年齢用 (ALL AGES)",
        "puppy": "子犬・子猫 (PUPPY)",
        "adult": "成犬・成猫 (ADULT)",
        "senior": "シニア (SENIOR)"
    },
    "cond": {
        "tear": "涙やけ (TEAR)",
        "diet": "体重管理 (WEIGHT)",
        "kidney": "腎臓・尿路 (KIDNEY)",
        "skin": "皮膚ケア (SKIN)",
        "joint": "関節ケア (JOINT)",
        "tooth": "歯の健康 (TOOTH)",
        "appetite": "食いつき (APPETITE)",
        "gf": "穀物不使用 (GF)",
        "digestive": "消化器ケア (DIGESTIVE)",
        "lamb": "ラム肉 (LAMB)"
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
const tagKeywords = {
    "gf": [
        "グレインフリー",
        "穀物不使用"
    ],
    "digestive": [
        "胃腸",
        "消化",
        "オナカ",
        "オ腹"
    ],
    "diet": [
        "体重",
        "肥満",
        "ダイエット",
        "減量"
    ],
    "lamb": [
        "ラム肉"
    ],
    "tooth": [
        "歯"
    ],
    "dog": [
        "犬"
    ],
    "cat": [
        "猫"
    ],
    "all_ages": [
        "全年齢用"
    ],
    "puppy": [
        "子犬・子猫"
    ],
    "adult": [
        "成犬・成猫"
    ],
    "senior": [
        "シニア"
    ],
    "tear": [
        "涙ヤケ"
    ],
    "kidney": [
        "腎臓・尿路"
    ],
    "skin": [
        "皮膚",
        "アレルギー"
    ],
    "joint": [
        "関節",
        "骨折"
    ],
    "appetite": [
        "食イツキ",
        "食ベムラ"
    ]
};
const CONTACT_MAIL_CODES = [121, 111, 117, 114, 45, 101, 109, 97, 105, 108, 64, 101, 120, 97, 109, 112, 108, 101, 46, 99, 111, 109];
const comments = [
    {
        "category": "animal",
        "key": "dog",
        "comment": "わんちゃんは涙やけや食いつきのご相談がお店でも本当に多いです。フード選びで改善するケースをたくさん見てきました"
    },
    {
        "category": "animal",
        "key": "dog",
        "comment": "犬種によって食いつきの好みがかなり違うので、まずは小袋タイプから試してみるのもおすすめですよ"
    },
    {
        "category": "animal",
        "key": "cat",
        "comment": "猫ちゃんは腎臓・尿路のケアで来店される方が年齢とともに増えてくる印象です。早めのケアがおすすめです"
    },
    {
        "category": "animal",
        "key": "cat",
        "comment": "猫は好みが変わりやすいので、いくつかローテーションできるフードを用意しておくと安心という声をよく聞きます"
    },
    {
        "category": "cond",
        "key": "tear",
        "comment": "涙やけの相談は本当に多いです。フードだけでなく食器の材質が原因のこともあるので、両方見直す方が多いですよ"
    },
    {
        "category": "cond",
        "key": "diet",
        "comment": "体重管理は『量を減らす』より『満腹感が続くフード』に変える方が、ストレスなく続けられている子が多い印象です"
    },
    {
        "category": "cond",
        "key": "kidney",
        "comment": "腎臓・尿路のケアは早めに始めるほど選択肢が広がるので、気になったタイミングで一度見直すのがおすすめです"
    },
    {
        "category": "cond",
        "key": "skin",
        "comment": "皮膚が気になる子は、フードを変えて数週間で毛艶が良くなったという声をよくいただきます"
    },
    {
        "category": "cond",
        "key": "joint",
        "comment": "関節ケアは中〜大型犬のシニア期に相談が増えますが、早めに切り替えている方も多いですよ"
    },
    {
        "category": "cond",
        "key": "tooth",
        "comment": "歯の健康は毎日のケアが大変という方が多いので、フードの硬さで工夫するのも一つの方法です"
    },
    {
        "category": "cond",
        "key": "appetite",
        "comment": "食いつきが悪い時は、フードそのものよりも温度や香りを変えるだけで食べてくれることもよくあります"
    },
    {
        "category": "cond",
        "key": "gf",
        "comment": "穀物不使用に切り替えてから毛艶やお腹の調子が良くなったという声、お店でもよく聞きます"
    },
    {
        "category": "cond",
        "key": "digestive",
        "comment": "お腹がゆるい子は、フードの切り替えペースをゆっくりにするだけで落ち着くことも多いです"
    },
    {
        "category": "cond",
        "key": "lamb",
        "comment": "ラム肉は他のお肉でアレルギーが出た子にもよく選ばれている印象です"
    }
];
const brands = [
    {
        "key": "nutro",
        "name": "ニュートロ"
    },
    {
        "key": "supremo",
        "name": "ニュートロ"
    },
    {
        "key": "wildrecipe",
        "name": "ニュートロ"
    },
    {
        "key": "royal canin",
        "name": "ロイヤルカナン"
    },
    {
        "key": "sheba",
        "name": "シーバ"
    },
    {
        "key": "Medycoat",
        "name": "ペットライン"
    },
    {
        "key": "Medyfas",
        "name": "ペットライン"
    },
    {
        "key": "Select Balance",
        "name": "セレクトバランス"
    }
];
