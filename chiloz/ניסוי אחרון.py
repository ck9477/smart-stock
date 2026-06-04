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


def fix_hebrew_text(text):
    words = text.split()[::-1]
    return " ".join(w[::-1] for w in words)


def parse_invoice_text(text):
    data = {"items": []}

    lines = text.splitlines()

    code_pattern = re.compile(r'\b\d{6,14}\b')
    num_pattern = re.compile(r'\d+(?:\.\d+)?')

    skip_words = [
        "טלפון", "פקס", "אימייל", "דואר", "תאריך", "סה", "מע\"מ",
        "חשבונית", "קבלה", "שעה", "פרטים", "ח.פ", "דף",
        "עוסק", "מורשה", "הזמנה", "העתק", "בפקסימיליה", "כניסה",
        "רחוב"
    ]

    bad_words_in_name = [
        "טלפון", "פקס", "רחוב", "עוסק", "מורשה",
        "העתק", "הזמנה", "כניסה", "בפקסימיליה"
    ]

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if len(line) < 8:
            continue

        if any(w in line for w in skip_words):
            continue

        codes = code_pattern.findall(line)
        if not codes:
            continue

        code = codes[-1]

        clean_line = line.replace(code, "").strip()
        nums = num_pattern.findall(clean_line)

        if len(nums) < 1:
            continue

        try:
            quantity = float(nums[-1])

            name = re.sub(r'\d+(?:\.\d+)?', '', clean_line).strip()
            name = re.sub(r'\s{2,}', ' ', name)

            if len(name) < 3:
                continue

            name = fix_hebrew_text(name)

            name = name.replace("----", "")
            name = name.replace("--", "")
            name = name.replace("- -", "")
            name = re.sub(r'\s{2,}', ' ', name).strip()

            if any(bad in name for bad in bad_words_in_name):
                continue

            data["items"].append({
                "name": name,
                "quantity": quantity,
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
        print(f"קוד: {item['code']} | מוצר: {item['name']} | כמות: {item['quantity']}")