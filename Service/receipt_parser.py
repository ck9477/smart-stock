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

        # Shuk City raw format: total  unit_price  qty_received  qty_sent  unit_type  name  code

        # (all four leading values are .XX decimal strings or '----')

        #

        # Problem: some receipts have integer-only quantities (not .XX formatted),

        # which breaks the positional logic when we only match \d+\.\d{2}.

        # So we tokenize the whole raw line into "value units" — either a decimal,

        # a '----' dummy, or an integer.

        #

        # Strategy: find ALL value-like tokens at the start of the line (up to 4),

        # and use the THIRD one (qty_received) as quantity.

        # If the third token doesn't parse to a reasonable quantity, scan all tokens

        # for the best candidate (integer > 0, ≤ 200 that isn't obviously a price).


        # Tokenize the raw line into value units (decimal, '----', or standalone int)

        value_tokens = re.findall(r'\b(?:\d+\.\d{2}|----|\d+)\b', line)


        quantity = 1


        # Try the positional approach first: token[2] should be qty_received

        if len(value_tokens) >= 3:

            candidate = value_tokens[2]

            if candidate != '----':

                try:

                    qty_float = float(candidate)

                    if qty_float == int(qty_float) and 1 <= qty_float <= 200:

                        # Integer quantity (e.g. "4")

                        quantity = int(qty_float)

                    elif qty_float < 1:

                        # Fractional quantity (e.g. "0.69" kg for produce)

                        quantity = round(qty_float, 2)

                    elif 1 < qty_float <= 200:

                        # Still reasonable as quantity

                        quantity = int(qty_float)

                except (ValueError, IndexError):

                    pass


        # If positional approach gave us 1 (default), try to find ANY reasonable quantity

        # among the value tokens, avoiding obvious prices (numbers that look like .XX format

        # with values typical for prices: 5-500 with .90/.99/.50 endings).

        if quantity == 1:

            for token in value_tokens:

                if token == '----':

                    continue

                try:

                    val = float(token)

                except ValueError:

                    continue

                if val == int(val) and 1 <= val <= 200:

                    # Integer found — but filter out codes (5+ digits)

                    if len(token.replace('.', '')) <= 3:

                        quantity = int(val)

                        break

                elif val < 1 and val > 0:

                    # Fractional quantity (produce sold by weight)

                    quantity = round(val, 2)

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


        # Remove unit type markers — single-word abbreviations (raw RTL)

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


        # Remove standalone numeric fragments (price leftovers, single numbers)

        name = re.sub(r'(?<!\S)[\d.]{1,6}(?!\S)', ' ', name)

        name = re.sub(r'\s+', ' ', name).strip()


        # ── Remove unit markers & weight/size suffixes from product name ──

        # These are NOT part of the product name — they describe the package.

        # Same comprehensive list as parse_mehadrin uses.

        # Define unit marker patterns that work with BOTH:

        # - Standard ASCII quotes (raw PDF text)

        # - Hebrew punctuation quotes (after fix_hebrew_reversal converts them)

        # We use character classes [\"״] and [\'׳] throughout.


        unit_markers = [

            # IMPORTANT: longer patterns MUST come before shorter ones!

            # Otherwise e.g. r'\bג[\'׳]\.?\b' matches the 'ג part of 'ג'ל',

            # leaving lone 'ל' behind.

            #

            # kg

            r'\bק["״]ג\b', r'\bג["״]ק\b',

            # liter / gallon (multi-char first)

            r'\bליטר\b', r'\bרטיל\b',

            r'\bליט[\'׳]?\.?\b', r'\b\'?\.?טיל\b',

            r'\bגלון\b', r'\bןולג\b',

            r'\bוא[\'׳]?ג\b', r'\bג[\'׳]?או\b',

            # ml

            r'\bמ["״]ל\b', r'\bל["״]מ\b',

            r'\bמ["״\'׳]?ל\b', r'\bל["״\'׳]?מ\b',

            # RTL reversed gallon + liter patterns (multi-char before single-char)

            r'\bג["״]ל\b', r'\bל["״]ג\b',

            r'\bג[\'׳]ל\b', r'\bל[\'׳]ג\b',

            r'\bל[\'׳]ט\b', r'\bט[\'׳]ל\b',

            # gram — full word and longer abbreviations FIRST

            r'\bגרם\b', r'\bםרג\b',

            r'\bגר[\'׳]?\.?\b', r'\b\'?\.?רג\b',

            r'\bגר\b',

            r'\bג[\'׳]\.?\b',                   # shortest gram abbrev — LAST

            # unit — longer first

            r'\bיחידה\b', r'\bהדיחי\b',

            r'\bליחידה\b', r'\bהדיחיל\b',

            r'\bיחידות\b', r'\bתודיחי\b',

            r'\bיח[\'׳]\.?\b', r'\b\'?\.?חי\b',

            # pack

            r'\bמארז\b', r'\bזראמ\b',

            # box / can

            r'\bקופסה\b', r'\bהספוק\b',

            r'\bקופסת\b', r'\bתספוק\b',

            r'\bפחית\b', r'\bתיחפ\b',

            r'\bפח\b', r'\bחפ\b',

            # bottle

            r'\bבקבוק\b', r'\bקוקבב\b',

            # bag / sachet

            r'\bשקית\b', r'\bתיקש\b',

            # piece / bead

            r'\bיחל["״]צ\b', r'\bצ["״]לחי\b',

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

        if not re.match(r'^[A-Za-z]{2,4}\s', name):

            name = re.sub(r'^[a-zA-Z]+\s+', '', name)


        # Remove trailing single-letter leftovers after cleanup

        # (RTL reversed unit forms were already removed in unit_markers above)

        name = re.sub(r'\s+[א-ת]\s*$', '', name)

        # Remove stray quotes and partial numbers left from unit removal

        name = re.sub(r'\s+\d+\s*\'+\s*', ' ', name)       # e.g. "240 '"

        # Remove trailing number only if it's clearly a unit leftover

        name = re.sub(r'(?<!\')\s+\d+\.?\s*$', '', name)

        name = re.sub(r'\s+\d+\.\d+\s*$', '', name)        # float leftovers

        name = re.sub(r'\s+\'+\s*$', '', name)

        # Remove "מס' X" / "מס'" pattern — product numbering, not part of name

        name = re.sub(r'\bמס\'\s*\d*\s*', '', name)


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
