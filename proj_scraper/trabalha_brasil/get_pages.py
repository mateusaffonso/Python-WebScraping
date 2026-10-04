import os
import random
import re
import time

from lib.web_scraper import create_scraper
from trabalha_brasil.storage import list_page_files, write_text_atomic

# Minimum pause between requests, in seconds. Avoids negative values drawn
# from the normal distribution (time.sleep would raise) and too-fast requests.
MIN_SLEEP_SECONDS = 0.5


def _get_last_saved_page_number(output_folder: str) -> int:
    """
    Retrieves the number of the last saved page from the specified output folder.

    Args:
        output_folder (str): The path to the folder containing the saved pages.

    Returns:
        int: The highest N among the page_N.html files. Returns 0 if there is none.
    """
    pages = list_page_files(output_folder)
    return pages[-1][0] if pages else 0


def sleep_between_requests(sleep_mean: float | None, sleep_std: float | None) -> None:
    """Sleeps for a random time drawn from N(sleep_mean, sleep_std), never below MIN_SLEEP_SECONDS."""
    if sleep_mean is None:
        return
    sleep_time = random.gauss(sleep_mean, sleep_std or 0)
    time.sleep(max(MIN_SLEEP_SECONDS, sleep_time))


def get_pages(
    base_url: str,
    output_folder: str,
    sleep_mean: float | None = None,
    sleep_std: float | None = None,
    log_num_pages: int = 10,
    max_pages: int | None = None,
    engine: str = "playwright",
    job_marker: str = "job-link",
) -> int:
    """
    Scrapes listing pages starting from a given base URL and saves them to an output folder.

    The scraping resumes after the last page_N.html already saved in the folder and stops when:
        - max_pages new pages were saved in this run (if max_pages is given);
        - a page without any job card is found (end of the listing); or
        - a page only repeats jobs already seen in this run (the site may send
          out-of-range page numbers back to an earlier page).

    Args:
        base_url (str): The listing URL. "?pagina=N" is appended to it.
        output_folder (str): The folder where the scraped pages will be saved.
        sleep_mean (float, optional): Mean of the normal distribution used for the pause between requests.
        sleep_std (float, optional): Standard deviation of that distribution.
        log_num_pages (int, optional): Print a message every log_num_pages pages. Defaults to 10.
        max_pages (int, optional): Maximum number of new pages to save in this run. Defaults to no limit.
        engine (str, optional): "playwright" (Firefox headless) or "requests".
        job_marker (str, optional): Text that must be present in a page with jobs.

    Raises:
        RuntimeError: If a page comes back empty.

    Returns:
        int: The number of pages saved in this run.
    """
    os.makedirs(output_folder, exist_ok=True)
    page_number = _get_last_saved_page_number(output_folder) + 1
    saved = 0
    seen_job_urls = set()
    scraper = create_scraper(engine)
    try:
        while max_pages is None or saved < max_pages:
            full_page_url = f"{base_url}?pagina={page_number}"
            page_str = scraper.get_page(full_page_url)
            if not page_str:
                raise RuntimeError(f"Failed to get page {page_number}")
            if job_marker not in page_str:
                print(f"Page {page_number} has no jobs: end of the listing.")
                break
            job_urls = set(re.findall(r'data-job-url="([^"]+)"', page_str))
            if job_urls and job_urls <= seen_job_urls:
                print(f"Page {page_number} only repeats jobs already seen: end of the listing.")
                break
            seen_job_urls |= job_urls

            write_text_atomic(os.path.join(output_folder, f"page_{page_number}.html"), page_str)
            saved += 1
            if page_number % log_num_pages == 0:
                print(f"Saved page {page_number}")
            page_number += 1
            sleep_between_requests(sleep_mean, sleep_std)
    finally:
        scraper.close_down()
    print(f"{saved} new page(s) saved in {output_folder}")
    return saved
