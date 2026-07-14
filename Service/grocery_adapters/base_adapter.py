"""
BaseGroceryAdapter — מחלקת בסיס מופשטת (ABC) לקנייה אוטומטית באתרי קניות.

כל Adapter של רשת ספציפית יורש ממנה ומספק רק:
    - כתובות URL, סלקטורים, והתנהגות ספציפית לאתר
    - מימוש _scrape_results, _expand_product_card, _click_plus

הלוגיקה הגנרית (חיפוש, ניקוד, תזמור) נמצאת כולה כאן.
"""

from abc import ABC, abstractmethod
from typing import Optional

from playwright.sync_api import sync_playwright, Page


class BaseGroceryAdapter(ABC):
    """
    Abstract Base Class לכל מתאמי הקניות.
    יורשים צריכים להגדיר מאפיינים ואז לממש שלוש מתודות:
      - _scrape_results()
      - _expand_product_card()
      - _click_plus()
    """

    # ============================================================
    # מאפיינים שכל תת-מחלקה חייבת להגדיר
    # ============================================================

    @property
    @abstractmethod
    def STORE_NAME(self) -> str:
        """שם הרשת (לצורכי לוגים), לדוגמה 'רמי לוי'."""
        ...

    @property
    @abstractmethod
    def HOMEPAGE_URL(self) -> str:
        """כתובת דף הבית של האתר."""
        ...

    @property
    @abstractmethod
    def SEARCH_RESULTS_INDICATOR(self) -> str:
        """סלקטור טקסט שמאשר שתוצאות חיפוש נטענו, לדוגמה 'text=תוצאות חיפוש עבור'."""
        ...

    # ============================================================
    # מאפיינים עם ברירת מחדל — אפשר לדרוס בתת-מחלקה
    # ============================================================

    SEARCH_INPUT_SELECTOR: str = "input"

    ERROR_404_TEXT: str = "תחזירו אותי הביתה"

    CARD_PARENT_STEPS: int = 4

    # ============================================================
    # מתודות hook — לדריסה לפי צורך
    # ============================================================

    def get_homepage_wait_texts(self) -> list[str]:
        """
        רשימת מחרוזות שאם אחת מהן נמצאת ב-body, סימן שדף הבית נטען בהצלחה.
        """
        return []

    def close_popups_js(self) -> str:
        """
        מחזיר קוד JS שמסיר פופאפים ומודלים.
        תת-מחלקות יכולות לדרוס עם סלקטורים ספציפיים לאתר.
        """
        return """
        (() => {
            document.querySelectorAll(
                '[id*="BV_modal"], [id*="modal"], .modal-backdrop, .modal.show'
            ).forEach(el => el.remove());
            document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
            document.body.style.overflow = '';
            document.body.classList.remove('modal-open');
        })();
        """

    def get_popup_close_selectors(self) -> list[str]:
        """
        מחזיר רשימת סלקטורים לכפתורי סגירה של פופאפים.
        """
        return ["[aria-label='Close']", ".close", ".modal-header button", "button.close"]

    def get_card_anchor_selector(self) -> str:
        """
        סלקטור לעוגן שמזהה כל כרטיס מוצר בתוצאות חיפוש.
        """
        return "span.sr-only:has-text('פתח תיאור')"

    def find_plus_button(self, page: Page):
        """
        מחזיר locator לכפתור + (הוספה לסל).
        """
        return page.locator("button.plus").first

    # ============================================================
    # מחזור חיי הדפדפן
    # ============================================================

    def __init__(self, headless: bool = False):
        self._play = sync_playwright().start()
        self._browser = self._play.chromium.launch(headless=headless)
        self._page = self._browser.new_page()
        self._go_to_homepage()
        self._close_popups()

    @property
    def page(self) -> Page:
        return self._page

    def close(self):
        """סגירת הדפדפן וניקוי משאבים."""
        try:
            self._browser.close()
        except Exception:
            pass
        try:
            self._play.stop()
        except Exception:
            pass

    # ============================================================
    # עזרים גנריים (לא דורשים דריסה)
    # ============================================================

    def _get_body(self) -> str:
        try:
            return self._page.inner_text("body")[:1000]
        except Exception:
            return ""

    def _click_element_by_text(self, text: str) -> bool:
        """לוחץ על אלמנט לפי טקסט."""
        for sel in [f"a:has-text('{text}')", f"button:has-text('{text}')", f"text={text}"]:
            try:
                el = self._page.locator(sel).first
                if el.count() > 0 and el.is_visible():
                    el.click(timeout=3000)
                    return True
            except Exception:
                pass
        print(f"  element not clickable: {text}")
        return False

    def _ensure_not_404(self):
        body = self._get_body()
        if self.ERROR_404_TEXT in body:
            print(f"  404 detected, clicking '{self.ERROR_404_TEXT}'")
            self._click_element_by_text(self.ERROR_404_TEXT)
            self._page.wait_for_timeout(5000)

    # ============================================================
    # סגירת פופאפים
    # ============================================================

    def _close_popups(self):
        """
        אסטרטגיית סגירת פופאפים גנרית.
        1. JS להריגת מודלים
        2. Escape
        3. כפתורי סגירה
        4. הקלקה על רקע
        5. Escape שוב
        6. JS שוב
        """
        try:
            # JS — הורג מודלים
            self._page.evaluate(self.close_popups_js())
            self._page.wait_for_timeout(300)

            # Escape
            self._page.keyboard.press("Escape")
            self._page.wait_for_timeout(200)

            # כפתורי סגירה
            for sel in self.get_popup_close_selectors():
                btns = self._page.locator(sel)
                if btns.count() > 0:
                    for i in range(btns.count()):
                        try:
                            btn = btns.nth(i)
                            if btn.is_visible():
                                btn.click(timeout=2000)
                                self._page.wait_for_timeout(300)
                        except Exception:
                            pass

            # הקלקה על רקע
            self._page.mouse.click(10, 10)
            self._page.wait_for_timeout(200)

            # Escape שוב
            self._page.keyboard.press("Escape")
            self._page.wait_for_timeout(200)

            # JS שוב — וידוא ניקיון
            self._page.evaluate(self.close_popups_js())
            self._page.wait_for_timeout(300)
        except Exception:
            pass

    # ============================================================
    # ניווט
    # ============================================================

    def _go_to_homepage(self):
        self._page.goto(self.HOMEPAGE_URL, timeout=30000)
        self._page.wait_for_timeout(5000)

        for _ in range(3):
            body = self._get_body()
            if self.ERROR_404_TEXT in body:
                print(f"  404 page, clicking '{self.ERROR_404_TEXT}'")
                self._click_element_by_text(self.ERROR_404_TEXT)
                self._page.wait_for_timeout(5000)
                continue
            if "404" in body:
                print("  404, reloading")
                self._page.goto(self.HOMEPAGE_URL, timeout=30000)
                self._page.wait_for_timeout(5000)
                continue
            break

        body = self._get_body()
        wait_texts = self.get_homepage_wait_texts()
        if any(t in body for t in wait_texts):
            print(f"  homepage loaded: {self.STORE_NAME}")
        else:
            print(f"  unknown page")
            self._page.screenshot(path=f"debug_{self.STORE_NAME.lower().replace(' ', '_')}.png")

    # ============================================================
    # חיפוש
    # ============================================================

    def _do_search(self, query: str):
        """מקליד טקסט בתיבת החיפוש ולוחץ Enter."""
        self._ensure_not_404()
        self._close_popups()

        input_box = self._page.locator(self.SEARCH_INPUT_SELECTOR).first
        input_box.wait_for(state="visible", timeout=5000)
        input_box.click(force=True, timeout=5000)
        input_box.fill("")
        input_box.fill(query)
        input_box.press("Enter")
        self._page.wait_for_timeout(4000)

    def _wait_for_search_results(self) -> bool:
        """ממתין לאינדיקטור תוצאות חיפוש."""
        try:
            self._page.wait_for_selector(self.SEARCH_RESULTS_INDICATOR, timeout=10000)
            return True
        except Exception:
            return False

    # ============================================================
    # שלוש מתודות מופשטות — כל תת-מחלקה חייבת לממש
    # ============================================================

    @abstractmethod
    def _scrape_results(self) -> list[dict]:
        """
        אוסף את כל תוצאות החיפוש מהדף.
        כל תוצאה חייבת להיות dict עם המפתחות:
            name, brand, size, price, index, card_text
        """
        ...

    @abstractmethod
    def _expand_product_card(self, result_index: int) -> bool:
        """
        לוחץ על כרטיס המוצר כדי לחשוף את כפתור הפלוס.
        מחזיר True בהצלחה.
        """
        ...

    @abstractmethod
    def _click_plus(self, times: int = 1) -> bool:
        """
        לוחץ על כפתור + (הוספה לסל) N פעמים.
        מחזיר True בהצלחה.
        """
        ...

    # ============================================================
    # ניקוד והתאמה (לוגיקה טהורה — לא נוגעת בדפדפן)
    # ============================================================

    def _score_match(self, requested_name: str, result: dict) -> int:
        """
        ניקוד התאמה בין שם המוצר המבוקש לתוצאה.
        """
        score = 0
        req_lower = requested_name.lower()
        res_name = result["name"].lower()
        res_brand = result["brand"].lower()
        res_text = result["card_text"].lower()

        req_words = req_lower.split()

        for word in req_words:
            if len(word) <= 1:
                continue

            if word in res_name:
                score += 3
            elif word in res_brand:
                score += 1
            elif word in res_text:
                score += 1

        # בונוס: התאמת מותג
        for word in req_words:
            if len(word) > 1 and word in res_brand:
                score += 5
                break

        # בונוס: אחוז שומן תואם
        for pct in ["1%", "2%", "3%", "5%", "0%"]:
            if pct in req_lower and pct in res_name:
                score += 4
                break

        # קנס: מותג שונה ממה שהמשתמש ביקש
        brand_in_req = None
        known_brands = ["תנובה", "טרה", "יטבתה", "שטראוס", "טרה", "באדי", "תלמה",
                        "אסם", "קוקה", "פפסי", "נסטלה", "יולו", "סימילאק"]
        for b in known_brands:
            if b in req_lower:
                brand_in_req = b
                break

        if brand_in_req and brand_in_req not in res_brand:
            score -= 5

        # קנס: קטגוריה שונה לגמרי
        non_food = ["סימילאק", "יולו", "באדי"]
        is_req_food = not any(nf in req_lower for nf in non_food)
        is_res_non_food = any(nf in res_name for nf in non_food)
        if is_req_food and is_res_non_food:
            score -= 10

        return score

    def _pick_best(self, results: list[dict], requested_name: str) -> Optional[dict]:
        """
        בוחר את התוצאה הטובה ביותר מתוך הרשימה.
        מחזיר dict או None.
        """
        if not results:
            return None

        scored = []
        for r in results:
            s = self._score_match(requested_name, r)
            scored.append((s, r))
            print(f"  [{s:>3}] {r['name']} | {r['brand']} | {r['price']}")

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best = scored[0]

        if best_score < 3:
            print(f"  no good match (score {best_score})")
            return None

        print(f"  best: {best['name']} | {best['brand']} | {best['price']} (score {best_score})")
        return best

    # ============================================================
    # תזמור — תהליך הקנייה המלא
    # ============================================================

    def process_product(
        self,
        barcode: Optional[str] = None,
        name: Optional[str] = None,
        quantity: int = 1,
        kg_per_click: Optional[float] = None,
    ) -> bool:
        """
        מוסיף מוצר לעגלה.
        - quantity: כמה יחידות/ק"ג להוסיף
        - kg_per_click: כמה ק"ג כל לחיצה (ברירת מחדל 1 = יחידות).
          לפירות/ירקות — 0.5 (חצי קילו ללחיצה)
        """
        clicks = quantity
        if kg_per_click is not None and kg_per_click > 0:
            clicks = max(1, round(quantity / kg_per_click))

        print(f"\n{'='*50}")
        print(f"Product: barcode={barcode} name={name} qty={quantity} ({clicks} clicks)")

        if barcode:
            return self._process_with_barcode(barcode, name, quantity, clicks)
        else:
            return self._process_by_name(name, clicks)

    def process_barcode(self, barcode: str) -> bool:
        """Legacy wrapper — חיפוש לפי ברקוד בלבד."""
        return self.process_product(barcode=barcode, name=None, quantity=1)

    def _process_with_barcode(
        self, barcode: str, name: Optional[str], quantity: int, clicks: int
    ) -> bool:
        """חיפוש לפי ברקוד, אימות מול שם, נפילה לחיפוש לפי שם."""
        print(f"  searching by barcode: {barcode}")
        try:
            self._do_search(barcode)
        except Exception as e:
            print(f"  barcode search failed: {e}")
            if name:
                print("  falling back to name search...")
                return self._process_by_name(name, clicks)
            return False

        self._ensure_not_404()

        has_results = self._wait_for_search_results()
        if not has_results:
            print("  no results for barcode — trying name fallback")
            if name:
                return self._process_by_name(name, clicks)
            return False

        self._close_popups()

        results = self._scrape_results()

        if name and results:
            best = self._pick_best(results, name)
            if best:
                print(f"  opening product #{best['index']}: {best['name']}")
                self._expand_product_card(best["index"])
            else:
                print("  no good match, trying name search")
                return self._process_by_name(name, clicks)
        elif results:
            print(f"  opening first product: {results[0]['name']}")
            self._expand_product_card(0)
        else:
            print("  no results found")
            if name:
                return self._process_by_name(name, clicks)
            return False

        print(f"  adding {clicks} clicks")
        return self._click_plus(times=clicks)

    def _process_by_name(self, name: str, clicks: int) -> bool:
        """חיפוש לפי שם בלבד (חלופה / נתיב ראשי)."""
        print(f"  searching by name: {name}")
        try:
            self._do_search(name)
        except Exception as e:
            print(f"  name search failed: {e}")
            return False

        self._ensure_not_404()
        if not self._wait_for_search_results():
            print("  no results for name")
            return False

        self._close_popups()

        results = self._scrape_results()
        print(f"  found {len(results)} results")

        if not results:
            print("  no results found")
            return False

        best = self._pick_best(results, name)
        if not best:
            print("  no good match found")
            return False

        print(f"  opening product #{best['index']}: {best['name']}")
        self._expand_product_card(best["index"])

        print(f"  adding {clicks} clicks")
        return self._click_plus(times=clicks)
