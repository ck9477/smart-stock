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
    words = words[::-1]
    words = [w[::-1] for w in words]
    return " ".join(words)


def clean_product_name(text):
    # הסרת מספרים בלבד
    text = re.sub(r'\d+(?:\.\d+)?', ' ', text)

    # הסרת תווים שאינם עבריים
    text = re.sub(r'[^א-ת\s]', ' ', text)

    # ניקוי רווחים כפולים
    text = re.sub(r'\s+', ' ', text).strip()

    # הסרת מילות כמות/יחידה אם הן בסוף המחרוזת
    quantity_words = ["יח", "יח׳", "יח'", "יחידה", "גר", "גרם", "ג", "ק\"ג", "קג", "ליטר", "ל", "מ\"ל", "מל"]
    words = text.split()
    while words and words[-1] in quantity_words:
        words.pop()

    return " ".join(words)


def parse_invoice_text(text):
    data = {"items": []}

    lines = text.splitlines()

    code_pattern = re.compile(r'\b\d{6,14}\b')
    num_pattern = re.compile(r'\d+(?:\.\d+)?')

    skip_words = [
        "טלפון", "פקס", "אימייל", "דואר", "תאריך", "סה", "מע\"מ",
        "חשבונית", "קבלה", "שעה", "פרטים", "ח.פ", "דף",
        "עוסק", "מורשה", "הזמנה", "העתק", "בפקסימיליה",
        "כניסה", "רחוב", "מבצע"
    ]

    for line in lines:
        line = line.strip()

        if not line or len(line) < 8:
            continue

        if "מבצע" in line:
            continue

        if re.search(r'-\s*\d+(?:\.\d+)?', line):
            continue

        if any(w in line for w in skip_words):
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

            if len(name) < 3:
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
    file_path = r"H:\function\smart-stock-project\Invoices\121_5218_1413803_260512_233623 (1).pdf"

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