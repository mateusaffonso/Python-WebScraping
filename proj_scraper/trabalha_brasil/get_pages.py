import os
import numpy as np
import time
from lib.web_scraper import PlaywrightWebScraper, BrowserType


def _get_last_saved_page_number(output_folder: str) -> int:
    """
    Retrieves the number of the last saved page from the specified output folder.

    Args:
        output_folder (str): The path to the folder containing the saved pages.

    Returns:
        int: The number of the last saved page. Returns 0 if the folder is empty.
    """
    files = os.listdir(output_folder)
    if len(files) == 0:
        return 0
    files = files.sort()
    last_page = files[-1]
    last_page_number = last_page.split("_")[-1].split(".")[0]
    return last_page_number


def get_pages(base_url: str, output_folder: str, sleep_mean=None, sleep_std=None, log_num_pages=10) -> None:
    """
    Scrapes web pages starting from a given base URL and saves them to an output folder.

    Args:
        base_url (str): The base URL to start scraping from. The page number will be appended to this URL.
        output_folder (str): The folder where the scraped pages will be saved.
        sleep_mean (float, optional): The mean value for the normal distribution used to determine sleep time between requests. Defaults to None.
        sleep_std (float, optional): The standard deviation for the normal distribution used to determine sleep time between requests. Defaults to None.
        log_num_pages (int, optional): The number of pages after which a log message will be printed. Defaults to 10.

    Raises:
        Exception: If a page fails to be retrieved, an exception is raised with the page number.

    Returns:
        None
    """
    if not os.path.isdir(output_folder):
        os.mkdir(output_folder)
    scraper = PlaywrightWebScraper(browser_type=BrowserType.FIREFOX)
    page_number = _get_last_saved_page_number(output_folder) + 1
    while True:
        full_page_url = f"{base_url}?pagina={page_number}"
        page_str = scraper.get_page(full_page_url)
        if page_str:
            full_path_file_name = f"{output_folder}/page_{page_number}.html"
            with open(full_path_file_name, "w") as f:
                f.write(page_str)
        else:
            raise (f"Failed to get page {page_number}")
        if page_number % log_num_pages == 0:
            print(f"Saved page {page_number}")
        page_number += 1
        if sleep_mean is not None:
            sleep_time = np.random.normal(sleep_mean, sleep_std)
            time.sleep(sleep_time)
