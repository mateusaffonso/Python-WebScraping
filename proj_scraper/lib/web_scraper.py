import requests
from enum import Enum
from playwright.sync_api import sync_playwright


class BrowserType(Enum):
    """
    Enum class representing different types of web browsers.

    Attributes:
        FIREFOX (str): Represents the Firefox browser.
        WEBKIT (str): Represents the WebKit browser engine.
        CHROMIUM (str): Represents the Chromium browser.
    """
    FIREFOX = "firefox"
    WEBKIT = "webkit"
    CHROMIUM = "chromium"


class BaseWebScraper:
    """
    Base class for web scraping.

    Methods
    -------
    __init__():
        Initializes the web scraper.

    get_page() -> str:
        Retrieves the content of a web page. This method should be implemented by subclasses.

    close_down():
        Closes any resources or connections used by the web scraper. This method should be implemented by subclasses.
    """
    def __init__(self):
        pass

    def get_page(self) -> str:
        pass

    def close_down(self):
        pass


class RequestsWebScraper(BaseWebScraper):
    """
    A web scraper that uses the Requests library to fetch web pages.

    Methods
    -------
    __init__():
        Initializes the RequestsWebScraper instance.
    
    get_page(url: str) -> str:
        Fetches the content of the web page at the specified URL.

        Parameters
        ----------
        url : str
            The URL of the web page to fetch.

        Returns
        -------
        str
            The content of the web page as a string.

        Raises
        ------
        Exception
            If there is an error while fetching the web page.
    """
    def __init__(self):
        pass

    def get_page(self, url: str) -> str:
       

        try:
            response = requests.get(url)
            return response.text
        except Exception as e:
            raise Exception(f"Error getting page: {e}")


class PlaywrightWebScraper(BaseWebScraper):
    """
    A web scraper class that uses Playwright to scrape web pages.

    Attributes:
        browser_type (BrowserType): The type of browser to use (FIREFOX, WEBKIT, or CHROMIUM).
        playwright (Playwright): The Playwright instance.
        browser (Browser): The browser instance created by Playwright.
        page (Page): The page instance created by the browser.

    Methods:
        __init__(browser_type: BrowserType):
            Initializes the PlaywrightWebScraper with the specified browser type.
        
        _generate_playwright_browser():
            Generates and returns a Playwright browser instance based on the specified browser type.
        
        close_down():
            Closes the browser and stops the Playwright instance.
        
        get_page(url: str) -> str:
            Navigates to the specified URL and returns the inner HTML of the body element.
    """
    def __init__(self, browser_type: BrowserType):
        """
        Initializes the WebScraper instance.

        Args:
            browser_type (BrowserType): The type of browser to use (e.g., Chromium, Firefox, WebKit).

        Attributes:
            browser_type (BrowserType): The type of browser to use.
            playwright (Playwright): The Playwright instance.
            browser (Browser): The browser instance created by Playwright.
            page (Page): The new page instance created in the browser.
        """
        self.browser_type = browser_type
        self.playwright = sync_playwright().start()
        self.browser = self._generate_playwright_browser()
        self.page = self.browser.new_page()

    def _generate_playwright_browser(self):
        """
        Generates and launches a Playwright browser instance based on the specified browser type.

        This method uses the `self.browser_type` attribute to determine which browser to launch.
        It supports launching Firefox, WebKit, and Chromium browsers using Playwright.

        Returns:
            Browser: An instance of the launched Playwright browser.

        Raises:
            ValueError: If the browser type specified in `self.browser_type` is invalid.
        """
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
        """
        Closes the browser and stops the Playwright instance.

        This method should be called to properly shut down the browser and 
        release any resources held by the Playwright instance.
        """
        self.browser.close()
        self.playwright.stop()

    def get_page(self, url: str) -> str:
        """
        Fetches the HTML content of the specified URL.

        Args:
            url (str): The URL of the web page to retrieve.

        Returns:
            str: The HTML content of the web page.

        Raises:
            Exception: If there is an error while fetching the page.
        """
        try:
            self.page.goto(url)
            body = self.page.inner_html("body")
            return body
        except Exception as e:
            raise Exception(f"Error getting page: {e}")
