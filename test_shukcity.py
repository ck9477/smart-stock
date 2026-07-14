"""
סקריפט בדיקה לשוק סיטי — פותח דפדפן, מחפש מוצר, ובודק את מבנה ה-DOM.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time

print("=" * 60)
print("בודק את שוק סיטי — DOM Explorer")
print("=" * 60)

play = sync_playwright().start()
browser = play.chromium.launch(headless=False)
page = browser.new_page()

# נווט לאתר
print("\n--- מנווט לאתר ---")
page.goto("https://www.shukcity.co.il", timeout=30000)
page.wait_for_timeout(5000)

body = page.inner_text("body")[:2000]
print("Body (first 2000 chars):")
print(body)
print()

# חפש מוצר
print("\n--- מחפש 'חלב' ---")
input_box = page.locator("input").first
input_box.wait_for(state="visible", timeout=5000)
input_box.click(force=True, timeout=5000)
input_box.fill("חלב")
input_box.press("Enter")
page.wait_for_timeout(5000)

# מה רואים?
body_after = page.inner_text("body")[:2000]
print("Body after search (first 2000 chars):")
print(body_after)
print()

# צלם מסך
page.screenshot(path="debug_shukcity_search.png")
print("Saved screenshot: debug_shukcity_search.png")

# חפש כפתורי פלוס
plus_buttons = page.locator("button.plus")
print(f"\nbutton.plus count: {plus_buttons.count()}")

# חפש sr-only spans
sr_spans = page.locator("span.sr-only")
print(f"span.sr-only count: {sr_spans.count()}")
for i in range(min(sr_spans.count(), 5)):
    try:
        text = sr_spans.nth(i).inner_text()
        print(f"  [{i}] {text[:100]}")
    except:
        pass

# חפש את כל הכפתורים
all_buttons = page.locator("button")
print(f"\nAll buttons count: {all_buttons.count()}")
for i in range(min(all_buttons.count(), 10)):
    try:
        text = all_buttons.nth(i).inner_text()
        if text.strip():
            print(f"  [{i}] {text[:80]}")
    except:
        pass

# תן למשתמש זמן להסתכל
print("\n--- הדפדפן נשאר פתוח 30 שניות לבדיקה ---")
time.sleep(30)

browser.close()
play.stop()
print("סיום.")
