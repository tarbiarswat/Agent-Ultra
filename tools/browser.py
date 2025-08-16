# --- Windows asyncio policy fix for Playwright ---
import sys, asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# -------------------------------------------------

from playwright.sync_api import sync_playwright

class BrowserTool:
    def __init__(self):
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(headless=False, args=["--disable-features=InterestCohort"])
        self.ctx = self.browser.new_context(viewport={"width": 1400, "height": 900})
        self.page = self.ctx.new_page()

    def open_url(self, url:str):
        self.page.goto(url, wait_until="domcontentloaded")
        return f"Opened {url}"

    def read_page(self):
        title = self.page.title()
        body = self.page.inner_text("body")
        return f"[{title}]\n{body[:4000]}"

    def click(self, text_or_selector:str):
        try:
            # Try text first (role/button/link), fallback to CSS selector
            self.page.get_by_role("button", name=text_or_selector).click(timeout=2000)
            return f"Clicked button '{text_or_selector}'"
        except:
            try:
                self.page.get_by_text(text_or_selector, exact=False).first.click(timeout=2000)
                return f"Clicked text '{text_or_selector}'"
            except:
                self.page.click(text_or_selector, timeout=3000)
                return f"Clicked selector {text_or_selector}"

    def type(self, text:str):
        self.page.keyboard.type(text, delay=20)
        return "Typed."

    def wait(self, seconds:float):
        self.page.wait_for_timeout(int(seconds*1000))
        return f"Waited {seconds}s"

    def close(self):
        self.ctx.close(); self.browser.close(); self.pw.stop()
