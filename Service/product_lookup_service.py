"""
Product Lookup Service
חיפוש תלת-שלבי: ברקוד ← שם ← fuzzy matching.
משתמש ב-OpenFoodFacts API למילוי אוטומטי של מוצרים חדשים.
"""

import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from Service.openfoodfacts_adapter import OpenFoodFactsAdapter

logger = logging.getLogger(__name__)

# ייבוא דחוי — rapidfuzz היא אופציונלית
try:
    from rapidfuzz import fuzz, process
    HAS_FUZZY = True
except ImportError:
    HAS_FUZZY = False


class ProductLookupService:
    """
    שירות חיפוש מוצרים תלת-שלבי.

    שלב 1: חיפוש לפי ברקוד — הכי מדויק
    שלב 2: חיפוש לפי שם מדויק ב-DB
    שלב 3: חיפוש fuzzy לפי שם ב-DB
    שלב 4 (אוטומטי): משיכה מ-OpenFoodFacts אם לא נמצא מקומית

    שימוש:
        service = ProductLookupService(db_session)
        product = service.lookup(barcode="7290112495037", name="קוקומן")
    """

    def __init__(self, session: Session):
        self.session = session
        self.off_adapter = OpenFoodFactsAdapter(session)

    # ── API ציבורי ─────────────────────────────────────────

    def lookup(
        self,
        barcode: Optional[str] = None,
        name: Optional[str] = None,
        category_id: int = 1,
        fuzzy_threshold: int = 75,
    ) -> Optional[Dict[str, Any]]:
        """
        מחפש מוצר. מחזיר dict עם כל השדות, או None.
        אם המוצר לא נמצא מקומית — מנסה למשוך מ-OpenFoodFacts.
        """
        product = None

        # שלב 1: ברקוד
        if barcode:
            product = self._by_barcode(barcode)

        # שלב 2: שם מדויק
        if not product and name:
            product = self._by_exact_name(name)

        # שלב 3: fuzzy
        if not product and name and HAS_FUZZY:
            product = self._by_fuzzy(name, threshold=fuzzy_threshold)

        # שלב 4: משיכה מ-OpenFoodFacts
        if not product and barcode:
            off_data = self.off_adapter.fetch_by_barcode(barcode)
            if off_data and off_data.get("name"):
                saved_id = self.off_adapter.save_to_db(off_data, category_id)
                if saved_id:
                    product = self._by_id(saved_id)

        if not product and name:
            off_results = self.off_adapter.search_by_name(name, page_size=3)
            for off_data in off_results:
                if off_data.get("name"):
                    saved_id = self.off_adapter.save_to_db(off_data, category_id)
                    if saved_id:
                        product = self._by_id(saved_id)
                        break

        return product

    def lookup_or_create(
        self,
        barcode: Optional[str] = None,
        name: Optional[str] = None,
        category_id: int = 1,
    ) -> Optional[int]:
        """
        כמו lookup, אבל מחזיר רק את ה-id (או None).
        """
        result = self.lookup(barcode=barcode, name=name, category_id=category_id)
        if result:
            return result["id"]
        return None

    def add_manual(
        self,
        name: str,
        barcode: Optional[str] = None,
        category_id: int = 1,
        off_category: Optional[str] = None,
        off_brand: Optional[str] = None,
    ) -> int:
        """
        הוספת מוצר ידנית. מחזיר את ה-id החדש.
        """
        self.session.execute(
            text("""
                INSERT INTO products (name, category_id, code, source, off_category, off_brand)
                VALUES (:name, :category_id, :code, 'manual', :off_category, :off_brand)
            """),
            {
                "name": name[:50],
                "category_id": category_id,
                "code": barcode or None,
                "off_category": (off_category or "")[:100],
                "off_brand": (off_brand or "")[:100],
            },
        )
        self.session.commit()

        new_id = self.session.execute(
            text("SELECT SCOPE_IDENTITY()")
        ).scalar()
        logger.info(f"Manually added product: id={new_id}, name={name}")
        return new_id

    # ── שאילתות פנימיות ───────────────────────────────────

    def _by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        row = self.session.execute(
            text("""
                SELECT id, name, category_id, code, source, off_category, off_brand, volume_ml
                FROM products
                WHERE code = :code
            """),
            {"code": barcode},
        ).mappings().first()
        return dict(row) if row else None

    def _by_exact_name(self, name: str) -> Optional[Dict[str, Any]]:
        row = self.session.execute(
            text("""
                SELECT id, name, category_id, code, source, off_category, off_brand, volume_ml
                FROM products
                WHERE name = :name
            """),
            {"name": name[:50]},
        ).mappings().first()
        return dict(row) if row else None

    def _by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        row = self.session.execute(
            text("""
                SELECT id, name, category_id, code, source, off_category, off_brand, volume_ml
                FROM products
                WHERE id = :id
            """),
            {"id": product_id},
        ).mappings().first()
        return dict(row) if row else None

    def _by_fuzzy(self, name: str, threshold: int = 75) -> Optional[Dict[str, Any]]:
        """מריץ fuzzy matching מול כל שמות המוצרים ב-DB."""
        if not HAS_FUZZY:
            return None

        rows = self.session.execute(
            text("""
                SELECT id, name, category_id, code, source, off_category, off_brand, volume_ml
                FROM products
            """)
        ).mappings().all()

        if not rows:
            return None

        # rapidfuzz מחפש הכי קרוב
        choices = {row["name"]: i for i, row in enumerate(rows)}
        match = process.extractOne(name, list(choices.keys()), scorer=fuzz.ratio)

        if match:
            best_name, score, _ = match
            if score >= threshold:
                logger.debug(f"Fuzzy match: '{name}' -> '{best_name}' (score={score})")
                return dict(rows[choices[best_name]])

        return None

    # ── חיפוש מוצרים מהרשימה ─────────────────────────────

    def get_pending_manual(self) -> List[Dict[str, Any]]:
        """
        מחזיר מוצרים שמקורם 'manual' — כלומר כאלה שהוזנו ידנית.
        שימושי לדעת אילו מוצרים אין ב-OpenFoodFacts.
        """
        rows = self.session.execute(
            text("""
                SELECT id, name, code, off_category, off_brand
                FROM products
                WHERE source = 'manual'
                ORDER BY name
            """)
        ).mappings().all()
        return [dict(r) for r in rows]
