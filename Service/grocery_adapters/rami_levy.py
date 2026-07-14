"""
RamiLevyAdapter — קנייה אוטומטית באתר רמי לוי.
"""

from Service.grocery_adapters.base_adapter import BaseGroceryAdapter


class RamiLevyAdapter(BaseGroceryAdapter):

    # ============================================================
    # תצורה ספציפית לרמי לוי
    # ============================================================

    @property
    def STORE_NAME(self) -> str:
        return "רמי לוי"

    @property
    def HOMEPAGE_URL(self) -> str:
        return "https://www.rami-levy.co.il/he/online"

    @property
    def SEARCH_RESULTS_INDICATOR(self) -> str:
        return "text=תוצאות חיפוש עבור"

    SEARCH_INPUT_SELECTOR: str = "input"
    ERROR_404_TEXT: str = "תחזירו אותי הביתה"
    CARD_PARENT_STEPS: int = 4

    # ============================================================
    # hooks
    # ============================================================

    def get_homepage_wait_texts(self) -> list[str]:
        return ["רמי לוי", "התחברות", "סל"]

    # ============================================================
    # גרידת תוצאות חיפוש
    # ============================================================

    def _scrape_results(self) -> list[dict]:
        """
        אוסף את כל תוצאות החיפוש מהדף.
        כל תוצאה נמצאת בתוך div שמכיל span.sr-only עם 'פתח תיאור'.
        """
        results = []

        sr_spans = self._page.locator("span.sr-only:has-text('פתח תיאור')")
        count = sr_spans.count()

        for i in range(count):
            try:
                span = sr_spans.nth(i)

                # מטפסים CARD_PARENT_STEPS רמות למעלה — ה-div של כרטיס המוצר
                card = span
                for _ in range(self.CARD_PARENT_STEPS):
                    card = card.locator("..")
                text = card.inner_text()

                if not text or "מחיר" not in text:
                    continue

                lines = [l.strip() for l in text.split("\n") if l.strip()]

                # ניקוי: sr-only, מחירים, ושאר רעש
                clean = [l for l in lines
                         if "פתח תיאור" not in l
                         and not l.startswith("₪")
                         and "מחיר" not in l
                         and "שקלים" not in l
                         and "ליח'" not in l
                         and not l.endswith("גרם")
                         and not l.endswith("מל")
                         and "ל-100" not in l]

                # מציאת שם מוצר — השורה הארוכה ביותר עם אותיות
                product_name = ""
                brand = ""
                size = ""

                for line in clean:
                    if "|" in line and not product_name:
                        parts = line.split("|")
                        brand = parts[0].strip()
                        size = parts[1].strip() if len(parts) > 1 else ""
                        continue

                    if any(c.isalpha() or c in "אבגדהוזחטיכלמנסעפצקרשת" for c in line) and len(line) > 3:
                        if not product_name or len(line) > len(product_name):
                            product_name = line

                # Fallback: brand|size אחרי השם
                if not brand:
                    for line in lines:
                        if "|" in line:
                            parts = line.split("|")
                            brand = parts[0].strip()
                            size = parts[1].strip() if len(parts) > 1 else ""
                            break

                # מחיר
                price = ""
                for line in lines:
                    if "₪" in line and any(c.isdigit() for c in line):
                        price = line.strip()
                        break

                # סינון תוצאות זבל
                if "פתח תיאור" in product_name:
                    continue
                if len(product_name) < 3:
                    continue

                skip_promo = False
                if "ההטבה" in product_name:
                    skip_promo = True
                if product_name and product_name.split():
                    first_word = product_name.split()[0]
                    if "ב-" in first_word:
                        skip_promo = True
                if skip_promo:
                    continue

                if product_name.replace(" ", "").replace("/", "").replace("-", "").replace(".", "").replace("ב", "").isdigit():
                    continue

                results.append({
                    "name": product_name,
                    "brand": brand,
                    "size": size,
                    "price": price,
                    "index": i,
                    "card_text": text,
                })

            except Exception:
                continue

        return results

    # ============================================================
    # פתיחת כרטיס מוצר
    # ============================================================

    def _expand_product_card(self, result_index: int) -> bool:
        """
        לוחץ על כרטיס המוצר לפי האינדקס כדי לחשוף את כפתור הפלוס.
        """
        sr_spans = self._page.locator(self.get_card_anchor_selector())
        if result_index >= sr_spans.count():
            print(f"  index {result_index} out of range")
            return False

        span = sr_spans.nth(result_index)
        card = span
        for _ in range(self.CARD_PARENT_STEPS):
            card = card.locator("..")

        card.click()
        self._page.wait_for_timeout(1500)
        return True

    # ============================================================
    # לחיצה על כפתור +
    # ============================================================

    def _click_plus(self, times: int = 1) -> bool:
        """לוחץ על כפתור + (פלוס) N פעמים."""
        for _ in range(times):
            plus_btn = self.find_plus_button(self._page)
            if plus_btn.count() == 0:
                print("  no plus button found")
                return False
            plus_btn.evaluate("el => el.click()")
            self._page.wait_for_timeout(600)
        return True
