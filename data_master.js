const siteVersion = '20260831081616';
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
const FORMSPREE_FORM_ID = "mdenyvoz";
const popular_searches = [
    {
        "word": "心臓"
    },
    {
        "word": "納豆菌"
    },
    {
        "word": "メディコート"
    }
];
const comments = [
    {
        "category": "animal",
        "key": "dog",
        "comment": "フードを見直す際はいきなり変えるのではなく、少しずつ量を変えていくのがおすすめです。まずはサンプルや小袋で試しましょう"
    },
    {
        "category": "animal",
        "key": "cat",
        "comment": "フードを見直す際はいきなり変えるのではなく、少しずつ量を変えていくのがおすすめです。まずはサンプルや小袋で試しましょう"
    },
    {
        "category": "cond",
        "key": "tear",
        "comment": "涙やけの相談は本当に多いです。フードだけでなく食器の材質が原因のこともあるので、両方見直す方が多いですよ"
    },
    {
        "category": "cond",
        "key": "tear",
        "comment": "涙やけの子は、納豆菌や乳酸菌などの善玉菌が入ったフードだと改善傾向がある印象です。おやつで足す方法もありますが、あげすぎには注意してください"
    },
    {
        "category": "cond",
        "key": "diet",
        "comment": "体重管理は『量を減らす』より『満腹感が続くフード』に変える方が、ストレスなく続けられている子が多い印象です"
    },
    {
        "category": "cond",
        "key": "diet",
        "comment": "もっと欲しがる子には、量を減らすより食物繊維多めのフードがおすすめです。満腹感が続きやすく、ストレスなく続けられる印象です"
    },
    {
        "category": "cond",
        "key": "kidney",
        "comment": "腎臓・尿路のケアは早めに始めるほど選択肢が広がるので、気になったタイミングで一度見直すのがおすすめです"
    },
    {
        "category": "cond",
        "key": "kidney",
        "comment": "腎臓・尿路のケアでは、塩分の少ないフードがおすすめです。ワンちゃんは心臓の相談も重なることがあるので、持病がある場合は必ず獣医師に確認してください"
    },
    {
        "category": "cond",
        "key": "skin",
        "comment": "皮膚が気になる子は、フードを変えてしばらく様子を見ると毛艶が落ち着いてくることがあります。合わないと感じたら、早めにやめましょう"
    },
    {
        "category": "cond",
        "key": "joint",
        "comment": "関節ケアはシニア期に相談が増えますが、気になり始めたタイミングで切り替えるのも選択の一つです"
    },
    {
        "category": "cond",
        "key": "tooth",
        "comment": "歯の健康は毎日のケアが大変という方が多いので、フードの硬さで工夫するのも一つの方法です。歯磨きは、小さいうちから口の中に手を入れられてもいいようにトレーニングしておきましょう"
    },
    {
        "category": "cond",
        "key": "appetite",
        "comment": "食いつきが悪い時は、カリカリをお湯でふやかすと匂いが出て食べてくれることがあります。トッピングは乗せるより混ぜる方が、うまくいく印象です"
    },
    {
        "category": "cond",
        "key": "appetite",
        "comment": "食いつきが良くない子には、匂いがきつめのフードや、タンパク質多めのタイプを試すと食べてくれることがあります。まずは少量から。腎臓など持病がある場合は、あげる前に獣医師へ確認してください"
    },
    {
        "category": "cond",
        "key": "gf",
        "comment": "穀物不使用に変えて、毛艶やお腹の調子が楽になったという声もあります。合う・合わないが分かれるので、まずは様子を見ながらの切り替えがおすすめです"
    },
    {
        "category": "cond",
        "key": "digestive",
        "comment": "お腹がゆるい子は、善玉菌配合のフードで調子を整えていきましょう。食物繊維多めのフードでも改善した話を聞いたことがありますが、いきなり切り替えるのではなく少しずつが良いです"
    },
    {
        "category": "cond",
        "key": "lamb",
        "comment": "ラム肉は他のお肉でアレルギーが出た子にまず選ばれている印象ですが、最近は、鹿や魚なども展開してるので視野に入れておくといいですよ"
    },
    {
        "category": "keyword",
        "key": "心臓",
        "comment": "心臓が気になる子には、塩分（ナトリウム）が調整されたフードを選ぶ方が多いです。持病がある場合は、必ず獣医師の指示に沿ったフード選びをおすすめします"
    },
    {
        "category": "keyword",
        "key": "心臓",
        "comment": "心臓病で食べむらがある子には、おやつやパウチを上に乗せるよりフードに混ぜると食べてくれることがあります。塩気の少ないもの、できれば心臓・腎臓用を選び、あげる前に必ず獣医師へ確認してください"
    },
    {
        "category": "keyword",
        "key": "納豆菌",
        "comment": "納豆菌などの乳酸菌・善玉菌が配合されたフードは、お腹の調子を整えたい子によく選ばれている印象です"
    },
    {
        "category": "keyword",
        "key": "納豆菌",
        "comment": "納豆菌などの善玉菌は、お腹だけでなく涙やけの相談でもよく提案しています。おやつで補う場合は、あげすぎに注意してください"
    },
    {
        "category": "keyword",
        "key": "避妊",
        "comment": "避妊・去勢した子は、まず様子を見て、体重が増えてきたらフード変更を検討するのがおすすめです。体重管理用でも代用できますし、もっと欲しがるなら食物繊維多めのフードが向いています"
    },
    {
        "category": "keyword",
        "key": "去勢",
        "comment": "避妊・去勢した子は、まず様子を見て、体重が増えてきたらフード変更を検討するのがおすすめです。体重管理用でも代用できますし、もっと欲しがるなら食物繊維多めのフードが向いています"
    },
    {
        "category": "keyword",
        "key": "食べむら",
        "comment": "食べむらがある子には、パウチやおやつをフードに混ぜたり、カリカリをお湯でふやかして匂いを出したりすると食いつきが戻ることがあります。持病がある場合は、塩分の少ないものを選んで獣医師に確認してからあげてください"
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
    },
    {
        "key": "Frecious",
        "name": "ユニ・チャーム"
    }
];
