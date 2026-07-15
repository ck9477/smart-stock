"""
Receipt Parser — dedicated extraction functions per receipt type.

1. parse_mehadrin  — Mehadrin Online receipts
2. parse_generic  — all other receipt types
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
# SHARED HELPERS
# ═══════════════════════════════════════════════════════════════

# Codes to never treat as products
_KNOWN_BAD_CODES = {
    '30000219419', '30000199410', '520022732', '9253567', '035702892',
    '0548494994', '1800071300', '7536333', '9483838', '071300',
    '00000', '0008', '3599', '20380', '40417', '47036', '73718',
    '12532', '86250', '83260', '9219407',
}
_PROMO_PREFIXES = ('256', '257', '260', '253', '255')

# Unit patterns to remove from names (bidirectional)
_UNIT_PATTERNS = [
    r'\bק"ג\b', r'\bג"ק\b', r'\bגק\b', r'\bקג\b', r'\bקילו\b',
    r'\bליטר\b', r'\bרטיל\b', r'\bגלון\b', r'\bליט\'?\.?\b',
    r'\bמ"ל\b', r'\bל"מ\b', r'\bגרם\b', r'\bגר\'?\.?\b',
    r'\bיחידה\b', r'\bהדיחי\b', r'\bחי\b', r'\bיח\b', r'\bיח\'\.?\b',
    r'\bליחידה\b', r'\bהדיחיל\b', r'\bיחידות\b', r'\bתודיחי\b',
    r'\bמארז\b', r'\bחבילה\b', r'\bקופסה\b', r'\bקופסת\b',
    r'\bפחית\b', r'\bבקבוק\b', r'\bשקית\b', r'\bקילוגרם\b',
    r'\bגל\b', r'\bלג\b', r'\bםרג\b', r'\bג\'ל\b', r'\bל\'ג\b',
    r'\bג"ל\b', r'\bל"ג\b', r'\bט\'ל\b', r'\bל\'ט\b',
]


def _find_code_in_line(line: str) -> str | None:
    """Extract product code from a line: barcode > fruit code > internal code."""
    # Barcode (12-14 digits)
    m = re.search(r'\b(\d{12,14})\b', line)
    if m:
        return m.group(1)
    # Fruit/veggie (9 + 6-8 digits)
    m = re.search(r'\b(9\d{6,8})\b', line)
    if m:
        return m.group(1)
    # Internal (5-10 digits, exclude promos and known-bad)
    for m in re.finditer(r'\b(\d{5,10})\b', line):
        c = m.group(1)
        if c in _KNOWN_BAD_CODES:
            continue
        if c.startswith(_PROMO_PREFIXES):
            continue
        return c
    return None


def _clean_product_name(name: str) -> str:
    """Remove units, numbers, and noise from product name."""
    for pat in _UNIT_PATTERNS:
        name = re.sub(pat, '', name)
    name = re.sub(r'\s+', ' ', name).strip()

    # Remove trailing numbers / unit fragments
    name = re.sub(r'\s+\d+(?:\.\d+)?\s*[א-ת]*\s*$', '', name)
    name = re.sub(r'\s+\d+%?\s*$', '', name)
    name = re.sub(r'\s+[א-תA-Za-z]\s*$', '', name)
    name = re.sub(r'^\s*[א-תA-Za-z]\s+', '', name)

    # Remove special chars except Hebrew, English, digits, apostrophe, dash, plus, space
    name = re.sub(r"[^֐-׿a-zA-Z0-9'\-+\s]", ' ', name)

    # Remove noise words
    for w in ['מחיר', 'ריחמ', 'מבצע', 'עצבמ']:
        name = re.sub(r'\b' + w + r'\b', '', name)

    name = name.replace('*', '').replace('"', '').replace('"', '')
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def _extract_weight(display: str) -> int:
    """Extract weight in grams from display text."""
    patterns = [
        (r'(\d+(?:\.\d+)?)\s*(?:ק"ג|קילוגרם|קילו|גק|ג"ק)', 1000),
        (r'(\d+(?:\.\d+)?)\s*(?:גרם|גר\b|םרג|רג)', 1),
        (r'(\d+(?:\.\d+)?)\s*(?:ליטר|ליט\'?|רטיל|ריטיל)', 1000),
        (r'(\d+(?:\.\d+)?)\s*(?:מ"ל|מיליליטר|ל"מ)', 1),
    ]
    for pattern, multiplier in patterns:
        m = re.search(pattern, display)
        if m:
            try:
                return round(float(m.group(1)) * multiplier)
            except ValueError:
                pass
    return 0


# ═══════════════════════════════════════════════════════════════
# 1. MEHADRIN ONLINE — dedicated parser
# ═══════════════════════════════════════════════════════════════

def is_mehadrin_receipt(text: str) -> bool:
    """Check if this is a Mehadrin Online receipt."""
    if "mehadrinonline" in text.lower() or "service@monline.co.il" in text:
        return True

    # Detect by line structure:  X.XX  X.XX  N  N  <unit>  <name>  <code>
    mehadrin_line = re.compile(
        r'(?:\d+\.\d{2}|----)\s+(?:\d+\.\d{2}|----)\s+\d+\s+\d+\s+\S+\s+.{2,}?\s+\d{5,14}\s*$',
        re.MULTILINE
    )
    return len(mehadrin_line.findall(text)) >= 3


def parse_mehadrin(text: str) -> list[dict]:
    """
    Parse a Mehadrin Online receipt.

    RAW format (space-separated, reversed RTL):
        total_price  unit_price  qty_supplied  qty_sent  unit_type  ...product_name...  code

    '----' means unsupplied → qty=0.
    """
    items = []
    lines = text.split("\n")

    RE_DECIMAL = re.compile(r'^\d+\.\d{2}$')
    RE_INT = re.compile(r'^\d+$')
    RE_DASH = re.compile(r'^----$')
    RE_NEG = re.compile(r'^-\d+\.\d{2}$')
    RE_PROMO = re.compile(r':\s*מבצע|:\s*עצבמ')
    RE_SEP = re.compile(r'^-{5,}$')

    skip_display = {
        "טלפון", "חשבונית", "תעודת", "ח.פ.", "סהכ", 'סה"כ',
        "מע\"מ", "מ.ע.מ", "שולח", "נמען", "service@", ".co.il",
        "mehadrin", "כתובת", "תאריך", "שעה", "עוסק", "קסוע",
        "מורשה", "השרומ", "חולשמ", "הקפסה", "אספקה", "פקס",
        "מיקוד", "דואר", "רחוב", "דירה", "עיר", "הזמנה",
        "דמי", "משלוח", "מבצע", "הנחה", "אשראי", "מזומן",
        "הנמזה", "הנומת", "רוזא", "תונח", "הרעה",
        "ןופלט", "סקפ", "הריד", "בייחל", "המייקתה", "חיש",
        "השיח", "םוכס", "לכה", "Page", "www.", "info@",
    }

    for line in lines:
        line = line.strip()
        if len(line) < 10 or RE_SEP.match(line) or RE_PROMO.search(line):
            continue
        if re.match(r'^\d{1,2}:\d{2}', line):
            continue

        display = get_display(line)
        if any(w in display for w in skip_display):
            continue

        tokens = line.split()
        if len(tokens) < 5:
            continue

        # Skip negative-price lines (discounts)
        if RE_NEG.match(tokens[0]):
            continue

        # ── Find code (last valid numeric token) ──
        code = None
        for i in range(len(tokens) - 1, -1, -1):
            c = _find_code_in_line(tokens[i])
            if c and len(c) >= 5:
                code = c
                break
        if not code:
            continue

        # ── Quantity ──
        quantity = 1
        dash_count = sum(1 for t in tokens[:4] if RE_DASH.match(t))
        if dash_count >= 2:
            quantity = 0
        elif len(tokens) >= 3:
            t0, t1, t2 = tokens[0], tokens[1], tokens[2]
            if RE_DECIMAL.match(t0) and RE_DECIMAL.match(t1):
                # t2 is either decimal qty or integer qty
                if RE_DECIMAL.match(t2):
                    qty_f = float(t2)
                    quantity = int(qty_f) if qty_f == int(qty_f) else round(qty_f, 2)
                elif RE_INT.match(t2) and not t2.startswith(('256', '257', '260')):
                    quantity = int(t2)

        # ── Name ──
        # After first 4 tokens (price fields), before the code
        name_start = 4
        # Find code index
        code_idx = next((i for i, t in enumerate(tokens) if t == code), len(tokens) - 1)
        name_tokens = []
        for i in range(name_start, code_idx):
            t = tokens[i]
            if t in ('יח', 'קג', 'חי', 'גק'):
                continue
            if re.match(r'^\d{1,4}$', t) or re.match(r'^\d{1,3}%$', t):
                continue
            if len(t) <= 1:
                continue
            name_tokens.append(t)

        raw_name = ' '.join(name_tokens)
        if not raw_name:
            continue

        name = get_display(raw_name)
        name = _clean_product_name(name)
        if len(name) < 2:
            continue

        weight = _extract_weight(display)

        items.append({
            "code": code,
            "name": name,
            "quantity": quantity,
            "weight": weight,
        })

    return items


# ═══════════════════════════════════════════════════════════════
# 2. GENERIC PARSER — for all other receipt types (Yohananof, Shuk City, etc.)
# ═══════════════════════════════════════════════════════════════

def parse_generic(text: str) -> list[dict]:
    """
    Maximal-effort parser for any non-Mehdarin receipt.

    Approach:
      1. Find product code (barcode/fruit/internal) per line
      2. Find quantity (integer close to the name)
      3. Extract name between leading numeric/price fields and the code
      4. Deduplicate: same code → merge quantities
    """
    items: list[dict] = []
    seen: dict[str, int] = {}  # code -> index in items list
    lines = text.split("\n")

    skip_display = {
        "חשבונית", "תעודת", "חולשמ", "השרומ", "עוסק", "invoice",
        "טלפון", "פקס", "כתובת", "סהכ", 'סה"כ', "סה״כ",
        "מע\"מ", "מעמ", "משלוח", "תאריך", "שעה", "מזומן",
        "אשראי", "קבלה", "תשלום", "מיקוד", "עיר",
        "הנחה", "אספקה", "הקפסה", "רחוב", "דרך", "הזמנה",
        "email", "co.il", "ישח", "קסוע", "רוזא", "תונח",
        "הנמזה", "הנומת", "הרעה", "הריד", "בייחל",
        "המייקתה", "חיש", "השיח", "www.", "Page", "info@",
    }
    skip_rev = {"םוכס", "לכה", 'ל"ה'}

    for line in lines:
        line = line.strip()
        if len(line) < 8:
            continue

        display = get_display(line)

        # Skip non-product lines
        if any(w in display for w in skip_display):
            continue
        if any(w in line for w in skip_rev):
            continue
        if re.match(r'^[-=]+$', line) or re.match(r'^\d{1,2}:\d{2}', line):
            continue
        if "מבצע" in display or "עצבמ" in line:
            continue
        if not re.search(r'[א-ת]', display) and not re.search(r'[א-ת]', line):
            continue
        # Skip negative-price lines
        if re.match(r'^-\d+', line.strip()):
            continue

        # ── Find code ──
        code = _find_code_in_line(line)
        if not code:
            continue

        # ── Quantity ──
        quantity = _find_generic_quantity(line, code)

        # ── Name ──
        name = _extract_generic_name(line, display, code)
        if not name or len(name) < 2:
            continue

        name = _clean_product_name(name)
        if len(name) < 2:
            continue

        # ── Deduplicate by code (merge quantities) ──
        if code in seen:
            items[seen[code]]["quantity"] += quantity
        else:
            seen[code] = len(items)
            items.append({
                "code": code,
                "name": name,
                "quantity": quantity,
                "weight": 0,
            })

    return items


def _find_generic_quantity(line: str, code: str) -> int | float:
    """Find quantity in a non-Mehdarin product line."""
    stripped = re.sub(r'\b' + re.escape(code) + r'\b', ' ', line)
    stripped = re.sub(r'ILS', ' ', stripped, flags=re.IGNORECASE)
    stripped = re.sub(r'\d+\.\d{1,2}ILS', ' ', stripped, flags=re.IGNORECASE)

    # ── הורדת מספרים ששייכים למשקל/אחוז/נפח ──
    stripped = re.sub(r'\b\d{1,4}\s*Z\b', ' ', stripped)
    stripped = re.sub(r'\b\d{1,3}\s*%', ' ', stripped)
    stripped = re.sub(r'\b\d{2,4}\s*ML\b', ' ', stripped)
    stripped = re.sub(r'\b\d+(?:\.\d+)?\s*L\b', ' ', stripped)
    stripped = re.sub(r'\b\d+(?:\.\d+)?\s*(?:ק\"ג|גרם|ליטר|מ\"ל)\b', ' ', stripped)

    all_nums = re.findall(r'(\d+(?:\.\d+)?)', stripped)
    parsed = []
    for n_str in all_nums:
        try:
            n = float(n_str)
            if n > 0:
                parsed.append(n)
        except ValueError:
            continue

    if not parsed:
        return 1

    # מחירי מכולה (עם נקודה עשרונית) — נוציא אותם מהרשימה
    non_prices = [n for n in parsed if not (0 < n < 1000 and n != int(n) and n == round(n, 2))]

    # קודים פנימיים — מספרים שמופיעים מיד לפני הברקוד (דפוס "NNN 7290...")
    code_pos = line.find(code)
    internal_code_set = set()
    if code_pos > 0:
        prefix = line[:code_pos].strip()
        for m in re.finditer(r'\b(\d{2,6})\b', prefix):
            internal_code_set.add(int(m.group(1)))

    # נעדיף מספרים שלמים קטנים (1-12) שאינם קוד פנימי
    candidates = [n for n in non_prices if 1 <= n <= 12 and n == int(n) and int(n) not in internal_code_set]
    if candidates:
        return int(candidates[-1])

    # קטנים מ-30, לא קוד פנימי
    candidates = [n for n in non_prices if 1 <= n <= 30 and n == int(n) and int(n) not in internal_code_set]
    if candidates:
        return int(candidates[-1])

    # Fallback: any reasonable number (לא קוד פנימי)
    candidates = [n for n in non_prices if 0.1 <= n <= 80 and int(n) not in internal_code_set]
    if candidates:
        n = candidates[-1]
        return int(n) if n == int(n) else n

    return 1


def _extract_generic_name(line: str, display: str, code: str) -> str:
    """Extract product name from generic receipt line.

    The name is on the OPPOSITE side of the barcode in the line.
    If barcode is at the end (LTR), name is at the beginning → use display.
    If barcode is at the beginning, name is after it → use line.
    """
    # ── שלב 1: חיתוך — לוקחים את מה שבצד הנגדי של הקוד ──
    idx = line.rfind(code)
    if idx < 0:
        # בדיקה גם ב-display (RTL — הקוד מופיע בהתחלה)
        idx = display.rfind(code)
        if idx < 0:
            return ""
        raw = display[idx + len(code):]
    elif idx > len(line) * 0.4:
        # הקוד בחצי הימני (סוף ב־LTR, התחלה ב־RTL)
        # → השם בתחילת השורה (לפני הקוד)
        raw = line[:idx]
    else:
        # הקוד בחצי השמאלי (התחלה ב־LTR)
        # → השם אחרי הקוד
        raw = line[idx + len(code):]

    # ── שלב 2: הסרת "80Z", "60%", "750ML", "1.5L" ליד השם ──
    raw = re.sub(r'\b\d{1,4}\s*Z\b', ' ', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\b\d{1,3}\s*%', ' ', raw)
    raw = re.sub(r'\b\d{2,4}\s*ML\b', ' ', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\b\d+(?:\.\d+)?\s*L\b', ' ', raw, flags=re.IGNORECASE)
    raw = re.sub(r'\b\d+(?:\.\d+)?\s*ק"ג\b', ' ', raw)
    raw = re.sub(r'\b\d+(?:\.\d+)?\s*גרם\b', ' ', raw)
    raw = re.sub(r'\b\d+(?:\.\d+)?\s*ליטר\b', ' ', raw)

    # ── שלב 3: הסרת מחירים (X.XX או X.X) ──
    raw = re.sub(r'\b\d+\.\d{1,2}\b', ' ', raw)

    # ── שלב 4: הסרת ILS ──
    raw = re.sub(r'\bILS\b', ' ', raw, flags=re.IGNORECASE)

    # ── שלב 5: הסרת ברקודים/קודים (12-14 ספרות) ──
    raw = re.sub(r'\b\d{12,14}\b', ' ', raw)

    # ── שלב 6: הסרת מספרים שלמים בתחילת המחרוזת ──
    for _ in range(6):
        raw = re.sub(r'^\s*\d+\s+', ' ', raw)

    # ── שלב 7: הסרת מילות יחידה/משקל בתחילת השם ──
    raw = re.sub(
        r'^\s*(?:מארז|חבילה|קופסה|קופסת|פחית|בקבוק|שקית|שלישיית|רביעיית|שמינייה|זוג)\s+',
        ' ', raw
    )

    # ── שלב 8: הסרת תו בודד (אנגלית או עברית) בתחילת המחרוזת ──
    raw = re.sub(r'^\s*[A-Za-z]\s+', ' ', raw)
    raw = re.sub(r'^\s*[א-ת]\s+', ' ', raw)

    # ── שלב 9: הסרת סימנים מיוחדים בתחילת המחרוזת ──
    raw = re.sub(r'^\s*[%*\-+.,;:!?"\')\]}>]+\s*', ' ', raw)

    # ── שלב 10: ניקוי רווחים כפולים ──
    raw = re.sub(r'\s+', ' ', raw).strip()

    # ── המרה ל-display (לוקח תוים עבריים) ──
    heb = re.findall(r'[֐-׿]+', raw)
    if heb:
        result = ' '.join(heb)
    else:
        result = get_display(raw)

    return result.strip() if result else ""


# ═══════════════════════════════════════════════════════════════
# 3. DATE EXTRACTION & ROUTER
# ═══════════════════════════════════════════════════════════════

def _extract_date(text: str) -> str | None:
    """Find purchase date in receipt text. Returns ISO string or None."""
    # DD/MM/YY or DD/MM/YYYY
    for d, m, y in re.findall(r'\b(\d{1,2})[/](\d{1,2})[/](\d{2,4})\b', text):
        try:
            day, month, year = int(d), int(m), int(y)
            if year < 100:
                year += 2000
            if 1 <= day <= 31 and 1 <= month <= 12 and 2020 <= year <= 2030:
                return f"{year}-{month:02d}-{day:02d}"
        except ValueError:
            continue

    # YYYY-MM-DD
    for y, m, d in re.findall(r'\b(\d{4})-(\d{2})-(\d{2})\b', text):
        try:
            year, month, day = int(y), int(m), int(d)
            if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year}-{month:02d}-{day:02d}"
        except ValueError:
            continue

    return None


def parse_receipt(text: str) -> tuple[list[dict], str | None]:
    """
    Parse any receipt. Auto-detects type and delegates.
    Returns (items, date).
    """
    if is_mehadrin_receipt(text):
        items = parse_mehadrin(text)
    else:
        items = parse_generic(text)

    return items, _extract_date(text)
