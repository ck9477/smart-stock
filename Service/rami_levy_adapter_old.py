from playwright.sync_api import sync_playwright


class RamiLevyAdapter:

   def __init__(self):
    self.play = sync_playwright().start()

    self.context = self.play.chromium.launch_persistent_context(
    user_data_dir=r"C:\PlaywrightProfile",
    executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    headless=False,
)
    print(self.context.pages)
    self.page = self.context.pages[0]
    print(self.page.url)

    self.page = self.context.new_page()

    self._go_to_homepage()

    def close(self):
        try:
            self.context.close()
        except Exception:
            pass

        try:
            self.play.stop()
        except Exception:
            pass

    # ============================================================
    # ניווט ועזרים
    # ============================================================
    def _go_to_homepage(self):
        self.page.goto("https://www.rami-levy.co.il/he")
        self.page.wait_for_timeout(10000)


        for _ in range(3):
            body = self._get_body()
            if "תחזירו אותי הביתה" in body:
                print("⚠️ דף 404, לוחץ על 'תחזירו אותי הביתה'")
                self._click_element_by_text("תחזירו אותי הביתה")
                self.page.wait_for_timeout(5000)
                continue
            if "404" in body:
                print("⚠️ 404, טוען מחדש")
                self.page.goto("https://www.rami-levy.co.il/he", timeout=30000)
                self.page.wait_for_timeout(5000)
                continue
            break

        body = self._get_body()
        if "רמי לוי" in body or "התחברות" in body or "סל" in body:
            print("✅ עמוד הבית נטען")
        else:
            print(f"⚠️ דף לא מוכר")
            self.page.screenshot(path="debug_homepage.png")

    def _get_body(self):
        try:
            return self.page.inner_text("body")[:1000]
        except:
            return ""

    def _click_element_by_text(self, text):
        for sel in [f"a:has-text('{text}')", f"button:has-text('{text}')", f"text={text}"]:
            try:
                el = self.page.locator(sel).first
                if el.count() > 0 and el.is_visible():
                    el.click(timeout=3000)
                    return
            except:
                pass
        print(f"⚠️ לא נמצא אלמנט לחיץ: {text}")

    def _ensure_not_404(self):
        body = self._get_body()
        if "תחזירו אותי הביתה" in body:
            print("⚠️ 404, לוחץ הביתה")
            self._click_element_by_text("תחזירו אותי הביתה")
            self.page.wait_for_timeout(5000)

    def _close_popups(self):
        """סוגר פופאפים, מודלים, וחלוניות קופצות — אגרסיבי."""
        try:
            # JavaScript — הורג את המודל ישירות
            self.page.evaluate("""() => {
                // מסיר BV modal
                document.querySelectorAll('[id*="BV_modal"], [id*="modal"], .modal-backdrop, .modal.show').forEach(el => el.remove());
                // מסיר backdrop
                document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
                // מחזיר scroll ל-body
                document.body.style.overflow = '';
                document.body.classList.remove('modal-open');
            }""")
            self.page.wait_for_timeout(300)

            # Escape סוגר מודלים
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(200)

            # ניסיון לסגור מודל BV דרך כפתור
            close_btns = self.page.locator("[aria-label='Close'], .close, .modal-header button, button.close")
            if close_btns.count() > 0:
                for i in range(close_btns.count()):
                    try:
                        btn = close_btns.nth(i)
                        if btn.is_visible():
                            btn.click(timeout=2000)
                            self.page.wait_for_timeout(300)
                    except:
                        pass

            # הקלקה על רקע
            self.page.mouse.click(10, 10)
            self.page.wait_for_timeout(200)

            # שוב Escape
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(200)

            # JavaScript שוב — מוודא ניקיון
            self.page.evaluate("""() => {
                document.querySelectorAll('[id*="BV_modal"], .modal-backdrop').forEach(el => el.remove());
                document.body.style.overflow = '';
                document.body.classList.remove('modal-open');
            }""")
            self.page.wait_for_timeout(300)
        except:
            pass

    # ============================================================
    # חיפוש (משותף לברקוד ולשם)
    # ============================================================

    def _do_search(self, query):
        """מקליד טקסט בתיבת החיפוש ולוחץ Enter."""
        self._ensure_not_404()
        self._close_popups()

        input_box = self.page.locator("input").first
        input_box.wait_for(state="visible", timeout=5000)

        # force click — דולג מעל מודלים חוסמים
        input_box.click(force=True, timeout=5000)
        input_box.fill("")       # מנקה
        input_box.fill(query)
        input_box.press("Enter")
        self.page.wait_for_timeout(4000)

    # ============================================================
    # גרידת תוצאות חיפוש
    # ============================================================

    def _scrape_results(self):
        """
        אוסף את כל תוצאות החיפוש מהדף.
        כל תוצאה נמצאת בתוך div שמכיל span.sr-only עם 'פתח תיאור'.
        מחזיר רשימה של dictים.
        """
        results = []

        sr_spans = self.page.locator("span.sr-only:has-text('פתח תיאור')")
        count = sr_spans.count()

        for i in range(count):
            try:
                span = sr_spans.nth(i)

                # מטפסים 4 רמות למעלה — ה-div של כרטיס המוצר
                card = span.locator("..").locator("..").locator("..").locator("..")
                text = card.inner_text()

                # handle timeout/errors silently
                if not text or "מחיר" not in text:
                    continue

                lines = [l.strip() for l in text.split("\n") if l.strip()]

                # parse: need to find product name, brand|size, price
                # Lines can have "פתח תיאור" (sr-only), promo labels, etc.
                # Clean lines: remove sr-only and price-lines
                clean = [l for l in lines
                         if "פתח תיאור" not in l
                         and not l.startswith("₪")
                         and "מחיר" not in l
                         and "שקלים" not in l
                         and "ליח'" not in l
                         and not l.endswith("גרם")  # price-per-gram
                         and not l.endswith("מל")   # price-per-ml
                         and "ל-100" not in l]      # price-per-100

                # Find product name — longest meaningful line
                product_name = ""
                brand = ""
                size = ""

                for line in clean:
                    # brand|size line
                    if "|" in line and not product_name:
                        # Might be before or after name
                        parts = line.split("|")
                        brand = parts[0].strip()
                        size = parts[1].strip() if len(parts) > 1 else ""
                        continue

                    # If line contains letters and >3 chars, it's probably the name
                    if any(c.isalpha() or c in "אבגדהוזחטיכלמנסעפצקרשת" for c in line) and len(line) > 3:
                        if not product_name or len(line) > len(product_name):
                            product_name = line

                # Fallback: find brand|size after name
                if not brand:
                    for line in lines:
                        if "|" in line:
                            parts = line.split("|")
                            brand = parts[0].strip()
                            size = parts[1].strip() if len(parts) > 1 else ""
                            break

                # price — find the line with ₪ and digits
                price = ""
                for line in lines:
                    if "₪" in line and any(c.isdigit() for c in line):
                        price = line.strip()
                        break

                # Skip fake/spam results
                if "פתח תיאור" in product_name:
                    continue
                if len(product_name) < 3:
                    continue
                # Skip promo/price labels
                skip_promo = False
                if "ההטבה" in product_name:
                    skip_promo = True
                if product_name and product_name.split():
                    first_word = product_name.split()[0]
                    if "ב-" in first_word:
                        skip_promo = True
                if skip_promo:
                    continue
                # Skip if it's just a number or promo code
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

            except Exception as e:
                continue

        return results

    # ============================================================
    # התאמה חכמה
    # ============================================================

    def _score_match(self, requested_name, result):
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
            # מילים קטנות מדי — מדלגים
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

        # בונוס: אחוז שומן תואם (1%, 2%, 3%)
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

    def _pick_best(self, results, requested_name):
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
            print(f"⚠️ אין התאמה טובה (ציון {best_score})")
            return None

        print(f"✅ הכי טוב: {best['name']} | {best['brand']} | {best['price']} (ציון {best_score})")
        return best

    # ============================================================
    # הוספה לסל
    # ============================================================

    def _expand_product_card(self, result_index):
        """
        לוחץ על כרטיס המוצר לפי האינדקס כדי לחשוף את כפתור הפלוס.
        """
        sr_spans = self.page.locator("span.sr-only:has-text('פתח תיאור')")
        if result_index >= sr_spans.count():
            print(f"❌ אינדקס {result_index} מחוץ לטווח")
            return False

        span = sr_spans.nth(result_index)
        # מטפסים ל-div הגלוי
        card = span.locator("..").locator("..").locator("..").locator("..")

        # לוחצים על הכרטיס
        card.click()
        self.page.wait_for_timeout(1500)
        return True

    def _click_plus(self, times=1):
        """לוחץ על כפתור + (פלוס) N פעמים."""
        for _ in range(times):
            plus_btn = self.page.locator("button.plus").first
            if plus_btn.count() == 0:
                print("❌ no plus button")
                return False
            plus_btn.evaluate("el => el.click()")
            self.page.wait_for_timeout(600)
        return True

    # ============================================================
    # תהליך מלא — ברקוד
    # ============================================================

    def process_barcode(self, barcode):
        # legacy wrapper
        return self.process_product(barcode=barcode, name=None, quantity=1)

    # ============================================================
    # תהליך מלא — מוצר (ברקוד + שם + כמות)
    # ============================================================

    def process_product(self, barcode=None, name=None, quantity=1, kg_per_click=None):
        """
        מוסיף מוצר לעגלה.
        - quantity: כמה יחידות/ק"ג להוסיף
        - kg_per_click: כמה ק"ג כל לחיצה (ברירת מחדל 1 = יחידות).
          לפירות/ירקות — 0.5 (חצי קילו ללחיצה)
        """
        # למשל 3 ק"ג עם 0.5 ק"ג ללחיצה = 6 לחיצות
        clicks = quantity
        if kg_per_click is not None and kg_per_click > 0:
            clicks = max(1, round(quantity / kg_per_click))

        print(f"\n{'='*50}")
        print(f"מוצר: ברקוד={barcode} שם={name} כמות={quantity} ({clicks} לחיצות)")

        # ----------------------------------------
        # נתיב 1: יש ברקוד
        # ----------------------------------------
        if barcode:
            print("🔍 מחפש לפי ברקוד:", barcode)
            try:
                self._do_search(barcode)
            except Exception as e:
                print(f"❌ חיפוש ברקוד נכשל: {e}")
                if name:
                    print("↪ נופל לחיפוש לפי שם...")
                    return self._process_by_name(name, quantity, clicks)
                return False

            self._ensure_not_404()

            has_results = False
            try:
                self.page.wait_for_selector("text=תוצאות חיפוש עבור", timeout=10000)
                has_results = True
            except:
                pass

            if not has_results:
                print("❌ לא נמצאו תוצאות לברקוד — מחפש חלופה לפי שם")
                if name:
                    return self._process_by_name(name, quantity, clicks)
                return False

            self._close_popups()

            results = self._scrape_results()

            if name and results:
                best = self._pick_best(results, name)
                if best:
                    print(f"📌 פותח מוצר #{best['index']}: {best['name']}")
                    self._expand_product_card(best["index"])
                else:
                    print("⚠️ לא נמצאה התאמה טובה, מנסה חיפוש לפי שם")
                    return self._process_by_name(name, quantity, clicks)
            elif results:
                print(f"📌 פותח מוצר ראשון: {results[0]['name']}")
                self._expand_product_card(0)
            else:
                print("❌ לא נמצאו תוצאות")
                if name:
                    return self._process_by_name(name, quantity, clicks)
                return False

            print(f"➕ מוסיף {clicks} יחידות" if clicks == quantity else f"➕ מוסיף {quantity} ק\"ג = {clicks} לחיצות")
            return self._click_plus(times=clicks)

        # ----------------------------------------
        # נתיב 2: חיפוש לפי שם בלבד
        # ----------------------------------------
        else:
            return self._process_by_name(name, quantity, clicks)

    # ============================================================
    # חיפוש לפי שם (חלופה / נתיב ראשי בלי ברקוד)
    # ============================================================

    def _process_by_name(self, name, quantity, clicks=None):
        if clicks is None:
            clicks = quantity

        print("🔍 מחפש לפי שם:", name)
        try:
            self._do_search(name)
        except Exception as e:
            print(f"❌ חיפוש שם נכשל: {e}")
            return False

        self._ensure_not_404()
        try:
            self.page.wait_for_selector("text=תוצאות חיפוש עבור", timeout=10000)
        except:
            print("❌ לא נמצאו תוצאות לשם")
            return False

        self._close_popups()

        results = self._scrape_results()
        print(f"📋 נמצאו {len(results)} תוצאות")

        if not results:
            print("❌ לא נמצאו תוצאות")
            return False

        best = self._pick_best(results, name)
        if not best:
            print("❌ לא נמצאה התאמה טובה")
            return False

        print(f"📌 פותח מוצר #{best['index']}: {best['name']}")
        self._expand_product_card(best["index"])

        print(f"➕ מוסיף {clicks} לחיצות")
        return self._click_plus(times=clicks)
