"""画像フィルター（年齢・ショップURL）の単体テスト"""
import unittest

from csv_to_json import (
    _extract_age_numbers,
    _get_api_item_text,
    _is_api_item_valid,
    _keyword_matches_text,
    _score_image_url,
    _text_has_exact_age,
)


class TestAgeExtraction(unittest.TestCase):
    def test_distinguish_1_and_11(self):
        self.assertEqual(_extract_age_numbers("1歳から"), {"1"})
        self.assertEqual(_extract_age_numbers("11歳から"), {"11"})
        self.assertEqual(_extract_age_numbers("子いぬ り乳〜1歳"), {"1"})

    def test_exact_age_boundary(self):
        self.assertTrue(_text_has_exact_age("1歳から", "1"))
        self.assertFalse(_text_has_exact_age("11歳から", "1"))
        self.assertTrue(_text_has_exact_age("11歳から", "11"))

    def test_keyword_no_false_positive(self):
        self.assertFalse(_keyword_matches_text("1歳から", "魚＆えんどう豆 11歳から"))
        self.assertTrue(_keyword_matches_text("1歳から", "魚＆えんどう豆 1歳から"))


class TestApiItemValidation(unittest.TestCase):
    product_1 = "メディコートアドバンス アレルゲンカット 魚＆えんどう豆たんぱく 1歳から"
    product_nyoseki = "メディコートアドバンス 尿石ケア pHサポート 1歳から"
    brand = "medycoat"
    size_3kg = "3kg"
    size_2kg = "2kg"

    def test_reject_11_age_in_api_title(self):
        api = "メディコート MCA-18 魚＆えんどう豆 11歳から 2kg"
        self.assertFalse(_is_api_item_valid(api, self.product_1, self.brand, self.size_2kg))

    def test_reject_box_set_without_age(self):
        api = "【クーポン付】 メディコートアドバンス アレルゲンカット 魚＆えんどう豆 6kg (500g×12袋) ペットライン"
        self.assertFalse(_is_api_item_valid(api, self.product_1, self.brand, self.size_2kg))

    def test_reject_nyoseki_box_set_with_subtext(self):
        """尿石ケア 1歳3kg に 11歳6kg箱セット（サブ文字列一致のみ）を拒否"""
        api = "メディコートアドバンス 尿石ケア pHサポート 11歳から 6kg (500g×12袋)"
        self.assertFalse(_is_api_item_valid(api, self.product_nyoseki, self.brand, self.size_3kg))

    def test_reject_nyoseki_wrong_kg_only(self):
        api = "メディコートアドバンス 尿石ケア pHサポート 1歳から 6kg (500g×12袋)"
        self.assertFalse(_is_api_item_valid(api, self.product_nyoseki, self.brand, self.size_3kg))

    def test_reject_age_in_caption_only(self):
        item = {
            "itemName": "メディコートアドバンス 尿石ケア pHサポート 6kg",
            "itemCaption": "11歳から 500g×12袋",
        }
        api = _get_api_item_text(item)
        self.assertFalse(_is_api_item_valid(api, self.product_nyoseki, self.brand, self.size_3kg))

    def test_accept_matching_age(self):
        api = "メディコートアドバンス アレルゲンカット 魚＆えんどう豆 1歳から 2kg"
        self.assertTrue(_is_api_item_valid(api, self.product_1, self.brand, self.size_2kg))


class TestUrlScoring(unittest.TestCase):
    product_1 = "メディコートアドバンス アレルゲンカット 魚＆えんどう豆たんぱく 1歳から"

    def test_exclude_pet_oukoku_shop(self):
        url = "https://thumbnail.image.rakuten.co.jp/@0_mall/pet-oukoku/cabinet/item/mca18.jpg"
        self.assertLess(_score_image_url(url, self.product_1), -5)

    def test_penalize_non_jan_cabinet(self):
        url = "https://thumbnail.image.rakuten.co.jp/@0_mall/rakuten24/cabinet/item/mca24.jpg"
        self.assertLess(_score_image_url(url, self.product_1), -5)

    def test_jan_cabinet_still_scores_well(self):
        url = "https://thumbnail.image.rakuten.co.jp/@0_mall/rakuten24/cabinet/jan/4902418002385.jpg"
        self.assertGreater(_score_image_url(url, self.product_1), 0)


if __name__ == "__main__":
    unittest.main()
