"""
Receipt Parser — dedicated extraction functions per receipt type.

1. parse_mehadrin  — Mehadrin Online receipts
2. parse_generic  — all other receipt types (maximal effort)
"""
import io
import re
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

        # ── Extract the 3 decimal numbers (in RAW order: total, unit, qty) ──
        # RAW: 22.90 22.90 1.00 <name> <code> <num>
        # The THREE decimal numbers at the start (in raw) are: total, unit_price, quantity
        # We want the THIRD one (quantity) — in raw order it's the one closest to the name
        all_nums = re.findall(r'\b(\d+\.\d{2})\b', line)
        quantity = 1
        if len(all_nums) >= 3:
            try:
                qty_float = float(all_nums[2])
                # For fruits/veggies, quantity is in kg (e.g. 0.69)
                # Keep as float if < 1, otherwise round to int
                if qty_float < 1:
                    quantity = round(qty_float, 2)
                else:
                    quantity = int(qty_float)
            except (ValueError, IndexError):
                quantity = 1
        elif len(all_nums) >= 1:
            # Fallback: try to find a reasonable quantity
            for n_str in all_nums:
                try:
                    n = int(float(n_str))
                    if 1 <= n <= 200:
                        quantity = n
                        break
                except ValueError:
                    pass

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
                 "אספקה", "הספקה"]
        if any(n in name for n in noise) or len(name) < 3:
            continue

        items.append({
            "code": code,
            "name": name,
            "quantity": quantity,
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
        })

    return items


# ═══════════════════════════════════════════════════════════════
# 3. ROUTER — dispatches to the correct parser
# ═══════════════════════════════════════════════════════════════

def parse_receipt(text: str) -> list[dict]:
    """
    Parse any receipt. Automatically detects type and uses the best parser.

    Returns list of dicts: {code, name, quantity}
    """
    if is_mehadrin_receipt(text):
        return parse_mehadrin(text)
    return parse_generic(text)
