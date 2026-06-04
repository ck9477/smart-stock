import pdfplumber
import re


CODE_PATTERN = re.compile(r'\b\d{6,14}\b')
NUMBER_PATTERN = re.compile(r'\d+(?:\.\d+)?')

SKIP_LINES = [
    "טלפון",
    "פקס",
    "עוסק",
    "מורשה",
    "העתק",
    "רחוב",
    "הזמנה",
    "הספקה",
    "פקסימיליה",
]

BAD_WORDS = {
    "מבצע",
    "חשי",
    "בחשי",
    "שי",
    "דסח",
    "ח\\שי",
    "ב",
    "חי",
}


def reverse_hebrew(text):
    words = text.split()
    words.reverse()

    fixed = []
    for w in words:
        fixed.append(w[::-1])

    return " ".join(fixed)


def clean_name(text):
    text = reverse_hebrew(text)

    text = re.sub(r'\d+(?:\.\d+)?', ' ', text)

    text = re.sub(r'[-:".,*/\\]+', ' ', text)

    text = re.sub(r'\s+', ' ', text).strip()

    words = []

    for w in text.split():

        if w in BAD_WORDS:
            continue

        if len(w) <= 1:
            continue

        if re.search(r'\d', w):
            continue

        words.append(w)

    return " ".join(words).strip()


def pick_quantity(numbers):

    candidates = []

    for n in numbers:
        try:
            val = float(n)

            if val <= 0:
                continue

            if val > 50 and not val.is_integer():
                continue

            if val <= 500:
                candidates.append(val)

        except:
            pass

    if not candidates:
        return None

    return candidates[-1]


def is_bad_line(line):
    for bad in SKIP_LINES:
        if bad in line:
            return True

    return False


def parse_invoice_text(text):
    items = []

    lines = text.splitlines()

    for line in lines:

        line = line.strip()

        if len(line) < 5:
            continue

        if is_bad_line(line):
            continue

        codes = CODE_PATTERN.findall(line)

        if not codes:
            continue

        code = codes[0]

        line_wo_code = line.replace(code, " ")

        numbers = NUMBER_PATTERN.findall(line_wo_code)

        quantity = pick_quantity(numbers)

        if quantity is None:
            continue

        name = clean_name(line_wo_code)

        if len(name) < 2:
            continue

        items.append({
            "code": code,
            "name": name,
            "quantity": quantity
        })

    return items


def extract_single_invoice(file_path):
    text = ""

    with pdfplumber.open(file_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    print("TEXT LENGTH:", len(text))

    items = parse_invoice_text(text)

    print("ITEMS:", len(items))
    print("-" * 60)

    for item in items:
        print(
            f"קוד: {item['code']} | "
            f"מוצר: {item['name']} | "
            f"כמות: {item['quantity']}"
        )

    return items


if __name__ == "__main__":

    file_path = r"H:\function\kabalot\121_5218_1413803_260512_233623 (1).pdf"

    extract_single_invoice(file_path)