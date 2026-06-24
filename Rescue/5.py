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

    # רק שינוי אחד כאן: 8-13 → 5-13
    item_pattern = re.compile(
        r'(\d+(?:[.,]\d+)?)\s+'
        r'(\d+(?:[.,]\d+)?)\s+'
        r'(\d+(?:[.,]\d+)?)\s+'
        r'(.+?)\s+'
        r'(\d{5,13})\s+\d+'
    )

    for match in item_pattern.finditer(text):
        try:
            price_total = float(match.group(1).replace(",", "."))
            price_unit = float(match.group(2).replace(",", "."))
            quantity = float(match.group(3).replace(",", "."))
            name = match.group(4).strip()
            code = match.group(5).strip()

            data['items'].append({
                'name': name,
                'quantity': quantity,
                'price_unit': price_unit,
                'price_total': price_total,
                'code': code
            })
        except ValueError:
            continue

    return data


if __name__ == "__main__":
    file_path = r"/smart-stock-project/Invoices.txt\121_1580_1296756 (1).pdf"
    invoice = extract_single_invoice(file_path)
    print(invoice)