import os
import random
import re
import time
from urllib.parse import urlencode

from lib.web_scraper import create_scraper
from trabalha_brasil.storage import list_page_files, write_text_atomic

BASE_URL = "https://www.trabalhabrasil.com.br/vagas-de-emprego"

# Values of the site's "Ordenacao" query parameter.
ORDER_PARAMS = {"relevant": None, "recent": "2"}

# The site never shows more than this many listing pages (page 501 comes back empty).
MAX_LISTING_PAGES = 500

# A page without jobs right after a full page (before MAX_LISTING_PAGES) may be a
# temporary failure of the site: it is retried EMPTY_PAGE_RETRIES times, waiting
# EMPTY_PAGE_WAIT seconds. After a page with fewer jobs, it is just the end.
JOBS_PER_PAGE = 15
EMPTY_PAGE_RETRIES = 2
EMPTY_PAGE_WAIT = 20

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


def build_listing_url(base_url: str, page_number: int, order: str = "relevant") -> str:
    """Builds the listing URL for a page number and an order ("relevant" or "recent")."""
    if order not in ORDER_PARAMS:
        raise ValueError(f"Invalid order: {order}")
    params = {"pagina": page_number}
    if ORDER_PARAMS[order]:
        params = {"Ordenacao": ORDER_PARAMS[order], **params}
    return f"{base_url}?{urlencode(params)}"


def _job_ids_in_page(page_str: str) -> set[str]:
    return set(re.findall(r'data-job-url="[^"]*?/(\d+)/?"', page_str))


def get_pages(
    base_url: str,
    output_folder: str,
    sleep_mean: float | None = None,
    sleep_std: float | None = None,
    log_num_pages: int = 10,
    max_pages: int | None = None,
    engine: str = "playwright",
    job_marker: str = "job-link",
    order: str = "relevant",
    known_job_ids: set[str] | None = None,
    stop_after_known_pages: int | None = None,
    min_pages: int = 0,
    min_job_id: int | None = None,
    stop_after_old_pages: int = 2,
    deadline: float | None = None,
    stats: dict | None = None,
) -> int:
    """
    Scrapes listing pages starting from a given base URL and saves them to an output folder.

    The scraping resumes after the last page_N.html already saved in the folder and stops when:
        - max_pages new pages were saved in this run (if max_pages is given);
        - a page without any job card is found (end of the listing); or
        - a page only repeats jobs already seen in this run (the site may send
          out-of-range page numbers back to an earlier page); or
        - stop_after_known_pages consecutive pages bring no job outside
          known_job_ids (incremental collection with order="recent": once the
          listing reaches jobs collected in previous days, there is nothing new).
          Pages up to min_pages never count: the "Mais recentes" listing starts
          with a sparse block of ~30 pages and only then the complete, newest-first
          sequence, so known jobs in the first block do not mean the end; or
        - stop_after_old_pages consecutive pages only have job ids below
          min_job_id (jobs older than the period of interest); or
        - the time.time() deadline is reached.

    stats, if given, receives "stop_reason" ("max_pages", "end", "repeated",
    "known", "old" or "deadline").

    Args:
        base_url (str): The listing URL. "?pagina=N" is appended to it.
        output_folder (str): The folder where the scraped pages will be saved.
        sleep_mean (float, optional): Mean of the normal distribution used for the pause between requests.
        sleep_std (float, optional): Standard deviation of that distribution.
        log_num_pages (int, optional): Print a message every log_num_pages pages. Defaults to 10.
        max_pages (int, optional): Maximum number of new pages to save in this run. Defaults to no limit.
        engine (str, optional): "playwright" (Firefox headless) or "requests".
        job_marker (str, optional): Text that must be present in a page with jobs.
        order (str, optional): "relevant" (site default) or "recent" (newest first).
        known_job_ids (set[str], optional): Ids of jobs already collected before.
        stop_after_known_pages (int, optional): See the stop conditions above.
        min_pages (int, optional): Page number up to which known pages are not counted.
        min_job_id (int, optional): Smallest job id of interest (ids grow with the publication date).
        stop_after_old_pages (int, optional): See the stop conditions above.
        deadline (float, optional): time.time() value after which no new page is requested.
        stats (dict, optional): Filled with the stop reason.

    Raises:
        RuntimeError: If a page comes back empty.

    Returns:
        int: The number of pages saved in this run.
    """
    os.makedirs(output_folder, exist_ok=True)
    page_number = _get_last_saved_page_number(output_folder) + 1
    saved = 0
    seen_job_urls = set()
    known_job_ids = known_job_ids or set()
    pages_without_new_jobs = 0
    old_pages = 0
    previous_page_full = False
    stop_reason = "max_pages"
    scraper = create_scraper(engine)
    try:
        while max_pages is None or saved < max_pages:
            if deadline is not None and time.time() > deadline:
                stop_reason = "deadline"
                break
            full_page_url = build_listing_url(base_url, page_number, order)
            page_str = _get_listing_page(scraper, full_page_url, page_number, job_marker, retry=previous_page_full)
            if job_marker not in page_str:
                print(f"Page {page_number} has no jobs: end of the listing.")
                stop_reason = "end"
                break
            job_urls = set(re.findall(r'data-job-url="([^"]+)"', page_str))
            if job_urls and job_urls <= seen_job_urls:
                print(f"Page {page_number} only repeats jobs already seen: end of the listing.")
                stop_reason = "repeated"
                break
            seen_job_urls |= job_urls
            previous_page_full = len(job_urls) >= JOBS_PER_PAGE

            write_text_atomic(os.path.join(output_folder, f"page_{page_number}.html"), page_str)
            saved += 1
            if page_number % log_num_pages == 0:
                print(f"Saved page {page_number}")
            page_number += 1

            job_ids = _job_ids_in_page(page_str)
            if stop_after_known_pages and page_number > min_pages:
                pages_without_new_jobs = 0 if job_ids - known_job_ids else pages_without_new_jobs + 1
                if pages_without_new_jobs >= stop_after_known_pages:
                    print(f"{pages_without_new_jobs} page(s) in a row without new jobs: stopping.")
                    stop_reason = "known"
                    break
            if min_job_id is not None and job_ids:
                old_pages = old_pages + 1 if max(int(i) for i in job_ids) < min_job_id else 0
                if old_pages >= stop_after_old_pages:
                    print(f"{old_pages} page(s) in a row older than job {min_job_id}: stopping.")
                    stop_reason = "old"
                    break
            sleep_between_requests(sleep_mean, sleep_std)
    finally:
        scraper.close_down()
    if stats is not None:
        stats["stop_reason"] = stop_reason
    print(f"{saved} new page(s) saved in {output_folder}")
    return saved


def _get_listing_page(scraper, url: str, page_number: int, job_marker: str, retry: bool = True) -> str:
    """
    Gets a listing page. If retry and before MAX_LISTING_PAGES, a page without
    jobs (or an error) is retried, because the site sometimes returns an empty
    page for a moment. Raises RuntimeError if the page cannot be downloaded at all.
    """
    attempts = 1 + (EMPTY_PAGE_RETRIES if retry and page_number <= MAX_LISTING_PAGES else 0)
    page_str, error = "", None
    for attempt in range(attempts):
        if attempt:
            print(f"Page {page_number} came back without jobs; retrying in {EMPTY_PAGE_WAIT} s")
            time.sleep(EMPTY_PAGE_WAIT)
        try:
            page_str, error = scraper.get_page(url) or "", None
        except Exception as e:
            page_str, error = "", e
        if job_marker in page_str:
            return page_str
    if error is not None and not page_str:
        raise RuntimeError(f"Failed to get page {page_number}: {error}")
    return page_str
