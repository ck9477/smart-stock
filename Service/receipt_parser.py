"""
Receipt Parser — dedicated extraction functions per receipt type.

1. parse_mehadrin  — Mehadrin Online receipts
2. parse_generic  — all other receipt types (maximal effort)
"""
import io
import re
from datetime import datetime
import pdfplumber
from bidi.algorithm import get_display


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF file."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)


# ═══════════════════════════════════════════════════════════════
# 1. MEHADRIN ONLINE — dedicated parser
# ═══════════════════════════════════════════════════════════════

def is_mehadrin_receipt(text: str) -> bool:
    """Check if this is a Mehadrin Online receipt."""
    return "mehadrinonline" in text.lower() or "service@monline.co.il" in text


def parse_mehadrin(text: str) -> list[dict]:
    """
    Parse a Mehadrin Online receipt.

    Mehadrin format — RAW line (reversed, RTL):
        total_price unit_price quantity product_name barcode line_num

    After bidi display:
        line_num  barcode  product_name  quantity  unit_price  total_price

    Examples (displayed):
        1  7290112495037  קוקומן כדורי דגנים בטעם שוק  1.00  22.90  22.90
        13 90000947       חציל ק"ג                       0.69   0.90   0.62

    Returns list of dicts: {code, name, quantity}
    """
    items = []
    seen_codes = set()
    lines = text.split("\n")

    for line in lines:
        line = line.strip()
        if len(line) < 10:
            continue

        display = get_display(line)

        # Skip header/footer lines
        skip_words = ["טלפון", "חשבונית", "תעודת", "ח.פ.", "סהכ", 'סה"כ',
                      "מע\"מ", "מ.ע.מ", "שולח", "נמען", "service@", ".co.il",
                      "mehadrin", "כתובת", "תאריך", "שעה"]
        if any(w in display for w in skip_words):
            continue

        # Find product code: barcode (12-14 digits) or Mehadrin fruit code (9xxxxxxx)
        code_match = re.search(r'\b(\d{12,14})\b', line)
        fruit_match = re.search(r'\b(9\d{6,7})\b', line)

        code = None
        if code_match:
            code = code_match.group(1)
        elif fruit_match:
            code = fruit_match.group(1)
        else:
            continue

        if code in seen_codes:
            continue
        seen_codes.add(code)

        # ── Extract the 3 decimal numbers (in RAW order: total, unit_price, qty) ──
        # RAW: 22.90 22.90 1.00 <name> <code> <num>
        # The THREE decimal numbers at the start (in raw) are: total, unit_price, quantity
        all_nums = re.findall(r'\b(\d+\.\d{2})\b', line)
        quantity = 1
        if len(all_nums) >= 3:
            try:
                qty_float = float(all_nums[2])
                if qty_float < 1:
                    quantity = round(qty_float, 2)
                else:
                    quantity = int(qty_float)
            except (ValueError, IndexError):
                quantity = 1
        elif len(all_nums) >= 1:
            for n_str in all_nums:
                try:
                    n = int(float(n_str))
                    if 1 <= n <= 200:
                        quantity = n
                        break
                except ValueError:
                    pass

        # ── Extract weight in GRAMS ──
        # Converts everything to grams:
        #   kg (*1000), gram (as-is), liter (*1000), ml (as-is)
        #   If no unit but quantity < 1 (fruits/veggies sold by kg) → qty*1000
        weight = 0
        weight_patterns = [
            (r'(\d+(?:\.\d+)?)\s*(?:ק"ג|קילוגרם|קילו)', 1000),
            (r'(\d+(?:\.\d+)?)\s*(?:גרם|גר\b)', 1),
            (r'(\d+(?:\.\d+)?)\s*(?:ליטר|ליט\'?|רטיל)', 1000),
            (r'(\d+(?:\.\d+)?)\s*(?:מ"ל|מיליליטר)', 1),
        ]
        for pattern, multiplier in weight_patterns:
            m = re.search(pattern, display)
            if m:
                try:
                    weight = round(float(m.group(1)) * multiplier)
                except ValueError:
                    pass
                break

        # Fruits/veggies (9xxxxxxx) sold by kg — convert quantity to grams
        if weight == 0 and code.startswith('9') and len(code) == 8 and isinstance(quantity, float):
            weight = round(quantity * 1000)
        # If quantity looks like kg (< 1) but no weight unit found
        elif weight == 0 and isinstance(quantity, float) and quantity < 1:
            weight = round(quantity * 1000)

        # ── Extract product name ──
        # The name is between the code and the 3 decimal numbers
        # In RAW: ... quantity <name> code num
        # In DISPLAY: num code <name> quantity ...

        # Work on RAW line (no bidi) — strip the three decimal numbers from the beginning
        raw_line = line

        # Remove the 3 leading decimal numbers (total, unit_price, quantity)
        for _ in range(3):
            raw_line = re.sub(r'^\s*\d+\.\d{2}\s*', '', raw_line, count=1)

        # Now raw_line should be: <product_name_in_reverse> <code> <line_num>
        # Remove the trailing code and line number
        raw_line = re.sub(r'\s+' + re.escape(code) + r'\s+\d{1,2}\s*$', '', raw_line)
        # Also try removing just the code
        raw_line = re.sub(r'\s+' + re.escape(code) + r'\s*$', '', raw_line)

        # Clean up
        raw_line = raw_line.strip()

        if not raw_line or len(raw_line) < 2:
            continue

        name = get_display(raw_line)

        # Filter out non-product names
        noise = ["תעודת", "משלוח", "חשבונית", "סהכ", 'סה"כ', "מע\"מ",
                 "מעמ", "טלפון", "פקס", "כתובת", "invoice", "receipt",
                 "אספקה", "הספקה", "דמי", "משלוח"]
        if any(n in name for n in noise) or len(name) < 3:
            continue

        # ── Remove unit markers from product name ──
        # Mehadrin appends unit info like "ק\"ג", "גרם", "ליטר", "מ\"ל", "יחידה" etc.
        # These are NOT part of the product name and should be stripped.
        unit_markers = [
            # kg
            r'\bק"ג\b', r'\bג"ק\b',
            # liter / gallon
            r'\bליטר\b', r'\bרטיל\b',
            r'\bליט\'?\.?\b', r'\b\'?\.?טיל\b',
            r'\bגלון\b', r'\bןולג\b',
            r'\bוא\'?ג\b', r'\bג\'?או\b',   # gallon abbreviation
            # ml
            r'\bמ"ל\b', r'\bל"מ\b',
            # gram (full + abbreviations)
            r'\bגרם\b', r'\bםרג\b',
            r'\bגר\'?\.?\b', r'\b\'?\.?רג\b',
            r'\bג\'\.?\b',                     # just 'ג' for gram
            # unit
            r'\bיחידה\b', r'\bהדיחי\b',
            r'\bיח\'\.?\b', r'\b\'?\.?חי\b',
            r'\bליחידה\b', r'\bהדיחיל\b',     # "per unit"
            r'\bיחידות\b', r'\bתודיחי\b',     # units (plural)
            # pack
            r'\bמארז\b', r'\bזראמ\b',
            # box / can
            r'\bקופסה\b', r'\bהספוק\b',
            r'\bקופסת\b', r'\bתספוק\b',
            r'\bפחית\b', r'\bתיחפ\b',        # can/tin
            r'\bפח\b', r'\bחפ\b',             # tin abbreviation
            # bottle
            r'\bבקבוק\b', r'\bקוקבב\b',
            # bag / sachet
            r'\bשקית\b', r'\bתיקש\b',
            # piece / bead
            r'\bיחל״צ\b', r'\bצ״לחי\b',      # piece abbreviation
        ]
        for pattern in unit_markers:
            name = re.sub(pattern, '', name)

        # Clean up extra spaces from unit removal
        name = re.sub(r'\s+', ' ', name).strip()

        # Remove stray single-character unit remnants at end of name
        # (e.g. 'ל' from 'מ\"ל', 'ג' from gram, 'א' etc.)
        # Only if preceded by a digit — that confirms it's a unit leftover
        name = re.sub(r'\s*\d+\s*[א-ת]\s*$', '', name)
        # Also remove trailing lone characters that are unit leftovers
        name = re.sub(r'\s*\d+\s*\'?\s*$', '', name)
        # Remove leftover number at end (e.g. "1.19" that was part of unit)
        name = re.sub(r'\s+\d+\.\d{2}\s*$', '', name)

        # Remove noise words like "מחיר ל..." leftovers
        name = re.sub(r'\bמחיר\b', '', name)
        name = re.sub(r'\bריחמ\b', '', name)  # reversed

        # Remove leading leftover numbers + english word (like "4 calm", "2 pack")
        name = re.sub(r'^\d+\s+[a-zA-Z]+\s*', '', name)
        # Remove leading english-only words BUT preserve product codes like TnX, XL
        # English words that are product brands (<=4 chars, all caps or mixed case)
        if not re.match(r'^[A-Za-z]{2,4}\s', name):
            name = re.sub(r'^[a-zA-Z]+\s+', '', name)
        else:
            # It's a brand name — keep it, just clean surrounding mess
            pass

        # Remove leftover unit abbreviations in RTL
        name = re.sub(r'\bל"ג\b', '', name)    # ml reversed
        name = re.sub(r'\bג"ל\b', '', name)
        # Remove "ל'ג" / "ג'ל" (jerry can unit), "ל'ט" / "ט'ל" (liter alt)
        name = re.sub(r'\bל\'ג\b', '', name)
        name = re.sub(r'\bג\'ל\b', '', name)
        name = re.sub(r'\bל\'ט\b', '', name)
        name = re.sub(r'\bט\'ל\b', '', name)

        # Remove trailing single-letter leftovers after cleanup
        # BUT preserve patterns like "מס' 8" (product number) — only strip
        # single letter if it's not part of "מס' X"
        name = re.sub(r'\s+[א-ת]\s*$', '', name)
        # Remove stray quotes and partial numbers left from unit removal
        name = re.sub(r'\s+\d+\s*\'+\s*', ' ', name)       # e.g. "240 '"
        # Remove trailing number only if it's clearly a unit leftover
        # But preserve "מס' 8" pattern (product numbering)
        name = re.sub(r'(?<!\')\s+\d+\.?\s*$', '', name)
        name = re.sub(r'\s+\d+\.\d+\s*$', '', name)        # float leftovers
        name = re.sub(r'\s+\'+\s*$', '', name)
        # Restore missing numbers after "מס'" if they were removed
        name = re.sub(r'\b(מס\')\s*$', r'\1', name)

        name = re.sub(r'\s+', ' ', name).strip()

        # Re-check length after unit removal
        if len(name) < 3:
            continue

        items.append({
            "code": code,
            "name": name,
            "quantity": quantity,
            "weight": weight,
        })

    return items


# ═══════════════════════════════════════════════════════════════
# 2. MAXIMAL PARSER — for all other receipt types
# ═══════════════════════════════════════════════════════════════

def parse_generic(text: str) -> list[dict]:
    """
    Maximal-effort parser for any receipt that isn't Mehadrin.

    Shuk City format — RAW line (reversed RTL):
        total  unit_price  qty_received  qty_sent  unit_type  product_name  code

    After bidi display:
        code  product_name  unit_type  qty_sent  qty_received  unit_price  total

    Special case: items not yet supplied have '----' instead of total & unit_price.
    Those still have qty_received as a plain integer.

    Returns list of dicts: {code, name, quantity}
    """
    items = []
    seen_codes = set()
    lines = text.split("\n")

    skip_words = [
        "חשבונית", "תעודת", "חולשמ", "השרומ", "עוסק", "invoice",
        "טלפון", "פקס", "כתובת", "סהכ", 'סה"כ', "סה״כ",
        "מע\"מ", "מעמ", "משלוח", "תאריך", "שעה", "מזומן",
        "אשראי", "קבלה", "תשלום", "מיקוד", "עיר",
        "מבצע", "הנחה", "אספקה", "הספקה", "רחוב", "דרך",
        "email", "co.il", "ישח",
    ]

    for line in lines:
        line = line.strip()
        if len(line) < 8:
            continue

        display = get_display(line)

        # Skip non-product / promo lines
        if any(w in display for w in skip_words):
            continue

        # Skip promo lines (מבצע)
        if "מבצע" in display:
            continue

        # Skip separator lines
        if re.match(r'^[-=]+$', line):
            continue

        # Find product code — barcode (12-14 digits) or internal code (5-8 digits)
        barcode_match = re.search(r'\b(\d{12,14})\b', line)
        internal_match = re.search(r'\b(\d{5,8})\b', line) if not barcode_match else None

        if barcode_match:
            code = barcode_match.group(1)
        elif internal_match:
            code = internal_match.group(1)
        else:
            continue

        if code in seen_codes:
            continue
        seen_codes.add(code)

        # ── Extract quantity ──
        # In RAW: total unit_price qty_received qty_sent ...
        # Normal case: all 4 are decimal numbers (X.XX)
        # Supplied=0 case: '----' '----' <qty_received_int> 0 ...
        all_nums = re.findall(r'\b(\d+\.\d{2})\b', line)
        quantity = 1

        if len(all_nums) >= 3:
            try:
                qty_val = int(float(all_nums[2]))
                if qty_val > 0:
                    quantity = qty_val
            except (ValueError, IndexError):
                pass
        else:
            # '----' case: look for the plain integer between '---- ----' and '0'
            # RAW: '---- ---- <qty_received> 0 ...'
            # Remove '----' strings, then find the first integer
            stripped = re.sub(r'----', ' ', line)
            int_nums = re.findall(r'\b(\d+)\b', stripped)
            for n_str in int_nums:
                n = int(n_str)
                # The qty_received is typically a small integer (1-50)
                # Skip large numbers (codes) and 0
                if 1 <= n <= 50:
                    quantity = n
                    break

        # ── Extract name from RAW line ──
        raw_line = line

        # Remove the 4 leading values (total, unit_price, qty_received, qty_sent)
        # They can be "X.XX" or "----"
        for _ in range(4):
            raw_line = re.sub(r'^\s*(?:\d+\.\d{2}|----|0)\s*', '', raw_line, count=1)

        # Remove the code from the end
        raw_line = re.sub(r'\s+' + re.escape(code) + r'\s*$', '', raw_line)

        # Skip clearly non-product lines (addresses, order numbers)
        if "הזמנה" in display or "דירה" in display or "רחוב" in display or "טלפון" in display:
            continue

        # Remove unit type markers: "יח", "קג", "גק"
        raw_line = re.sub(r'\b(?:יח|קג|גק)\b', ' ', raw_line)

        # Clean up
        raw_line = re.sub(r'\s+', ' ', raw_line).strip()

        # Remove single/double letter noise
        raw_line = re.sub(r'(?<!\S)[a-zA-Z]{1,2}(?!\S)', ' ', raw_line)
        raw_line = re.sub(r'\s+', ' ', raw_line).strip()

        name = get_display(raw_line) if raw_line else ""

        if not name or len(name) < 2:
            continue
        if any(w in name for w in skip_words):
            continue

        # Remove standalone numeric fragments
        name = re.sub(r'(?<!\S)[\d.]{1,6}(?!\S)', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()

        if len(name) < 3:
            continue

        items.append({
            "code": code,
            "name": name,
            "quantity": quantity,
            "weight": 0,
        })

    return items


# ═══════════════════════════════════════════════════════════════
# 3. ROUTER — dispatches to the correct parser
# ═══════════════════════════════════════════════════════════════

def _extract_date(text: str) -> str | None:
    """
    Try to find a purchase date hidden in the receipt text.
    Returns ISO date string (YYYY-MM-DD) or None.
    """
    # Typical patterns in RTL receipts after bidi display:
    #   17:00 5/01/21    (Shuk City: hour + DD/MM/YY)
    #   23:22 4/01/21    (Mehadrin:   hour + DD/MM/YY)
    #   2024-01-15       (already ISO)
    #
    # We look for dates with separators '/' or '-'
    # Pattern:  DD/MM/YY  or  DD/MM/YYYY  or  YYYY-MM-DD

    # 1) DD/MM/YY or DD/MM/YYYY
    matches = re.findall(r'\b(\d{1,2})[/](\d{1,2})[/](\d{2,4})\b', text)
    for d, m, y in matches:
        try:
            day, month = int(d), int(m)
            year = int(y)
            if year < 100:
                year += 2000
            if 1 <= day <= 31 and 1 <= month <= 12 and 2020 <= year <= 2030:
                return f"{year}-{month:02d}-{day:02d}"
        except ValueError:
            continue

    # 2) YYYY-MM-DD (already ISO, fallback)
    iso = re.findall(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
    for y, m, d in iso:
        try:
            year, month, day = int(y), int(m), int(d)
            if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year}-{month:02d}-{day:02d}"
        except ValueError:
            continue

    return None


def parse_receipt(text: str) -> tuple[list[dict], str | None]:
    """
    Parse any receipt. Automatically detects type and uses the best parser.

    Returns (list of dicts: {code, name, quantity}, date: ISO str | None)
    """
    if is_mehadrin_receipt(text):
        items = parse_mehadrin(text)
    else:
        items = parse_generic(text)

    receipt_date = _extract_date(text)
    return items, receipt_date
