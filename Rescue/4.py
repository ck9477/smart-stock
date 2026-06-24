import pdfplumber
import re
import os


def extract_single_invoice(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file does not exist: {file_path}")

    with pdfplumber.open(file_path) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    invoice_info = parse_invoice_text(text)
    invoice_info['file_name'] = os.path.basename(file_path)
    return invoice_info


def parse_invoice_text(text):
    data = {}

    invoice_number_match = re.search(r'מספר הקצאה:\s*(\d+)', text)
    if invoice_number_match:
        data['invoice_number'] = invoice_number_match.group(1)

    date_match = re.search(r'תאריך:\s*([\d/]+)', text)
    if date_match:
        data['date'] = date_match.group(1)

    total_match = re.search(r'ס[הה]?"כ כולל מע"מ:\s*([\d.,]+)', text)
    if total_match:
        data['total'] = total_match.group(1)

    data['items'] = []

    lines = text.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split()

        # חייב לפחות 6 חלקים לשורת פריט תקינה
        if len(parts) < 6:
            continue

        try:
            # 3 המספרים הראשונים
            price_total = float(parts[0].replace(',', '.'))
            price_unit = float(parts[1].replace(',', '.'))
            quantity = float(parts[2].replace(',', '.'))

            # הקוד בדרך כלל לפני האחרון
            code = parts[-2] if parts[-2].isdigit() else ''

            # שם מוצר = כל מה שבאמצע
            name = ' '.join(parts[3:-2])

            data['items'].append({
                'name': name,
                'quantity': quantity,
                'price_unit': price_unit,
                'price_total': price_total,
                'code': code
            })

        except:
            continue

    return data


if __name__ == "__main__":
    file_path = r"/smart-stock-project/Invoices.txt\121_1580_1296756 (1).pdf"
    invoice = extract_single_invoice(file_path)
    print(invoice)