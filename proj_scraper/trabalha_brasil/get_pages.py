import os
import numpy as np
import time
from lib.web_scraper import PlaywrightWebScraper


def _get_last_saved_page_number(output_folder: str) -> int:
    files = os.listdir(output_folder)
    if len(files) == 0:
        return 0
    files = files.sort()
    last_page = files[-1]
    last_page_number = last_page.split("_")[-1].split(".")[0]
    return last_page_number


def get_pages(base_url: str, output_folder: str, sleep_mean=None, sleep_std=None, log_num_pages=10) -> None:
    if not os.path.isdir(output_folder):
        os.mkdir(output_folder)
    scraper = PlaywrightWebScraper()
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
