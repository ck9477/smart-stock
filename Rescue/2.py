import pdfplumber
import re
import os

def extract_single_invoice(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

    data = parse_invoice_text(text)
    data["file_name"] = os.path.basename(file_path)
    return data

def parse_invoice_text(text):
    data = {"items": []}
    lines = text.splitlines()

    # קוד מוצר ישראלי טיפוסי (6-14 ספרות)
    code_pattern = re.compile(r'\b\d{6,14}\b')
    # מספרים (מחיר/כמות)
    num_pattern = re.compile(r'\d+(?:\.\d+)?')
    # מילים לדילוג
    skip_words = [
        "טלפון", "אימייל", "דואר", "תאריך", "סה", "מע\"מ",
        "חשבונית", "קבלה", "שעה", "פרטים", "ח.פ", "דף"
    ]

    for line in lines:
        line = line.strip()
        if not line or any(w in line for w in skip_words):
            continue

        codes = code_pattern.findall(line)
        if not codes:
            continue

        code = codes[-1]  # תמיד הקוד האחרון בשורה
        clean_line = line.replace(code, "").strip()
        nums = num_pattern.findall(clean_line)

        # חיפוש הכמות האמיתית
        quantity = None
        for n in reversed(nums):
            val = float(n)
            if 0 < val <= 100:  # סף סביר לכמות
                quantity = val
                break
        if quantity is None:
            continue

        # הסרת כל המספרים מהשם
        name = re.sub(r'\d+(?:\.\d+)?', '', clean_line).strip()
        name = re.sub(r'\s{2,}', ' ', name)

        if len(name) < 3:
            continue

        data["items"].append({
            "name": name,
            "quantity": quantity,
            "code": code
        })

    return data

if __name__ == "__main__":
    file_path = r"/smart-stock-project/Invoices.txt\30000156970.pdf"
    result = extract_single_invoice(file_path)

    print(f"חשבונית: {result['file_name']}")
    print("-" * 80)
    for item in result["items"]:
        print(f"קוד: {item['code']} | מוצר: {item['name']} | כמות: {item['quantity']}")