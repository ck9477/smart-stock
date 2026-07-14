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
