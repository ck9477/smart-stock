import io
import json
import pdfplumber
import re
from bidi.algorithm import get_display

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
    def process_receipt(self, receipt_file, user_id: int):
        products = self.parse_receipt_file(receipt_file)
        if not products:
            raise ValueError("No products found in receipt")

        receipt = Receipt(user_id=user_id)
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
            # המוצר נמצא (מקומית או דרך OpenFoodFacts)
            product = self.product_repo.get_by_id(result["id"])
            if product:
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
    # CATEGORY GUESSER (when OpenFoodFacts is unavailable)
    # -----------------------------
    def _guess_category(self, name: str) -> int:
        """מנחש קטגוריה לפי מילות מפתח בשם המוצר."""
        name_lower = name.strip()

        # 28 = פירות וירקות טריים
        fruits_veg = [
            "עגבני", "מלפפון", "חציל", "בצל", "תפוח", "אגס", "בננה", "אבטיח",
            "מלון", "ענב", "תות", "קלמנטי", "תפוז", "לימון", "אשכולי",
            "גזר", "כרוב", "חסה", "פלפל", "פטרוז", "קישוא", "דלעת",
            "סלק", "צנון", "שום", "אבוקדו", "מנגו", "קיווי", "שזיף",
            "אפרסק", "משמש", "נקטרי", "צבר", "פסיפלו", "רימון",
            "תמר", "תאנה", "זית", "בטטה", "תפו\"א", "תפוח אדמה",
        ]
        if any(w in name_lower for w in fruits_veg):
            return 28

        # 30 = חלב וביצים / 29 = מוצרי חלב טריים
        dairy = ["חלב", "שמנת", "יוגורט", "גבינ", "לבן", "אשל", "קוטג'", "ביצ"]
        if any(w in name_lower for w in dairy):
            return 30

        # 31 = לחמים ותחליפי פחמימה
        bread = ["לחם", "חלה", "פיתה", "לחמני", "בייגל", "קרקר", "מצה", "בורגול", "קוסקוס", "קמח"]
        if any(w in name_lower for w in bread):
            return 31

        # 32 = משקאות קלים
        drinks = ["קולה", "מיץ", "משקה", "סודה", "מים", "ספרינג", "פפסי", "שוקו", "קקאו",
                  "בירה", "יין", "שתייה", "שתיה", "אנרגיה"]
        if any(w in name_lower for w in drinks):
            return 32

        # 35 = אורז ופסטות
        grains = ["פסטה", "ספגטי", "מקרוני", "אורז", "אטריות", "נודלס", "פתיתים", "קוסקוס"]
        if any(w in name_lower for w in grains):
            return 35

        # 34 = שימורים ורטבים
        canned = ["שימורי", "טונה", "רסק", "קטשופ", "מיונז", "חרדל", "סילאן",
                  "רוטב", "זיתים", "קורנפלור", "מלפפון חמוץ", "סויה"]
        if any(w in name_lower for w in canned):
            return 34

        # 36 = מוצרי ניקיון
        cleaning = ["נוזל רצפות", "סבון כלים", "מרכך כביסה", "אקונומיקה", "חומר ניקוי",
                    "ספוג", "מגבון", "שמפו", "סבון", "משחת שיניים", "דאודורנט",
                    "מרכך שיער", "ג'ל", "קרם גוף", "תרחיץ"]
        if any(w in name_lower for w in cleaning):
            return 36

        # 29 = מוצרי חלב טריים (גבינות ספציפיות)
        cheese = ["צהובה", "גבינה", "בולגרית", "צפתית", "מוצרלה", "פרמזן", "גאודה", "עמק"]
        if any(w in name_lower for w in cheese):
            return 29

        # 27 = מאפים טריים
        bakery = ["עוגה", "עוגי", "בורקס", "קרואסון", "רוגלך", "סופגני", "דונאט"]
        if any(w in name_lower for w in bakery):
            return 27

        # 33 = מוצרי יסוד
        staples = ["סוכר", "מלח", "שמן", "קמח", "קטניות", "עדשים", "שעועית",
                   "חומוס", "תירס", "אפונה"]
        if any(w in name_lower for w in staples):
            return 33

        # 42 = חומרי ניקוי
        heavy_cleaning = ["אקונומיקה", "נוזל כלים", "מסיר שומנים", "ספריי"]
        if any(w in name_lower for w in heavy_cleaning):
            return 42

        # defaultgit
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
    def parse_receipt_file(self, receipt_file):
        from Service.receipt_parser import extract_text_from_pdf, parse_receipt

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

        # Try JSON first (for programmatic uploads)
        try:
            payload = json.loads(text)
            if isinstance(payload, list):
                return self.filter_real_products(payload)
            if isinstance(payload, dict) and "products" in payload:
                return self.filter_real_products(payload["products"])
        except Exception:
            pass

        # Use the new dedicated parser
        products = parse_receipt(text)
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
            from Service.receipt_parser import fix_hebrew_reversal
            clean_name = fix_hebrew_reversal(clean_name)

        return clean_name