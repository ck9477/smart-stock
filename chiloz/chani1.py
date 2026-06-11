import pdfplumber
import re
from pathlib import Path
from bidi.algorithm import get_display

# -----------------------------
# LOAD INVOICE
# -----------------------------
def extract_single_invoice(file_path):
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

    data = parse_invoice_text(text)
    data["file_name"] = file_path.name
    return data

# -----------------------------
# EXTRACT PRODUCT NAME
# -----------------------------
def extract_product_name(text, code):
    text = text.replace(code, "")
    text = re.sub(r'\d+\.\d+', '', text)
    text = re.sub(r'\d+%', '', text)

    junk = ["חי", "חשי", "רג", "יש", "ק", "ג"]

    for j in junk:
        text = re.sub(rf'\b{j}\b', '', text)

    text = re.sub(r'[-*/"(),.:]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    text = get_display(text)

    return text if len(text) > 2 else ""

# -----------------------------
# EXTRACT QUANTITY
# -----------------------------
def extract_quantity(text):
    match = re.search(r'\b(\d{1,2})\s+\1\b', text)
    if match:
        return int(match.group(1)), "units"

    numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)

    for n in numbers:
        try:
            v = float(n)
            if 0 < v <= 200:
                return int(v), "units"
        except:
            continue

    return 1, "units"

# -----------------------------
# EXTRACT WEIGHT
# -----------------------------
def extract_weight_grams(name):
    patterns = [
        r'(\d{2,5})\s*גרם',
        r'(\d{2,5})\s*ג\b',
        r'(\d+(?:\.\d+)?)\s*קג',
        r'(\d+(?:\.\d+)?)\s*ק"ג',
        r'(\d+(?:\.\d+)?)\s*ליטר',
        r'(\d+(?:\.\d+)?)\s*ל\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, name, re.IGNORECASE)

        if match:
            value = float(match.group(1))

            if "קג" in pattern or 'ק"ג' in pattern or "ליטר" in pattern:
                return int(value * 1000)

            return int(value)

    numbers = re.findall(r'\b(\d{2,5})\b', name)

    for n in numbers:
        n = int(n)

        if 50 <= n <= 2000:
            return n

    return None

# -----------------------------
# FILTER REAL PRODUCTS
# -----------------------------
def is_real_product(name):
    blacklist = [
        "טלפון", "פקס", "כתובת", "עוסק", "מורשה",
        "משלוח", "תעודת", "הזמנה", "חשבונית", "מסמך",
        "קבלה", "סהכ", 'סה"כ', "מעמ", 'מע"מ',
        "tax", "total", "invoice", "receipt"
    ]

    name_lower = name.lower()

    for word in blacklist:
        if word.lower() in name_lower:
            return False

    if len(name.strip()) < 3:
        return False

    if not re.search(r'[a-zA-Zא-ת]', name):
        return False

    return True

# -----------------------------
# PARSE INVOICE
# -----------------------------
def parse_invoice_text(text):
    lines = text.splitlines()

    items = []
    seen = set()

    code_pattern = re.compile(r'\b(\d{6,14})\b')

    skip_words = [
        "חשבונית",
        "invoice",
        "receipt",
        "טלפון",
        "פקס",
        "כתובת",
        "סהכ",
        "total",
        "tax"
    ]

    for line in lines:
        line = line.strip()

        if len(line) < 6:
            continue

        if any(w in line.lower() for w in skip_words):
            continue

        codes = code_pattern.findall(line)

        if not codes:
            continue

        code = codes[0]

        if code in seen:
            continue

        seen.add(code)

        name = extract_product_name(line, code)

        if not name or not is_real_product(name):
            continue

        qty, unit = extract_quantity(line)
        weight = extract_weight_grams(name)

        items.append({
            "code": code,
            "name": name,  # נשאר בדיוק כפי שחולץ
            "quantity": qty,
            "unit_type": unit,
            "weight_grams": weight
        })

    return {"items": items}

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    file_path = r"H:\smart-stock-project\attachments (13)\30000219419.pdf"

    result = extract_single_invoice(file_path)

    print(f"\nחשבונית: {result['file_name']}")
    print("-" * 60)

    for item in result["items"]:
        print(
            f"קוד: {item['code']} | "
            f"מוצר: {item['name']} | "
            f"כמות: {item['quantity']} | "
            f"סוג: {item['unit_type']} | "
            f"משקל: {item['weight_grams']}"
        )