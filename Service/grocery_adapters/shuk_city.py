"""
ShukCityAdapter — קנייה אוטומטית באתר שוק סיטי.

⚠️ STUB — יש למלא את מימוש _scrape_results, _expand_product_card, _click_plus
    לאחר בדיקת מבנה ה-DOM של האתר.
"""

from Service.grocery_adapters.base_adapter import BaseGroceryAdapter


class ShukCityAdapter(BaseGroceryAdapter):

    # ============================================================
    # תצורה ספציפית לשוק סיטי
    # ============================================================

    @property
    def STORE_NAME(self) -> str:
        return "שוק סיטי"

    @property
    def HOMEPAGE_URL(self) -> str:
        return "https://www.shukcity.co.il"

    @property
    def SEARCH_RESULTS_INDICATOR(self) -> str:
        # TBD — ייתכן שצריך להתאים אחרי בדיקת האתר
        return "text=תוצאות חיפוש"

    SEARCH_INPUT_SELECTOR: str = "input"
    ERROR_404_TEXT: str = "תחזירו אותי הביתה"  # TBD
    CARD_PARENT_STEPS: int = 4  # TBD

    # ============================================================
    # hooks
    # ============================================================

    def get_homepage_wait_texts(self) -> list[str]:
        return ["שוק סיטי", "סל"]

    def close_popups_js(self) -> str:
        # TBD — להתאים סלקטורים ספציפיים לשוק סיטי
        return super().close_popups_js()

    def get_card_anchor_selector(self) -> str:
        # TBD — לבדוק איך נראה כרטיס מוצר בתוצאות חיפוש
        return "span.sr-only:has-text('פתח תיאור')"

    # ============================================================
    # STUBS — דורשים מימוש
    # ============================================================

    def _scrape_results(self) -> list[dict]:
        """
        TODO: לממש גרידת תוצאות חיפוש משוק סיטי.

        יש לבדוק:
        1. איך נראה כרטיס מוצר בתוצאות חיפוש
        2. איפה נמצאים: שם, מותג, מחיר
        3. אילו סלקטורים מזהים כל כרטיס
        """
        raise NotImplementedError(
            "ShukCity scraping not yet implemented. "
            "Please inspect the DOM structure of search results at "
            "https://www.shukcity.co.il and implement _scrape_results()."
        )

    def _expand_product_card(self, result_index: int) -> bool:
        """
        TODO: לממש פתיחת כרטיס מוצר בשוק סיטי.

        יש לבדוק:
        1. איך לוחצים על כרטיס מוצר
        2. האם צריך לגלול קודם
        3. איך הכרטיס מגיב (נפתח? מתחת?)
        """
        raise NotImplementedError(
            "ShukCity card expansion not yet implemented."
        )

    def _click_plus(self, times: int = 1) -> bool:
        """
        TODO: לממש לחיצה על כפתור + בשוק סיטי.

        יש לבדוק:
        1. איזה סלקטור יש לכפתור הפלוס
        2. האם הוא מופיע רק אחרי פתיחת כרטיס
        """
        raise NotImplementedError(
            "ShukCity plus button not yet implemented."
        )
