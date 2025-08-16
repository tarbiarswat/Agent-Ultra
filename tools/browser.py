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
        return {
            "status": "ok",
            "current_url": self.page.url,
            "title": self.page.title()
        }

    def read_page(self):
        title = self.page.title()
        text  = self.page.inner_text("body")[:2000]
        return {
            "status": "ok",
            "title": title,
            "excerpt": text
        }

    def click(self, text_or_selector:str):
        try:
            self.page.get_by_role("button", name=text_or_selector).click(timeout=2000)
            where = "role(button)"
        except:
            try:
                self.page.get_by_text(text_or_selector, exact=False).first.click(timeout=2000)
                where = "text"
            except:
                self.page.click(text_or_selector, timeout=3000)
                where = "selector"
        return {"status": "ok", "clicked_via": where, "target": text_or_selector}

    def type(self, text:str):
        self.page.keyboard.type(text, delay=20)
        return {"status": "ok", "typed_len": len(text)}

    def wait(self, seconds:float=1):
        self.page.wait_for_timeout(int(seconds*1000))
        return {"status": "ok", "waited_s": seconds}

    def close(self):
        self.ctx.close(); self.browser.close(); self.pw.stop()
