import time
from datetime import datetime

from lib.web_scraper import create_scraper
from trabalha_brasil.extract_data import DETAIL_FIELDS, extract_job_details, extract_page_data
from trabalha_brasil.get_pages import sleep_between_requests
from trabalha_brasil.storage import list_listing_runs, list_page_files_recursive, listings_folder, load_jobs, save_jobs

# Save vagas.csv every N visited jobs, so little is lost if the run is interrupted.
SAVE_EVERY = 10

# A job page that fails this many times (e.g. removed from the site) is not tried again.
MAX_FETCH_ERRORS = 3

# After this many errors in a row the site may be refusing requests: pause for
# ERROR_PAUSE seconds, and give up the run after MAX_ERROR_PAUSES pauses.
ERRORS_IN_A_ROW = 10
ERROR_PAUSE = 300
MAX_ERROR_PAUSES = 3


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def update_jobs_from_listings(data_folder: str) -> dict[str, dict]:
    """
    Reads every saved listing page (all collection days) and updates vagas.csv:
    new jobs are added, and the listing fields / first_seen / last_seen of the
    known jobs are refreshed. Details already downloaded are kept.

    Returns:
        dict[str, dict]: All jobs, by job_id.
    """
    jobs = load_jobs(data_folder)
    for run_date in list_listing_runs(data_folder):
        for path in list_page_files_recursive(listings_folder(data_folder, run_date)):
            with open(path, encoding="utf-8") as f:
                cards = extract_page_data(f.read())
            for card in cards:
                if not card["job_id"]:
                    continue
                job = jobs.setdefault(card["job_id"], {})
                job.update(card)
                job["first_seen"] = min(filter(None, [job.get("first_seen"), run_date]))
                job["last_seen"] = max(filter(None, [job.get("last_seen"), run_date]))
    save_jobs(data_folder, jobs)
    return jobs


def _jobs_to_visit(
    jobs: dict[str, dict],
    recheck: bool,
    max_jobs: int | None = None,
    max_recheck: int | None = None,
    eligible_ids: set[str] | None = None,
) -> list[dict]:
    """
    Jobs without details come first (newest ids first, at most max_jobs).
    With recheck=True, jobs not yet seen as closed and not checked today are
    also included, the ones checked longest ago first (at most max_recheck).
    Only jobs in eligible_ids are considered, if given (parallel collection).
    """
    today = datetime.now().date().isoformat()
    if eligible_ids is not None:
        jobs = {job_id: job for job_id, job in jobs.items() if job_id in eligible_ids}
    new_jobs = [
        job
        for job in jobs.values()
        if not job.get("details_fetched_at") and int(job.get("fetch_errors") or 0) < MAX_FETCH_ERRORS
    ]
    new_jobs.sort(key=lambda job: int(job["job_id"]) if job["job_id"].isdigit() else 0, reverse=True)
    to_visit = new_jobs[:max_jobs] if max_jobs is not None else new_jobs
    if recheck:
        open_jobs = [
            job
            for job in jobs.values()
            if job.get("details_fetched_at")
            and not job.get("closed_detected_at")
            and not (job.get("last_checked_at") or "").startswith(today)
        ]
        open_jobs.sort(key=lambda job: job.get("last_checked_at") or "")
        to_visit += open_jobs[:max_recheck] if max_recheck is not None else open_jobs
    return to_visit


def get_details(
    data_folder: str,
    max_jobs: int | None = None,
    recheck: bool = False,
    max_recheck: int | None = None,
    sleep_mean: float | None = None,
    sleep_std: float | None = None,
    engine: str = "playwright",
    log_num_jobs: int = 10,
    eligible_ids: set[str] | None = None,
    deadline: float | None = None,
) -> dict[str, dict]:
    """
    Visits the page of each job to collect its details (publication date,
    salary range, full description...) and to detect closed jobs.

    The closing date is not published by the site. It is inferred: when a page
    that was open starts showing "A vaga foi encerrada", closed_detected_at is
    set to the moment of that visit. Run with recheck=True periodically (e.g.
    daily) to get closing dates with that precision.

    Args:
        data_folder (str): Folder with listings/ and vagas.csv.
        max_jobs (int, optional): Maximum number of new jobs (without details) to visit in this run.
        recheck (bool, optional): Also revisit open jobs to detect closings.
        max_recheck (int, optional): Maximum number of open jobs to revisit in this run.
        sleep_mean (float, optional): Mean pause between requests, in seconds.
        sleep_std (float, optional): Standard deviation of the pause.
        engine (str, optional): "playwright" (Firefox headless) or "requests".
        log_num_jobs (int, optional): Print a message every log_num_jobs jobs.
        eligible_ids (set[str], optional): Only visit these jobs (parallel collection).
        deadline (float, optional): time.time() value after which no new job is visited.

    Returns:
        dict[str, dict]: All jobs, by job_id.
    """
    jobs = update_jobs_from_listings(data_folder)
    to_visit = _jobs_to_visit(jobs, recheck, max_jobs, max_recheck, eligible_ids)
    print(f"{len(to_visit)} job page(s) to visit")
    if not to_visit:
        return jobs

    scraper = create_scraper(engine)
    visited = errors = errors_in_a_row = pauses = 0
    try:
        for job in to_visit:
            if deadline is not None and time.time() > deadline:
                print("Time limit reached: the remaining jobs stay for the next run.")
                break
            try:
                page = scraper.get_html(job["url"])
            except Exception as e:
                errors += 1
                errors_in_a_row += 1
                job["fetch_errors"] = int(job.get("fetch_errors") or 0) + 1
                print(f"Error on job {job['job_id']}: {e}")
                if errors_in_a_row >= ERRORS_IN_A_ROW:
                    pauses += 1
                    if pauses > MAX_ERROR_PAUSES:
                        print("Too many errors in a row: stopping this run.")
                        break
                    print(f"{errors_in_a_row} errors in a row: pausing {ERROR_PAUSE} s")
                    time.sleep(ERROR_PAUSE)
                    errors_in_a_row = 0
                continue
            errors_in_a_row = 0
            details = extract_job_details(page)
            checked_at = _now()

            # Keep the details collected while the job was open.
            if details["date_posted"] or not job.get("details_fetched_at"):
                job.update({field: details[field] for field in DETAIL_FIELDS})
            if not job.get("details_fetched_at"):
                job["details_fetched_at"] = checked_at
            job["last_checked_at"] = checked_at
            job["closed"] = details["closed"]
            if details["closed"] and not job.get("closed_detected_at"):
                job["closed_detected_at"] = checked_at

            visited += 1
            if visited % SAVE_EVERY == 0:
                save_jobs(data_folder, jobs)
            if visited % log_num_jobs == 0:
                print(f"Visited {visited}/{len(to_visit)} jobs")
            sleep_between_requests(sleep_mean, sleep_std)
    finally:
        scraper.close_down()
        save_jobs(data_folder, jobs)
    print(f"{visited} job page(s) visited, {errors} error(s)")
    return jobs
