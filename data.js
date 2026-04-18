const productData = [
    { 
        name: "ロイヤルカナン ダーマコンフォート (皮膚・被毛・涙やけ・アレルギー配慮)", 
        brand: "Royal Canin", 
        tags: ["dog", "adult", "skin", "tear"], 
        desc: "皮膚が敏感な小型犬用。健康な皮膚と被毛を維持するための特別な栄養バランス。",
        img: "https://unsplash.com", 
        amz: "#", rak: "#", yah: "#" 
    },
    { 
        name: "シュプレモ 湖畔のレシピ ラム (穀物不使用・成犬用・アレルギー・涙やけケア)", 
        brand: "Supremo", 
        tags: ["dog", "adult", "gf", "lamb", "tear"], 
        desc: "高品質なラム肉を第一主原料に使用。穀物不使用で消化にも優しく、涙やけが気になる子にも。",
        img: "https://unsplash.com", 
        amz: "#", rak: "#", yah: "#" 
    },
    { 
        name: "ロイヤルカナン ユリナリー ケア (猫用・尿路健康・結石予防・腎臓ケア)", 
        brand: "Royal Canin", 
        tags: ["cat", "adult", "kidney"], 
        desc: "健康な尿を維持したい猫用。ミネラルバランスを調整し、尿路結石の形成を抑制します。",
        img: "https://unsplash.com", 
        amz: "#", rak: "#", yah: "#" 
    }
];
  const productData = [
    // --- ニュートロ 犬用：ナチュラル チョイス（サイズ・年齢・悩み別） ---
    { name: "ナチュラル チョイス 子犬用 超小型犬〜中型犬 チキン＆玄米", brand: "Nutro", tags: ["dog", "puppy", "growth", "chicken"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ナチュラル チョイス 成犬用 超小型犬用 チキン＆玄米", brand: "Nutro", tags: ["dog", "adult", "small", "chicken"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ナチュラル チョイス 成犬用 小型犬用 ラム＆玄米", brand: "Nutro", tags: ["dog", "adult", "small", "lamb", "tear", "skin"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ナチュラル チョイス 減量用 全犬種用 成犬用 ラム＆玄米", brand: "Nutro", tags: ["dog", "adult", "diet", "lamb"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ナチュラル チョイス 避妊・去勢犬用 超小型犬〜小型犬 成犬用", brand: "Nutro", tags: ["dog", "adult", "diet", "tear"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ナチュラル チョイス エイジングケア 超小型犬用 チキン＆玄米", brand: "Nutro", tags: ["dog", "senior", "small", "chicken"], img: "https://unsplash.com", amz: "#", rak: "#" },

    // --- ニュートロ 犬用：ワイルド レシピ（穀物不使用・高タンパク） ---
    { name: "ワイルド レシピ 子犬用 ターキー", brand: "Nutro", tags: ["dog", "puppy", "gf", "turkey"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ワイルド レシピ 成犬用 鹿肉 (超小型〜小型犬)", brand: "Nutro", tags: ["dog", "adult", "gf", "venison", "tear"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ワイルド レシピ 成犬用 サーモン", brand: "Nutro", tags: ["dog", "adult", "gf", "fish", "skin"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ワイルド レシピ 超小型犬〜小型犬用 エイジングケア ターキー", brand: "Nutro", tags: ["dog", "senior", "gf", "turkey"], img: "https://unsplash.com", amz: "#", rak: "#" },

    // --- ニュートロ 猫用：ナチュラル チョイス ---
    { name: "ナチュラル チョイス 室内猫用 アダルト チキン", brand: "Nutro", tags: ["cat", "adult", "diet", "chicken"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ナチュラル チョイス 食にこだわる猫用 アダルト チキン", brand: "Nutro", tags: ["cat", "adult", "appetite", "chicken"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ナチュラル チョイス 毛玉トータルケア アダルト チキン", brand: "Nutro", tags: ["cat", "adult", "hairball", "chicken"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ナチュラル チョイス 避妊・去勢猫用 アダルト 白身魚", brand: "Nutro", tags: ["cat", "adult", "diet", "fish"], img: "https://unsplash.com", amz: "#", rak: "#" },

    // --- ニュートロ 猫用：ワイルド レシピ ---
    { name: "ワイルド レシピ アダルト チキン (猫用)", brand: "Nutro", tags: ["cat", "adult", "gf", "chicken", "appetite"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ワイルド レシピ エイジングケア ターキー (猫用)", brand: "Nutro", tags: ["cat", "senior", "gf", "turkey"], img: "https://unsplash.com", amz: "#", rak: "#" },

    // --- ニュートロ 犬用：追加分 ---
    { name: "ナチュラル チョイス 子犬用 大型犬用 チキン＆玄米", brand: "Nutro", tags: ["dog", "puppy", "growth", "chicken"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ナチュラル チョイス 成犬用 中型犬〜大型犬用 ラム＆玄米", brand: "Nutro", tags: ["dog", "adult", "lamb", "skin"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ナチュラル チョイス 成犬用 超小型犬〜小型犬用 フィッシュ＆ポテト", brand: "Nutro", tags: ["dog", "adult", "fish", "skin", "tear"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ワイルド レシピ 成犬用 ビーフ (超小型〜小型犬)", brand: "Nutro", tags: ["dog", "adult", "gf", "beef"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ワイルド レシピ 成犬用 白身魚 (超小型〜小型犬)", brand: "Nutro", tags: ["dog", "adult", "gf", "fish", "skin"], img: "https://unsplash.com", amz: "#", rak: "#" },

    // --- ニュートロ 猫用：追加分 ---
    { name: "ナチュラル チョイス キトン チキン (子猫用)", brand: "Nutro", tags: ["cat", "puppy", "growth", "chicken"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ナチュラル チョイス 減量用 アダルト チキン", brand: "Nutro", tags: ["cat", "adult", "diet", "chicken"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ナチュラル チョイス エイジングケア 7歳以上 チキン", brand: "Nutro", tags: ["cat", "senior", "chicken"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ワイルド レシピ アダルト ターキー (猫用)", brand: "Nutro", tags: ["cat", "adult", "gf", "turkey"], img: "https://unsplash.com", amz: "#", rak: "#" },

 　　// --- シュプレモ 犬用：基本ライン（全ライフステージ） ---
    { name: "シュプレモ 子犬用 (全犬種用)", brand: "Supremo", tags: ["dog", "puppy", "growth", "tear"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "シュプレモ 超小型犬用 成犬用", brand: "Supremo", tags: ["dog", "adult", "small", "tear"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "シュプレモ 小型犬用 成犬用", brand: "Supremo", tags: ["dog", "adult", "small", "tear"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "シュプレモ 成犬用 (中型犬〜大型犬用)", brand: "Supremo", tags: ["dog", "adult", "medium"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "シュプレモ 体重管理用 (全犬種用)", brand: "Supremo", tags: ["dog", "adult", "diet"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "シュプレモ 超小型犬〜小型犬用 エイジングケア", brand: "Supremo", tags: ["dog", "senior", "joint", "small", "tear"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "シュプレモ エイジングケア (中型犬〜大型犬用)", brand: "Supremo", tags: ["dog", "senior", "joint", "medium"], img: "https://unsplash.com", amz: "#", rak: "#" },

    // --- シュプレモ 犬用：レシピシリーズ（穀物不使用・味別） ---
    { name: "シュプレモ 湖畔のレシピ (ラム/穀物不使用)", brand: "Supremo", tags: ["dog", "adult", "gf", "lamb", "tear"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "シュプレモ 地中海のレシピ (ラム/鹿肉/穀物不使用)", brand: "Supremo", tags: ["dog", "adult", "gf", "venison", "lamb"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "シュプレモ 牧場のレシピ (ビーフ/穀物不使用)", brand: "Supremo", tags: ["dog", "adult", "gf", "beef"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "シュプレモ 草原のレシピ (チキン/穀物不使用)", brand: "Supremo", tags: ["dog", "adult", "gf", "chicken"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "シュプレモ 森のレシピ (ターキー/穀物不使用)", brand: "Supremo", tags: ["dog", "adult", "gf", "turkey"], img: "https://unsplash.com", amz: "#", rak: "#" },

    // --- シュプレモ 猫用 ---
    { name: "シュプレモ キトン (子猫用)", brand: "Supremo", tags: ["cat", "puppy", "growth"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "シュプレモ アダルト チキン (成猫用)", brand: "Supremo", tags: ["cat", "adult", "chicken"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "シュプレモ アダルト サーモン (成猫用)", brand: "Supremo", tags: ["cat", "adult", "fish"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "シュプレモ 白身魚＆サーモン (穀物不使用/成猫用)", brand: "Supremo", tags: ["cat", "adult", "gf", "fish", "appetite"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "シュプレモ エイジングケア (シニア猫用)", brand: "Supremo", tags: ["cat", "senior", "joint"], img: "https://unsplash.com", amz: "#", rak: "#" },

    // --- ロイヤルカナン 犬用：サイズ・年齢別 (SHN) ---
    { name: "エクストラスモール パピー (超小型犬 子犬用)", brand: "Royal Canin", tags: ["dog", "puppy", "growth", "small"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "エクストラスモール アダルト (超小型犬 成犬用)", brand: "Royal Canin", tags: ["dog", "adult", "small"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "エクストラスモール エイジング 12+ (超小型犬 高齢犬用)", brand: "Royal Canin", tags: ["dog", "senior", "small", "joint"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ミニ パピー (小型犬 子犬用)", brand: "Royal Canin", tags: ["dog", "puppy", "growth", "small"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ミニ アダルト (小型犬 成犬用)", brand: "Royal Canin", tags: ["dog", "adult", "small", "tear"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ミニ インドア アダルト (室内で生活する小型犬用)", brand: "Royal Canin", tags: ["dog", "adult", "diet", "small"], img: "https://unsplash.com", amz: "#", rak: "#" },

    // --- ロイヤルカナン 犬用：お悩み別 (CCN) ---
    { name: "ステアライズド (避妊・去勢犬用)", brand: "Royal Canin", tags: ["dog", "adult", "diet", "small"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ダーマコンフォート (皮膚が敏感な犬用)", brand: "Royal Canin", tags: ["dog", "adult", "skin", "tear", "small"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ダイジェスティブ ケア (胃腸が弱い犬用)", brand: "Royal Canin", tags: ["dog", "adult", "stomach", "small"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ジョイント ケア (関節が気になる犬用)", brand: "Royal Canin", tags: ["dog", "adult", "joint", "senior"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ユリナリー ケア (健康な尿を維持したい犬用)", brand: "Royal Canin", tags: ["dog", "adult", "kidney", "small"], img: "https://unsplash.com", amz: "#", rak: "#" },

    // --- ロイヤルカナン 猫用：ライフステージ別 (FHN) ---
    { name: "マザー＆ベビーキャット (成長前期の子猫用)", brand: "Royal Canin", tags: ["cat", "puppy", "growth"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "キトン (成長後期の子猫用)", brand: "Royal Canin", tags: ["cat", "puppy", "growth"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "インドア (室内で生活する成猫用)", brand: "Royal Canin", tags: ["cat", "adult", "diet"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "フィット (標準的な成猫用)", brand: "Royal Canin", tags: ["cat", "adult", "appetite"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "エイジング 12+ (12歳以上の老齢猫用)", brand: "Royal Canin", tags: ["cat", "senior", "kidney", "joint"], img: "https://unsplash.com", amz: "#", rak: "#" },

    // --- ロイヤルカナン 猫用：お悩み別 (FCN) ---
    { name: "ヘアボール ケア (毛玉が気になる猫用)", brand: "Royal Canin", tags: ["cat", "adult", "hairball"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ライト ウェイト ケア (肥満気味の猫用)", brand: "Royal Canin", tags: ["cat", "adult", "diet"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "ユリナリー ケア (健康な尿を維持したい猫用)", brand: "Royal Canin", tags: ["cat", "adult", "kidney"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "オーラル ケア (歯垢・歯石が気になる猫用)", brand: "Royal Canin", tags: ["cat", "adult", "tooth"], img: "https://unsplash.com", amz: "#", rak: "#" },
    
    // --- ロイヤルカナン 犬用：お悩み別 (CCN) 補完分 ---
    { name: "CCN ミニ ダイジェスティブ ケア (おなかの健康維持)", brand: "Royal Canin", tags: ["dog", "adult", "small", "stomach"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "CCN ミニ デンタル ケア (歯垢・歯石が気になる犬用)", brand: "Royal Canin", tags: ["dog", "adult", "small", "tooth"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "CCN ミニ エクシジェント (食欲にムラがある犬用)", brand: "Royal Canin", tags: ["dog", "adult", "small", "appetite"], img: "https://unsplash.com", amz: "#", rak: "#" },

    // --- ロイヤルカナン 猫用：お悩み別 (FCN) 補完分 ---
    { name: "FCN ダイジェスティブ ケア (胃腸が弱い猫用)", brand: "Royal Canin", tags: ["cat", "adult", "stomach"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "FCN オーラル ケア (歯の健康維持)", brand: "Royal Canin", tags: ["cat", "adult", "tooth"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "FCN ヘア＆スキン ケア (皮膚・被毛の健康維持)", brand: "Royal Canin", tags: ["cat", "adult", "skin"], img: "https://unsplash.com", amz: "#", rak: "#" },
    { name: "FCN アペタイト コントロール (おねだりの多い猫用)", brand: "Royal Canin", tags: ["cat", "adult", "diet", "appetite"], img: "https://unsplash.com", amz: "#", rak: "#" }
