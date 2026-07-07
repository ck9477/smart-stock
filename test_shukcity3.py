"""
סקריפט בדיקה 3 — חיפוש דרך ה-search-input האמיתי.
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

# נמצא את ה-search-input
search_input = page.locator(".search-input").first
print(f"search-input visible: {search_input.is_visible()}")

# נקליק עליו
search_input.click(force=True, timeout=5000)
page.wait_for_timeout(500)

# נקליד
search_input.fill("חלב")
page.wait_for_timeout(1000)

# נלחץ Enter
search_input.press("Enter")
page.wait_for_timeout(5000)

body = page.inner_text("body")[:2000]
print("\nBody after search:")
print(body)

# חפש תוצאות
page.screenshot(path="debug_shukcity_search3.png")
print("\nSaved: debug_shukcity_search3.png")

# בדוק את ה-URL
print(f"\nCurrent URL: {page.url}")

# חפש אלמנטים של מוצרים
all_divs = page.locator("div").count()
print(f"Total divs on page: {all_divs}")

# חפש מחירים
prices = page.locator("text=₪")
print(f"Elements with ₪: {prices.count()}")

# חפש תמונות מוצר
imgs = page.locator("img[alt*='חלב'], img[src*='product']")
print(f"Product images: {imgs.count()}")

# נסה לגשת לתוצאות דרך URL של קטגוריה
print("\n--- מנסה גישה דרך קטגוריה ---")
page.goto("https://www.shukcity.co.il/category/חלב-ומשקאות-חלב", timeout=30000)
page.wait_for_timeout(5000)
body2 = page.inner_text("body")[:1500]
if "blocked" in body2.lower():
    print("BLOCKED by Cloudflare on category page")
else:
    print("Category page loaded")
    page.screenshot(path="debug_shukcity_category.png")

print("\nהדפדפן נשאר פתוח 30 שניות...")
time.sleep(30)
browser.close()
play.stop()
