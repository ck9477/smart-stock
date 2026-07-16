import io
import json
import re
from datetime import datetime

from models.Products import Product
from models.receipts import Receipt
from models.Reception_products import ReceptionProducts
from Repository.Products import ProductRepository
from Repository.receipts import ReceiptRepository
from Repository.Reception_products import ReceptionProductsRepository



class ReceiptService:

    def __init__(self, session):
        self.session = session
        self.receipt_repo = ReceiptRepository(session)
        self.reception_repo = ReceptionProductsRepository(session)
        self.product_repo = ProductRepository(session)

    # -----------------------------
    # MAIN FLOW
    # -----------------------------
    def create_receipt(self, user_id: int, receipt_date=None):
        """
        Create an empty receipt (e.g. for manual entry).
        receipt_date: datetime or None (defaults to today).
        """
        if receipt_date is None:
            receipt_date = self._resolve_date(None)
        receipt = Receipt(user_id=user_id, receipt_date=receipt_date)
        self.receipt_repo.add_receipt(receipt)
        self.session.commit()
        return receipt.id

    def process_receipt(self, receipt_file, user_id: int):
        from Service.receipt_parser import parse_receipt
        text = self._read_receipt_text(receipt_file)
        products, parsed_date = parse_receipt(text)

        if not products:
            raise ValueError("No products found in receipt")

        receipt_date = self._resolve_date(parsed_date)

        receipt = Receipt(user_id=user_id, receipt_date=receipt_date)
        self.receipt_repo.add_receipt(receipt)
        self.session.flush()
        self.session.refresh(receipt)

        receipt_id = receipt.id
        reception_items = []
        products_response = []

        for raw_product in products:
            product = self.find_or_create_product(raw_product)
            amount = self.parse_amount(raw_product.get("quantity", 1))
            reception_item = ReceptionProducts(
                receipts_id=receipt_id,
                products_id=product.id,
                amount=amount
            )
            reception_items.append(reception_item)
            products_response.append({
                "reception_id": None,
                "product_id": product.id,
                "product_code": product.code,
                "name": product.name,
                "amount": amount
            })

        self.reception_repo.add_items(reception_items)
        self.session.commit()

        for item, response_item in zip(reception_items, products_response):
            response_item["reception_id"] = item.id

        return {
            "receipt_id": receipt_id,
            "receipt_date": receipt_date.isoformat(),
            "products": products_response
        }

    # -----------------------------
    # FIND OR CREATE PRODUCT (with OpenFoodFacts enrichment)
    # -----------------------------
    def find_or_create_product(self, raw_product):
        code = str(raw_product.get("code", "")).strip() or None
        name = str(raw_product.get("name", "")).strip() or None

        # ── שלב 1–4: חיפוש מקומי + OpenFoodFacts + fuzzy ──
        from Service.product_lookup_service import ProductLookupService
        lookup = ProductLookupService(self.session)

        result = lookup.lookup(barcode=code, name=name)
        if result:
            product = self.product_repo.get_by_id(result["id"])
            if product:
                # ⚠️ Override bad OFF name with the receipt name if better
                product = self._prefer_receipt_name(product, name)

                # ⚠️ Fix category if it stayed on default (33) and we can guess better
                if product.category_id == 33 and name:
                    guessed = self._guess_category(name)
                    if guessed != 33:
                        product.category_id = guessed
                        from sqlalchemy.orm import object_session
                        sess = object_session(product)
                        if sess:
                            sess.flush()

                return product

        # ── שלב 5: נפילה אחרונה — יצירת מוצר ידנית ──
        category_id = self._guess_category(name) if name else 33
        product = Product(
            name=name if name else "UNKNOWN",
            code=code,
            category_id=category_id,
            volume_ml=0,
            source='manual',
        )

        self.product_repo.add(product)
        self.session.flush()
        self.session.refresh(product)
        return product

    # -----------------------------
    # PREFER RECEIPT NAME OVER BAD OFF NAMES
    # -----------------------------
    @staticmethod
    def _prefer_receipt_name(product, receipt_name: str):
        """
        If the DB product name came from OpenFoodFacts and is in a foreign
        language while the receipt has a good Hebrew name — upgrade it.
        Only updates when:
        - receipt_name has Hebrew characters
        - the current name has NO Hebrew (pure English/French/etc.)
        """
        if not receipt_name or len(receipt_name) < 3:
            return product

        current_name = (product.name or "").strip()
        if not current_name:
            return product

        has_hebrew = any('֐' <= c <= '׿' for c in receipt_name)
        no_hebrew_current = not any('֐' <= c <= '׿' for c in current_name)

        if has_hebrew and no_hebrew_current:
            product.name = receipt_name[:50]
            # Keep source as-is; only update if it was 'openfoodfacts'
            # (CK_products_source constraint allows: manual, openfoodfacts, import)
            if product.source == 'openfoodfacts':
                product.source = 'manual'
            # Persist immediately so the fix is saved to DB
            from sqlalchemy.orm import object_session
            sess = object_session(product)
            if sess:
                sess.flush()

        return product

    # -----------------------------
    # CATEGORY GUESSER (when OpenFoodFacts is unavailable)
    # -----------------------------
    def _normalize_product_name(self, name: str) -> str:
        name = name.lower().strip()
        name = re.sub(r'\b(?:בטעמי|בטעם של|בטעם|טעם)\b\s*', ' ', name)
        name = re.sub(r'[^א-תa-z0-9\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    @staticmethod
    def _keyword_match(text: str, keyword: str) -> bool:
        keyword = keyword.strip().lower()
        if not keyword:
            return False
        if re.search(r'\b' + re.escape(keyword) + r'\b', text):
            return True
        return keyword in text

    def _guess_category(self, name: str) -> int:
        """מנחש קטגוריה לפי מילות מפתח בשם המוצר."""
        name_lower = name.strip().lower()
        cleaned = self._normalize_product_name(name_lower)
        if len(cleaned) < 2:
            cleaned = name_lower

        category_keywords = [
            (32, [
                "קרמים", "סירופ", "קולה", "מיץ", "משקה", "סודה", "ספרינג", "פפסי",
                "שוקו", "קקאו", "בירה", "יין", "שתייה", "שתיה",
                "אנרגיה", "טרופית", "תפוזינה", "ספרייט", "פאנטה",
                "juice", "cola", "soda", "beer", "wine", "drink", "tea", "coffee"
            ]),
            (37, [
                "דוריטוס", "חטיף", "חטיפי", "ביסלי", "במבה", "צ'יטוס", "שוש",
                "אפרופו", "קליק", "פינגווין", "פיצוחים", "גרעינים",
                "שוקולד", "ממתק", "סוכריות", "מרשמלו", "עוגיות", "ופל",
                "בייגלה", "שלדג", "קרקרים", "פופקורן", "צ'יפס"
            ]),
            (27, [
                "עוגה", "עוגי", "בורקס", "קרואסון", "רוגלך", "סופגני", "דונאט",
                "מאפה", "מאפין", "cake", "pastry", "donut", "croissant"
            ]),
            (31, [
                "לחם", "חלה", "פיתה", "לחמני", "בייגל", "מצה", "בורגול", "קוסקוס",
                "bread", "pita", "bagel"
            ]),
            (35, [
                "נודלס", "פסטה", "ספגטי", "מקרוני", "אורז", "אטריות", "פתיתים",
                "pasta", "spaghetti", "macaroni", "rice", "noodles"
            ]),
            (30, [
                "חלב", "שמנת", "יוגורט", "גבינ", "לבן", "אשל", "קוטג'", "ביצ",
                "milk", "yogurt", "egg", "dairy"
            ]),
            (29, [
                "צהובה", "גבינה", "בולגרית", "צפתית", "מוצרלה", "פרמזן", "גאודה", "עמק",
                "ricotta", "mozzarella", "feta", "parmesan", "gouda", "cheese"
            ]),
            (34, [
                "שימורי", "שימורים", "כבושים", "מוחמצים", "מוחמץ", "טונה", "רסק",
                "קטשופ", "מיונז", "חרדל", "סילאן", "רוטב", "זיתים", "זיתי",
                "קורנפלור", "מלפפון חמוץ", "סויה", "משומר",
                "canned", "sauce", "mustard", "ketchup", "soy sauce"
            ]),
            (39, ["קפוא", "קפואה", "קפואים", "קפואות", "frozen", "ice cream"]),
            (38, [
                "בשר", "עוף", "הודו", "סלמון", "קרפיון", "אמנון", "בורי", "מושט",
                "נקניק", "נקניקיה", "פסטרמה", "סלמי", "שווארמה", "קבב",
                "המבורגר", "שניצל", "כנפיים", "שוקי", "חזה", "פרגית",
                "בקר", "כבש", "עגל", "אנטריקוט", "צלעות", "סטייק",
                "meat", "chicken", "turkey", "beef", "salmon", "fish"
            ]),
            (28, [
                "עגבני", "מלפפון", "חציל", "בצל", "גזר", "כרוב", "חסה", "פלפל",
                "פטרוז", "קישוא", "דלעת", "סלק", "צנון", "שום", "אבוקדו",
                "בטטה", "תפו", "קולורבי", "ארטישוק", "אספרגوس", "שעועית ירוקה",
                "תפוח", "אגס", "בננה", "אבטיח", "מלון", "ענב", "תות", "קלמנטי",
                "תפוז", "לימון", "אשכולי", "מנגו", "קיווי", "שזיף", "אפרסק",
                "משמש", "נקטרי", "צבר", "פסיפלו", "רימון", "תמר", "תאנה",
                "אננס", "פפאיה", "דובדבן", "פירות יער", "אוכמני", "פטל",
                "fruit", "vegetable", "salad", "herb", "mushroom"
            ]),
            (42, ["אקונומיקה", "מסיר שומנים", "ספריי", "bleach", "degreaser", "spray"]),
            (36, [
                "נוזל רצפות", "סבון כלים", "מרכך כביסה", "חומר ניקוי", "ספוג",
                "מגבון", "שמפו", "משחת שיניים", "דאודורנט", "מרכך שיער",
                "קרם גוף", "תרחיץ", "נוזל כלים", "מסיר", "אבקת כביסה",
                "טישו", "נייר טואלט", "חיתולים", "מטליות", "שקית אשפה",
                "שקיות אשפה", "cleaning", "soap", "shampoo", "toothpaste",
                "detergent", "laundry", "bleach", "dishwashing"
            ]),
            (33, [
                "סוכר", "מלח", "שמן", "קמח", "קטניות", "עדשים", "שעועית", "חומוס",
                "תירס", "אפונה", "דבש", "ריבה", "טחינה", "מרגרינה",
                "חמאה", "אורגנו", "פפריקה", "כמון", "קינמון", "פלפל שחור",
                "כורכום", "זעתר", "תבלין", "אבקת אפיה", "סודה לשתיה",
                "תמצית וניל", "שמרים", "פירורי לחם", "ציר", "מרק", "אבקת מרק",
                "spice", "sugar", "salt", "flour", "oil", "lentil", "beans", "cereal"
            ]),
        ]

        for category_id, keywords in category_keywords:
            if any(self._keyword_match(cleaned, kw) for kw in keywords):
                return category_id

        return 33

    # -----------------------------
    # AMOUNT PARSER
    # -----------------------------
    def parse_amount(self, amount):
        try:
            amount = int(float(amount))
        except Exception:
            return 1
        if amount < 1:
            return 1
        if amount > 1000:
            return 1
        return amount

    # -----------------------------
    # PARSE RECEIPT FILE
    # -----------------------------
    def _read_receipt_text(self, receipt_file) -> str:
        """Extract raw text from receipt file (PDF or plain text)."""
        from Service.receipt_parser import extract_text_from_pdf

        receipt_file.stream.seek(0)
        raw = receipt_file.read()
        filename = (getattr(receipt_file, "filename", "") or "").lower()

        if filename.endswith(".pdf"):
            text = extract_text_from_pdf(raw)
        else:
            text = raw.decode("utf-8", errors="ignore")

        # DEBUG
        with open("debug_receipt.txt", "w", encoding="utf-8") as f:
            f.write(text)

        return text

    @staticmethod
    def _resolve_date(parsed_date: str | None):
        """Fallback to today if the parser couldn't find a date."""
        if parsed_date:
            try:
                return datetime.strptime(parsed_date, "%Y-%m-%d")
            except ValueError:
                pass
        # Default: today at midnight
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    def parse_receipt_file(self, receipt_file):
        """Legacy wrapper — returns only products (for direct JSOn upload)."""
        from Service.receipt_parser import parse_receipt

        text = self._read_receipt_text(receipt_file)

        # Try JSON first (for programmatic uploads)
        try:
            payload = json.loads(text)
            if isinstance(payload, list):
                return self.filter_real_products(payload)
            if isinstance(payload, dict) and "products" in payload:
                return self.filter_real_products(payload["products"])
        except Exception:
            pass

        # Use the new dedicated parser (ignore date for legacy callers)
        products, _ = parse_receipt(text)
        return self.filter_real_products(products)

    # -----------------------------
    # FILTER REAL PRODUCTS
    # -----------------------------
    def filter_real_products(self, products):
        filtered = []
        for p in products:
            code = str(p.get("product_code") or p.get("code") or "")
            name = p.get("name", "")
            quantity = p.get("amount") or p.get("quantity") or 1

            # סינון שורות ריקות / רעש
            ignore_words = ["תעודת משלוח", "מבצע", "דירה", "חי", "חשי", "פוריס", "סוכב", "סמנ"]
            if any(word in name for word in ignore_words):
                continue

            # רק מוצרים עם קוד תקין
            if not code or not code.isdigit() or len(code) < 6:
                continue

            filtered.append({
                "code": code,
                "name": name,
                "quantity": self.parse_amount(quantity)
            })
        return filtered

    # -----------------------------
    # PARSE INVOICE TEXT
    # -----------------------------
    def parse_invoice_text(self, text):
        import re

        lines = text.splitlines()
        items = []
        seen_codes = set()

        # קוד מוצר: 6-14 ספרות רצופות
        code_re = re.compile(r'\b\d{6,14}\b')
        # מספרים (כמות, מחיר)
        number_re = re.compile(r'\d+(?:\.\d+)?')
        # אותיות עבריות ואנגליות
        letters_re = re.compile(r'[א-תA-Za-z]')

        # מילים ורעש שאסור להכניס
        noise_keywords = [
            "תעודת", "משלוח", "טלפון", "פקס", "כתובת",
            "דירה", "סהכ", "סה״כ", "חשבונית", "מסמך",
            "שולח", "נמען", "מבצע", "שח"
        ]

        def is_real_product(line, code):
            # ❌ שורה קצרה מידי? לא מוצר
            if len(line.strip()) < 5:
                return False

            # ❌ מכילה מילה מרעש
            if any(k in line for k in noise_keywords):
                return False

            # ❌ חייב להיות לפחות אות אחת + קוד
            if not letters_re.search(line):
                return False
            if not code:
                return False

            # ✅ אם כוללת מילת Imported או דומה, זה לרוב מוצר אמיתי
            if "Imported" in line:
                return True

            # אם יש מספרים נוספים (מחיר/כמות), סביר להניח מוצר
            nums = number_re.findall(line)
            if len(nums) >= 1:
                return True

            # אחרת, שורה לא נראית כמו מוצר
            return False

        for line in lines:
            line = line.strip()
            codes = code_re.findall(line)
            if not codes:
                continue

            code = codes[-1]
            if code in seen_codes:
                continue
            seen_codes.add(code)

            if not is_real_product(line, code):
                continue

            # ניקוי שם
            name = line.replace(code, "")
            name = re.sub(r'[\d\-\_\:\;\*\#\@\=\+\[\]\(\)/\.]', ' ', name)
            name = re.sub(r'\s+', ' ', name).strip()
            if len(name) < 2:
                name = "UNKNOWN"

            # חיפוש כמות ראשונה תקינה
            nums = number_re.findall(line)
            quantity = 1
            for n in nums:
                try:
                    v = float(n)
                    if 0 < v <= 1000:
                        quantity = int(v)
                        break
                except:
                    continue

            items.append({
                "code": code,
                "name": name,
                "quantity": quantity
            })

        return items
    # -----------------------------
    # EXTRACT PRODUCT NAME
    # -----------------------------
    def extract_product_name(self, text, code):
        text = text.replace(code, "")
        text = re.sub(r'\d+\.\d+', '', text)
        text = re.sub(r'\b\d+\b', '', text)
        text = re.sub(r'[-_:;*#@=+\[\]()/]', ' ', text)
        words = re.findall(r'[א-תA-Za-z]+', text)
        clean_name = " ".join(words).strip()

        non_products = ['תעודת', 'משלוח', 'invoice', 'receipt', 'סהכ', 'total', 'tax']
        if any(np in clean_name.lower() for np in non_products):
            return ""

        hebrew_count = sum(1 for c in clean_name if '\u0590' <= c <= '\u05FF')
        if hebrew_count > 1:
            clean_name = get_display(clean_name)

        return clean_name