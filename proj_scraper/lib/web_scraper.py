from enum import Enum
from playwright.sync_api import sync_playwright


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
        self.playwright = sync_playwright().start()
        self.browser = self._generate_playwright_browser()
        self.page = self.browser.new_page()

    def _generate_playwright_browser(self):
        webkit = None
        match self.browser_type:
            case BrowserType.FIREFOX:
                webkit = self.playwright.firefox.launch()
            case BrowserType.WEBKIT:
                webkit = self.playwright.webkit.launch()
            case BrowserType.CHROMIUM:
                webkit = self.playwright.chromium.launch()
        if webkit is None:
            raise ValueError("Invalid browser type")
        return webkit

    def close_down(self):
        self.browser.close()
        self.playwright.stop()

    def get_page(self, url: str) -> str:
        try:
            self.page.goto(url)
            body = self.page.inner_html("body")
            return body
        except Exception as e:
            raise Exception(f"Error getting page: {e}")
