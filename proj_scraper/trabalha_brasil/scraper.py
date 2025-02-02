from playwright.sync_api import sync_playwright

def get_page(url: str):
    with sync_playwright() as playwright:
        webkit = playwright.webkit
        browser = webkit.launch()
        context = browser.new_context()
        page = context.new_page()
        page.goto(url)
        body = page.inner_html("body")
        browser.close()
        return body