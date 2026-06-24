import pytesseract
from pdf2image import convert_from_path
import re

# הפונקציה שלך לפירוק הקבלה
def parse_receipt(text):
    data = {
        'business_name': None,
        'branch_number': None,
        'branch_name': None,
        'business_id': None,
        'address': None,
        'phone': None,
        'purchase_date': None,
        'receipt_number': None,
        'items': [],
        'total': None,
        'total_excl_vat': None,
        'vat': None
    }

    lines = text.splitlines()
    for line in lines:
        line = line.strip()

        # פרטי העסק
        if not data['business_name']:
            m = re.search(r'שם\s*עסק[:\s]*(.+)', line)
            if m: data['business_name'] = m.group(1).strip()

        if not data['branch_number']:
            m = re.search(r'מספר\s*סניף[:\s]*(\d+)', line)
            if m: data['branch_number'] = m.group(1)

        if not data['branch_name']:
            m = re.search(r'שם\s*סניף[:\s]*(.+)', line)
            if m: data['branch_name'] = m.group(1).strip()

        if not data['business_id']:
            m = re.search(r'ח\.פ\.[:\s]*(\d+)', line)
            if m: data['business_id'] = m.group(1)

        if not data['address']:
            m = re.search(r'כתובת[:\s]*(.+)', line)
            if m: data['address'] = m.group(1).strip()

        if not data['phone']:
            m = re.search(r'טלפון[:\s]*(\d+)', line)
            if m: data['phone'] = m.group(1)

        if not data['purchase_date']:
            m = re.search(r'תאריך\s*קניה[:\s]*(.+)', line)
            if m: data['purchase_date'] = m.group(1).strip()

        if not data['receipt_number']:
            m = re.search(r'חשבונית\s*מס[:\s]*(\d+)', line)
            if m: data['receipt_number'] = m.group(1)

        # פריטים
        item_match = re.match(r'^\d+\s+(\d+)?\s*(.+?)\s+([\d,.]+)\s+([\d,.]+)\s+ILS([\d,.]+)', line)
        if item_match:
            data['items'].append({
                'code': item_match.group(1) if item_match.group(1) else '',
                'name': item_match.group(2).strip(),
                'unit_price': float(item_match.group(3).replace(',', '.')),
                'quantity': float(item_match.group(4).replace(',', '.')),
                'total_price': float(item_match.group(5).replace(',', '.'))
            })

        # סיכומים
        if 'סה"כ:' in line:
            m = re.search(r'סה"כ[:\s]*ILS([\d,.]+)', line)
            if m: data['total'] = float(m.group(1).replace(',', '.'))

        if 'סה"כ ללא מע"מ' in line:
            m = re.search(r'סה"כ ללא מע"מ[:\s]*ILS([\d,.]+)', line)
            if m: data['total_excl_vat'] = float(m.group(1).replace(',', '.'))

        if 'מע"מ' in line:
            m = re.search(r'מע"מ.*ILS([\d,.]+)', line)
            if m: data['vat'] = float(m.group(1).replace(',', '.'))

    return data

# פונקציה לקריאה מ-PDF סרוק
def parse_receipt_from_scanned_pdf(pdf_path):
    # המרה של כל עמוד בתור תמונה
    pages = convert_from_path(pdf_path)
    full_text = ""
    for page in pages:
        text = pytesseract.image_to_string(page, lang='heb')  # עברית
        full_text += text + "\n"
    return parse_receipt(full_text)

# שימוש בקובץ שלך
pdf_path = r"/mnt/data/121_1580_1296756 (1).pdf"
parsed_data = parse_receipt_from_scanned_pdf(pdf_path)
print(parsed_data)