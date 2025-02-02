from enum import Enum
from playwright.sync_api import sync_playwright
from playwright import Browser, Context


class BrowserType(Enum):
    FIREFOX = "firefox"
    WEBKIT = "webkit"
    CHROMIUM = "chromium"


class BaseWebScraper:
    def __init__(self):
        pass

    def get_page(self) -> str:
        pass

    def close_down(self):
        pass


class RequestsWebScraper(BaseWebScraper):
    def __init__(self):
        pass

    def get_page(self, url: str) -> str:
        import requests

        try:
            response = requests.get(url)
            return response.text
        except Exception as e:
            raise Exception(f"Error getting page: {e}")


class PlaywrightWebScraper(BaseWebScraper):
    def __init__(self, browser_type: BrowserType):
        self.browser_type = browser_type
        self.playwright = sync_playwright()
        self.browser = self._generate_playwright_browser(self.playwright, browser_type)

    def _generate_playwright_browser(self, playwright, browser_type: BrowserType = BrowserType.FIREFOX) -> Browser:
        webkit = None
        match browser_type:
            case BrowserType.FIREFOX:
                webkit = playwright.firefox
            case BrowserType.WEBKIT:
                webkit = playwright.webkit
            case BrowserType.CHROMIUM:
                webkit = playwright.chromium
        if webkit is None:
            raise ValueError("Invalid browser type")
        browser = webkit.launch()
        return browser

    def close_down(self):
        self.browser.close()
        self.playwright.stop()

    def get_page(self, url: str, browser_type: BrowserType) -> str:
        try:
            page = self.context.new_page()
            page.goto(url)
            body = page.inner_html("body")
            return body
        except Exception as e:
            raise Exception(f"Error getting page: {e}")
