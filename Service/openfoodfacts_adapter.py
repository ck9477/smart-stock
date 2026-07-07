"""
OpenFoodFacts API Adapter
Pulls product data from OpenFoodFacts and saves to local DB.
"""

import re
import time
import logging
import requests
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

BASE_URL = "https://world.openfoodfacts.org/api/v2"

# ── SSL support for filtered environments ──
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_VERIFY_SSL = True

try:
    import certifi
    _VERIFY_SSL = certifi.where()
except ImportError:
    pass

# In filtered environments, SSL verification may not work — allow override
if os.environ.get('OFF_VERIFY_SSL', '').lower() in ('false', '0', 'no'):
    _VERIFY_SSL = False


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
        self._http = requests.Session()
        self._http.verify = _VERIFY_SSL

    # ── API call ──────────────────────────────────────────────

    def fetch_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """
        מושך מוצר מ-OpenFoodFacts לפי ברקוד.
        מחזיר dict עם name, category, brand, barcode — או None אם לא נמצא.
        """
        self._rate_limit()

        url = f"{BASE_URL}/product/{barcode}.json"
        try:
            resp = self._http.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.warning(f"OpenFoodFacts API error for barcode {barcode}: {e}")
            return None

        if data.get("status") != 1 or not data.get("product"):
            logger.info(f"Product not found on OpenFoodFacts: {barcode}")
            return None

        return self._parse_product(data["product"], barcode)

    def search_by_name(self, name: str, page_size: int = 5) -> list[Dict[str, Any]]:
        """
        מחפש מוצרים לפי שם. מחזיר רשימה של dictים.
        """
        self._rate_limit()

        url = f"{BASE_URL}/search"
        params = {
            "search_terms": name,
            "search_simple": 1,
            "json": 1,
            "page_size": page_size,
        }
        try:
            resp = self._http.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.warning(f"OpenFoodFacts search error for '{name}': {e}")
            return []

        products = data.get("products", [])
        return [self._parse_product(p, p.get("code", "")) for p in products if p]

    # ── Save to DB ────────────────────────────────────────────

    def save_to_db(self, product_data: Dict[str, Any], category_id: int) -> Optional[int]:
        """
        שומר מוצר ב-DB המקומי. מדלג אם הברקוד כבר קיים.
        מחזיר את ה-id של המוצר (חדש או קיים), או None.
        """
        barcode = product_data.get("barcode")
        name = product_data.get("name", "ללא שם")[:50]
        off_category = (product_data.get("category") or "")[:100]
        off_brand = (product_data.get("brand") or "")[:100]

        if not name or name == "ללא שם":
            logger.warning(f"Skipping product with no name: barcode={barcode}")
            return None

        # בדיקה אם כבר קיים לפי ברקוד
        if barcode:
            existing_id = self.session.execute(
                text("SELECT id FROM products WHERE code = :code"),
                {"code": barcode},
            ).scalar()
            if existing_id:
                logger.debug(f"Product already in DB: barcode={barcode}, id={existing_id}")
                return existing_id

        # הכנסה
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

    # ── Helpers ────────────────────────────────────────────────

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
        # קטגוריות מגיעות עם קידומת שפה, למשל en:snacks
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
        """שומר על ריווח מינימלי בין בקשות — כבוד ל-API."""
        now = time.time()
        elapsed = now - self._last_request_at
        if elapsed < 0.3:  # מקסימום ~3 בקשות לשנייה
            time.sleep(0.3 - elapsed)
        self._last_request_at = time.time()
