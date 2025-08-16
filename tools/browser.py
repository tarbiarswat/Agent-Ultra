# tools/browser.py
# --- Windows asyncio policy fix for Playwright ---
import sys, asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# -------------------------------------------------
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

class BrowserTool:
    def __init__(self):
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(
            headless=False,
            args=["--disable-features=InterestCohort"]
        )
        self.ctx = self.browser.new_context(viewport={"width": 1400, "height": 900})
        self.page = self.ctx.new_page()
        self.page.set_default_timeout(6000)  # a bit more generous

    def open_url(self, url:str):
        self.page.goto(url, wait_until="domcontentloaded")
        return {"status":"ok","current_url": self.page.url, "title": self.page.title()}

    def read_page(self):
        title = self.page.title()
        excerpt = self.page.inner_text("body")[:2000]
        return {"status":"ok","title": title,"excerpt": excerpt}

    def click(self, text_or_selector:str):
        try:
            self.page.get_by_role("button", name=text_or_selector).click()
            where = "role(button)"
        except Exception:
            try:
                self.page.get_by_text(text_or_selector, exact=False).first.click()
                where = "text"
            except Exception:
                self.page.click(text_or_selector)
                where = "selector"
        return {"status":"ok","clicked_via": where,"target": text_or_selector}

    def type(self, text:str):
        self.page.keyboard.type(text, delay=20)
        return {"status":"ok","typed_len": len(text)}

    # NEW: focus a selector explicitly
    def focus(self, selector:str):
        self.page.wait_for_selector(selector, state="visible")
        self.page.focus(selector)
        return {"status":"ok","focused": selector}

    # NEW: fill a specific selector
    def fill(self, selector:str, text:str):
        self.page.wait_for_selector(selector, state="visible")
        self.page.fill(selector, text)
        return {"status":"ok","filled": selector,"text_len": len(text)}

    # NEW: press a key (e.g., Enter)
    def press(self, key:str):
        self.page.keyboard.press(key)
        return {"status":"ok","pressed": key}

    # NEW: site_search — smart search box finder (works on many sites incl. python.org)
    def site_search(self, query:str):
        selectors_try = [
            "#id-search-field",            # python.org
            "input[name='q']",
            "input[type='search']",
            "input[aria-label*='search' i]",
            "input[placeholder*='search' i]"
        ]
        for sel in selectors_try:
            try:
                self.page.wait_for_selector(sel, state="visible", timeout=2500)
                self.page.fill(sel, "")
                self.page.type(sel, query, delay=20)
                # try pressing Enter first
                try:
                    self.page.keyboard.press("Enter")
                except Exception:
                    pass
                # fallback: click a submit button if present
                for submit in ("#submit", "button[type='submit']", "input[type='submit']"):
                    try:
                        self.page.locator(submit).first.click(timeout=1200)
                        break
                    except Exception:
                        continue
                return {"status":"ok","used_selector": sel,"query": query}
            except PWTimeout:
                continue
            except Exception:
                continue
        return {"status":"error","message":"No search field found","query": query}

    def wait(self, seconds:float=1):
        self.page.wait_for_timeout(int(seconds*1000))
        return {"status":"ok","waited_s": seconds}

    def close(self):
        self.ctx.close(); self.browser.close(); self.pw.stop()
