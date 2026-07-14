"""
סקריפט בדיקה 2 — חיפוש מעמיק במבנה ה-DOM של שוק סיטי.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time

play = sync_playwright().start()
browser = play.chromium.launch(headless=False)
page = browser.new_page()

print("--- מנווט לאתר ---")
page.goto("https://www.shukcity.co.il", timeout=30000)
page.wait_for_timeout(5000)

# נחפש את תיבת החיפוש האמיתית
print("\n--- כל ה-inputs ---")
all_inputs = page.locator("input")
print(f"Total inputs: {all_inputs.count()}")
for i in range(all_inputs.count()):
    try:
        inp = all_inputs.nth(i)
        placeholder = inp.get_attribute("placeholder") or ""
        name = inp.get_attribute("name") or ""
        id_attr = inp.get_attribute("id") or ""
        class_attr = inp.get_attribute("class") or ""
        if inp.is_visible():
            print(f"  [{i}] visible | placeholder='{placeholder}' | name='{name}' | id='{id_attr}' | class='{class_attr[:60]}'")
    except:
        pass

# ננסה לחפש דרך input עם placeholder
print("\n--- מחפש input חיפוש לפי placeholder ---")
search_input = page.locator("input[placeholder*='חיפוש'], input[placeholder*='חפש'], input[placeholder*='search'], input[name*='search'], input[name*='q']")
print(f"Search inputs found: {search_input.count()}")
for i in range(search_input.count()):
    try:
        inp = search_input.nth(i)
        print(f"  [{i}] placeholder='{inp.get_attribute('placeholder')}' visible={inp.is_visible()}")
    except:
        pass

# אולי צריך ללחוץ על אייקון חיפוש קודם?
print("\n--- מחפש אייקון/כפתור חיפוש ---")
search_icons = page.locator("[aria-label*='חיפוש'], [aria-label*='search'], .search-icon, .fa-search, svg[class*='search']")
print(f"Search icons: {search_icons.count()}")

# ננסה לגשת ישירות ל-URL של חיפוש
print("\n--- מנסה URL ישיר לחיפוש ---")
page.goto("https://www.shukcity.co.il/search?q=%D7%97%D7%9C%D7%91", timeout=30000)
page.wait_for_timeout(5000)

body = page.inner_text("body")[:1500]
print("Body after direct search URL:")
print(body)

# חפש כל אלמנט שמכיל "תוצאות"
results_text = page.locator("text=תוצאות")
print(f"\nElements with 'תוצאות': {results_text.count()}")

# חפש מוצרים — אולי יש div עם class של product
product_divs = page.locator("[class*='product'], [class*='Product'], [class*='item']")
print(f"\nProduct-related divs: {product_divs.count()}")

# צלם
page.screenshot(path="debug_shukcity_search2.png")
print("\nSaved: debug_shukcity_search2.png")

print("\nהדפדפן נשאר פתוח 30 שניות...")
time.sleep(30)
browser.close()
play.stop()
