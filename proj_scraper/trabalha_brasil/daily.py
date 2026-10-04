from datetime import date

from trabalha_brasil.get_details import get_details
from trabalha_brasil.get_pages import BASE_URL, get_pages
from trabalha_brasil.storage import listings_folder, load_jobs


def run_daily(
    data_folder: str,
    max_pages: int | None = 100,
    stop_after_known_pages: int = 3,
    max_jobs: int | None = 2000,
    max_recheck: int | None = 1000,
    sleep_mean: float = 2.0,
    sleep_std: float = 0.5,
    engine: str = "requests",
    run_date: str | None = None,
) -> dict[str, dict]:
    """
    One day of incremental collection, meant to be scheduled (e.g. GitHub Actions):

    1. Listing ordered by "Mais recentes": new pages go to listings/<run_date>/.
       Stops after stop_after_known_pages pages in a row with no job outside
       vagas.csv (or at max_pages).
    2. Details (publication date, salary, description) of the new jobs (at most max_jobs).
    3. Revisits up to max_recheck open jobs (checked longest ago first) to detect
       the closed ones (closed_detected_at).

    Returns:
        dict[str, dict]: All jobs, by job_id.
    """
    run_date = run_date or date.today().isoformat()
    known_job_ids = set(load_jobs(data_folder))
    print(f"== {run_date}: {len(known_job_ids)} job(s) already known")

    print("== 1/2 Listing (most recent first)")
    get_pages(
        BASE_URL,
        listings_folder(data_folder, run_date),
        sleep_mean=sleep_mean,
        sleep_std=sleep_std,
        log_num_pages=10,
        max_pages=max_pages,
        engine=engine,
        order="recent",
        known_job_ids=known_job_ids,
        stop_after_known_pages=stop_after_known_pages,
    )

    print("== 2/2 Job pages (new jobs + rechecks)")
    jobs = get_details(
        data_folder,
        max_jobs=max_jobs,
        recheck=True,
        max_recheck=max_recheck,
        sleep_mean=sleep_mean,
        sleep_std=sleep_std,
        engine=engine,
        log_num_jobs=100,
    )

    new_today = sum(1 for job in jobs.values() if job.get("first_seen") == run_date and job["job_id"] not in known_job_ids)
    closed = sum(1 for job in jobs.values() if job.get("closed_detected_at"))
    pending = sum(1 for job in jobs.values() if not job.get("details_fetched_at"))
    print(f"== Summary: {len(jobs)} job(s) | {new_today} new today | {closed} detected as closed | {pending} still without details")
    return jobs
