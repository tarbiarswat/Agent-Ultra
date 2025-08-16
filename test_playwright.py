from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.set_viewport_size({"width": 1400, "height": 900})
    page.goto("https://example.com", wait_until="domcontentloaded")
    print("Title:", page.title())
    page.wait_for_timeout(1200)
    browser.close()
    print("OK ✅")
