"""
OpenFoodFacts API Adapter
Pulls product data from OpenFoodFacts and saves to local DB.
Uses curl subprocess (Python SSL is blocked in filtered environments).
"""

import json
import subprocess
import time
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

BASE_URL = "https://world.openfoodfacts.org/api/v2"


def _http_get_json(url: str, timeout: int = 10) -> Optional[dict]:
    """Fetch JSON from URL using curl (works through NetFree/Netspark)."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout), url],
            capture_output=True, text=True, encoding="utf-8", timeout=timeout + 2,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        return json.loads(result.stdout)
    except Exception as e:
        logger.warning(f"curl fetch failed: {e}")
        return None


class OpenFoodFactsAdapter:
    """
    מתקשר עם OpenFoodFacts API.
    שימוש:
        adapter = OpenFoodFactsAdapter(db_session)
        product = adapter.fetch_by_barcode("7290112495037")
        if product:
            saved = adapter.save_to_db(product, category_id=1)
    """

    def __init__(self, session: Session):
        self.session = session
        self._last_request_at = 0.0

    # ── API calls ────────────────────────────────────────────

    def fetch_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """מושך מוצר מ-OpenFoodFacts לפי ברקוד."""
        self._rate_limit()
        url = f"{BASE_URL}/product/{barcode}.json"
        data = _http_get_json(url)
        if not data or data.get("status") != 1 or not data.get("product"):
            logger.info(f"Product not found on OpenFoodFacts: {barcode}")
            return None
        return self._parse_product(data["product"], barcode)

    def search_by_name(self, name: str, page_size: int = 5) -> list[Dict[str, Any]]:
        """מחפש מוצרים לפי שם. מחזיר רשימה של dictים."""
        self._rate_limit()
        from urllib.parse import urlencode
        url = f"{BASE_URL}/search?{urlencode({'search_terms': name, 'search_simple': '1', 'json': '1', 'page_size': str(page_size)})}"
        data = _http_get_json(url)
        if not data:
            return []
        products = data.get("products", [])
        return [self._parse_product(p, p.get("code", "")) for p in products if p]

    # ── Save to DB ──────────────────────────────────────────

    # מיפוי OpenFoodFacts categories_tags → category_id פנימי
    # ⚠️ הסדר קריטי — ההתאמה הראשונה מנצחת.
    # דפוסים ספציפיים לפני כלליים (frozen vegetables לפני vegetables וכו')
    OFF_CATEGORY_MAP = [
        # ── קפואים (לפני vegetables/fruits/meat) ──
        (["frozen", "ice cream", "frozen food", "frozen meals",
          "frozen pizza", "frozen desserts"], 39),
        # ── חטיפים וממתקים ──
        (["biscuits", "cookies", "chocolates", "sweets", "candies",
          "confectioneries", "snacks", "crisps", "chips", "popcorn",
          "cereal bars", "sweet spreads", "nutella", "chocolate",
          "wafer", "waffles"], 37),
        # ── מאפים (לפני bread) ──
        (["cakes", "pastries", "croissant", "brioche", "doughnuts", "rusks"], 27),
        # ── לחמים ──
        (["bread", "breads", "toast", "pita", "baguettes", "rolls"], 31),
        # ── פסטות ואורז ──
        (["pasta", "noodles", "rice", "couscous", "spaghetti", "macaroni",
          "bulgur", "semolina", "quinoa"], 35),
        # ── משקאות ──
        (["beverages", "sodas", "cola", "soft drinks", "water", "mineral water",
          "juice", "nectar", "iced tea", "energy drink", "syrup", "cordial",
          "coffee", "tea", "hot drinks", "cocoa", "chocolate powder"], 32),
        # ── שימורים ורטבים (לפני vegetables/fruits) ──
        (["canned", "tuna", "sardine", "sauces", "ketchup", "mayonnaise",
          "mustard", "soy sauce", "vinegar", "olive oil", "oils",
          "tomato paste", "canned tomatoes", "canned corn",
          "pickles", "pickled", "preserves", "canned food",
          "olives", "olive", "cucumber pickle", "pickled cucumber",
          "canned peas", "shelf stable", "jarred", "tinned"], 34),
        # ── בשר ודגים (לפני fish שמופיע ב-fresh fish) ──
        (["meat", "poultry", "chicken", "turkey", "beef", "lamb",
          "sausage", "cold cuts", "pastrami", "salami",
          "fish", "salmon", "carp", "tilapia"], 38),
        # ── ניקיון וטיפוח ──
        (["cleaning", "hygiene", "soap", "shampoo", "toothpaste",
          "deodorant", "detergent", "laundry", "bleach",
          "dishwashing", "surface cleaner", "sponge",
          "tissues", "toilet paper", "diapers", "wipes",
          "shower gel", "body wash", "hand soap",
          "fabric softener", "air freshener"], 36),
        # ── גבינות טריות (ספציפי — לפני dairies כללי) ──
        (["fresh cheeses", "french cheeses", "spread cheeses",
          "cottage cheese", "fromage frais", "mozzarella",
          "feta", "parmesan", "gouda", "camembert", "brie",
          "ricotta", "mascarpone", "cream cheese", "goat cheese"], 29),
        # ── חלב ומוצרי חלב ──
        (["dairies", "yogurts", "milk", "cheese", "butter", "cream",
          "fermented milk", "dairy", "yogurt", "quark",
          "sour cream", "whipped cream"], 30),
        # ── פירות וירקות טריים (אחרונים — הכי פחות ספציפיים) ──
        (["fruits", "vegetables", "fresh vegetables", "fresh fruits",
          "salads", "leaf vegetables", "herbs", "mushrooms",
          "potatoes", "tomatoes", "onions", "garlic", "peppers",
          "citrus", "apples", "bananas", "grapes", "stone fruits",
          "berries", "melons", "tropical fruits", "cucumbers",
          "squashes", "aubergines", "avocados"], 28),
        # ── מוצרי יסוד (קטניות, תבלינים, אפייה) — אחרונים לגמרי ──
        (["legumes", "lentils", "chickpeas", "beans",
          "sugar", "salt", "flour", "baking", "yeast",
          "spices", "seasonings", "herbs dried",
          "cereals", "muesli", "granola", "oats",
          "breakfast cereals", "porridge"], 33),
    ]

    @classmethod
    def _map_off_category(cls, off_category: str) -> int | None:
        """ממפה off_category (מחרוזת מופרדת בפסיקים מ-OFF) ל-category_id פנימי.
        מחזיר None אם לא נמצא מיפוי."""
        if not off_category:
            return None
        cats_lower = off_category.lower()
        for keywords, cat_id in cls.OFF_CATEGORY_MAP:
            for kw in keywords:
                if kw in cats_lower:
                    return cat_id
        return None

    def save_to_db(self, product_data: Dict[str, Any], category_id: int) -> Optional[int]:
        """שומר מוצר ב-DB המקומי. מדלג אם הברקוד כבר קיים."""
        barcode = product_data.get("barcode")
        name = product_data.get("name", "ללא שם")[:50]
        off_category = (product_data.get("category") or "")[:100]
        off_brand = (product_data.get("brand") or "")[:100]

        if not name or name == "ללא שם":
            logger.warning(f"Skipping product with no name: barcode={barcode}")
            return None

        if barcode:
            existing_id = self.session.execute(
                text("SELECT id FROM products WHERE code = :code"),
                {"code": barcode},
            ).scalar()
            if existing_id:
                logger.debug(f"Product already in DB: barcode={barcode}, id={existing_id}")
                return existing_id

        # ── נסה למפות off_category לקטגוריה פנימית ──
        mapped_cat = self._map_off_category(off_category)
        if mapped_cat:
            category_id = mapped_cat
            logger.debug(f"Mapped OFF category '{off_category[:60]}...' -> cat_id={category_id}")

        self.session.execute(
            text("""
                INSERT INTO products (name, category_id, code, source, off_category, off_brand)
                VALUES (:name, :category_id, :code, 'openfoodfacts', :off_category, :off_brand)
            """),
            {
                "name": name,
                "category_id": category_id,
                "code": barcode or None,
                "off_category": off_category,
                "off_brand": off_brand,
            },
        )
        self.session.commit()

        new_id = self.session.execute(
            text("SELECT id FROM products WHERE code = :code"),
            {"code": barcode},
        ).scalar()
        logger.info(f"Saved new product: id={new_id}, name={name}, barcode={barcode}")
        return new_id

    # ── Helpers ──────────────────────────────────────────────

    def _parse_product(self, raw: Dict[str, Any], barcode: str) -> Dict[str, Any]:
        """מחלץ שם, קטגוריה ומותג ממוצר גולמי של OpenFoodFacts."""
        name = (
            raw.get("product_name_he")
            or raw.get("product_name_en")
            or raw.get("product_name")
            or raw.get("generic_name_he")
            or raw.get("generic_name_en")
            or ""
        ).strip()

        category = (
            raw.get("categories_tags", [])
            if isinstance(raw.get("categories_tags"), list)
            else []
        )
        category_clean = [
            c.split(":", 1)[1].replace("-", " ")
            for c in category[:3]
            if ":" in c
        ]
        category_str = ", ".join(category_clean) if category_clean else ""

        brand = (raw.get("brands") or "").strip()

        return {
            "barcode": barcode,
            "name": name,
            "category": category_str,
            "brand": brand,
        }

    def _rate_limit(self):
        """שומר על ריווח מינימלי בין בקשות."""
        now = time.time()
        elapsed = now - self._last_request_at
        if elapsed < 0.3:
            time.sleep(0.3 - elapsed)
        self._last_request_at = time.time()
