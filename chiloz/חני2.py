import pdfplumber
import re
from pathlib import Path


def extract_single_invoice(file_path):
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"The file does not exist: {file_path}")

    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

    data = parse_invoice_text(text)
    data["file_name"] = file_path.name
    return data


def fix_rtl_text(text):
    words = text.split()
    return " ".join(w[::-1] for w in words[::-1])


def clean_product_name(text):
    # לא מוחקים מספרים בצורה אגרסיבית כדי לא לשבור OCR
    text = re.sub(r'\d+(?:\.\d+)?', ' ', text)

    # תיקון שיבושי רווחים
    text = re.sub(r'\s+', ' ', text)

    # יחידות מידה בלבד (לא פוגע במילים אחרות)
    units = {"יח", "יח׳", "יח'", "גרם", "גר", "ג", "קג", "ק\"ג", "ליטר", "ל", "מל", "מ\"ל"}

    words = text.split()
    cleaned = []

    for w in words:
        w_clean = w.strip()

        # אם זו יחידה בלבד -> מדלגים
        if w_clean in units:
            continue

        # אם יחידה נדבקה לסוף מילה (למשל שומשוםג)
        for u in units:
            if w_clean.endswith(u) and len(w_clean) > len(u):
                w_clean = w_clean[:-len(u)]

        cleaned.append(w_clean)

    return " ".join(cleaned).strip()


def parse_invoice_text(text):
    data = {"items": []}

    lines = text.splitlines()

    code_pattern = re.compile(r'\b\d{6,14}\b')
    num_pattern = re.compile(r'\d+(?:\.\d+)?')

    skip_words = [
        "טלפון", "פקס", "אימייל", "דואר", "תאריך", "סה", "מע\"מ",
        "חשבונית", "קבלה", "שעה", "פרטים", "ח.פ", "דף",
        "עוסק", "מורשה", "הזמנה", "העתק", "בפקסימיליה",
        "כניסה", "רחוב"
    ]

    for line in lines:
        line = line.strip()

        if not line or len(line) < 8:
            continue

        if any(w in line for w in skip_words):
            continue

        if "מבצע" in line:
            continue

        codes = code_pattern.findall(line)
        if not codes:
            continue

        code = codes[-1]

        clean_line = line.replace(code, "").strip()
        nums = num_pattern.findall(clean_line)

        if len(nums) < 2:
            continue

        try:
            quantity = float(nums[-2])
            weight_grams = float(nums[-1])

            if quantity <= 0:
                continue

            name = clean_product_name(clean_line)

            if len(name) < 2:
                continue

            name = fix_rtl_text(name)

            data["items"].append({
                "name": name,
                "quantity": quantity,
                "weight_grams": weight_grams,
                "code": code
            })

        except ValueError:
            continue

    return data


if __name__ == "__main__":
    file_path = r"H:\function\smart-stock-project\Invoices\30000130246.pdf"

    result = extract_single_invoice(file_path)

    print(f"\nחשבונית: {result['file_name']}")
    print("-" * 100)

    for item in result["items"]:
        print(
            f"קוד: {item['code']} | "
            f"מוצר: {item['name']} | "
            f"כמות: {item['quantity']} | "
            f"משקל ליחידה (גרם): {item['weight_grams']}"
        )