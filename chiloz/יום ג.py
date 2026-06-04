import os
import pdfplumber
import re

# הפונקציות שלך
def extract_single_invoice(file_path):
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
    item_pattern = re.compile(
        r'(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)\s+(.+?)\s+(\d{8,13})\s+\d+'
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

# כאן עוברים על כל הקבצים בתיקייה
if __name__ == "__main__":
    invoices_folder = r"H:\function\smart-stock-project\Invoices"
    all_invoices = []

    for file_name in os.listdir(invoices_folder):
        if file_name.lower().endswith(".pdf"):
            file_path = os.path.join(invoices_folder, file_name)
            try:
                invoice = extract_single_invoice(file_path)
                all_invoices.append(invoice)
            except Exception as e:
                print(f"Error processing {file_name}: {e}")

    # מדפיסים את כל הקבלות
    for invoice in all_invoices:
        print(invoice)
