from datetime import date
from typing import Optional

import typer

from trabalha_brasil.daily import run_daily
from trabalha_brasil.get_details import get_details, update_jobs_from_listings
from trabalha_brasil.get_pages import BASE_URL, ORDER_PARAMS, get_pages
from trabalha_brasil.intensive import run_shard
from trabalha_brasil.storage import JOBS_CSV, listings_folder, load_jobs, load_jobs_file, merge_jobs, save_jobs

app = typer.Typer()

DataFolder = typer.Option("./data", "--data-folder", "-d", help="Folder where the pages and vagas.csv are saved (e.g. a Google Drive folder).")
SleepMean = typer.Option(2.0, help="Mean pause between requests, in seconds.")
SleepStd = typer.Option(0.5, help="Standard deviation of the pause, in seconds.")
Engine = typer.Option("playwright", help='"playwright" (Firefox headless) or "requests".')


@app.command("get-pages")
def get_trabalha_brasil_pages(
    data_folder: str = DataFolder,
    max_pages: Optional[int] = typer.Option(None, help="Maximum number of new listing pages in this run (default: until the end)."),
    run_date: str = typer.Option(date.today().isoformat(), help="Collection day (YYYY-MM-DD). Pages go to <data-folder>/listings/<run-date>/."),
    sleep_mean: float = SleepMean,
    sleep_std: float = SleepStd,
    engine: str = Engine,
    log_num_pages: int = typer.Option(1, help="Print a message every N pages."),
    order: str = typer.Option("relevant", help=f"Listing order: {' or '.join(ORDER_PARAMS)} (newest first)."),
    stop_after_known_pages: Optional[int] = typer.Option(
        None, help="Stop after N pages in a row with no job outside vagas.csv (use with --order recent for daily collections)."
    ),
):
    """
    Downloads the job listing pages of the Trabalha Brasil website.

    Pages are saved to <data-folder>/listings/<run-date>/page_N.html. Running it
    again on the same day resumes after the last saved page.
    """
    get_pages(
        BASE_URL,
        listings_folder(data_folder, run_date),
        sleep_mean=sleep_mean,
        sleep_std=sleep_std,
        log_num_pages=log_num_pages,
        max_pages=max_pages,
        engine=engine,
        order=order,
        known_job_ids=set(load_jobs(data_folder)) if stop_after_known_pages else None,
        stop_after_known_pages=stop_after_known_pages,
    )


@app.command("extract-data")
def extract_trabalha_brasil_data(data_folder: str = DataFolder):
    """
    Extracts the jobs of all saved listing pages into <data-folder>/vagas.csv
    (one row per job, keeping the details already collected).
    """
    jobs = update_jobs_from_listings(data_folder)
    print(f"{len(jobs)} job(s) saved in {data_folder}/{JOBS_CSV}")


@app.command("get-details")
def get_trabalha_brasil_details(
    data_folder: str = DataFolder,
    max_jobs: Optional[int] = typer.Option(None, help="Maximum number of new jobs (without details) to visit in this run."),
    recheck: bool = typer.Option(False, "--recheck", help="Also revisit open jobs to detect the ones that were closed."),
    max_recheck: Optional[int] = typer.Option(None, help="Maximum number of open jobs to revisit (with --recheck)."),
    sleep_mean: float = SleepMean,
    sleep_std: float = SleepStd,
    engine: str = Engine,
):
    """
    Visits each job page to collect its publication date, salary range and full
    description, and (with --recheck) detects closed jobs. Updates vagas.csv.
    """
    jobs = get_details(
        data_folder,
        max_jobs=max_jobs,
        recheck=recheck,
        max_recheck=max_recheck,
        sleep_mean=sleep_mean,
        sleep_std=sleep_std,
        engine=engine,
    )
    with_details = sum(1 for job in jobs.values() if job.get("details_fetched_at"))
    closed = sum(1 for job in jobs.values() if job.get("closed_detected_at"))
    print(f"{len(jobs)} job(s) in {data_folder}/{JOBS_CSV}: {with_details} with details, {closed} detected as closed")


@app.command("daily")
def daily_collection(
    data_folder: str = DataFolder,
    max_pages: Optional[int] = typer.Option(100, help="Maximum number of listing pages (15 jobs each)."),
    stop_after_known_pages: int = typer.Option(3, help="Stop the listing after N pages in a row with no new job."),
    max_jobs: Optional[int] = typer.Option(2000, help="Maximum number of new jobs to get details for."),
    max_recheck: Optional[int] = typer.Option(1000, help="Maximum number of open jobs to revisit to detect closings."),
    sleep_mean: float = SleepMean,
    sleep_std: float = SleepStd,
    engine: str = typer.Option("requests", help='"requests" (default here, lighter) or "playwright".'),
):
    """
    Daily incremental collection: newest jobs of the listing + their details +
    revisits of open jobs to detect closings. Meant to run once a day (see
    .github/workflows/coleta-diaria.yml).
    """
    run_daily(
        data_folder,
        max_pages=max_pages,
        stop_after_known_pages=stop_after_known_pages,
        max_jobs=max_jobs,
        max_recheck=max_recheck,
        sleep_mean=sleep_mean,
        sleep_std=sleep_std,
        engine=engine,
    )


@app.command("shard")
def intensive_shard(
    data_folder: str = DataFolder,
    shard: int = typer.Option(..., help="Number of this shard (0 to n-shards - 1)."),
    n_shards: int = typer.Option(..., help="Number of shards running in parallel."),
    state_file: str = typer.Option(..., help="JSON with the occupations already read by this shard (kept between runs)."),
    min_job_id: int = typer.Option(..., help="Smallest job id of interest: start of the period (ids grow with the publication date)."),
    partial: str = typer.Option(..., help="CSV where the jobs added or changed by this shard are written."),
    listing_minutes: float = typer.Option(90, help="Time for reading listings, in minutes."),
    total_minutes: float = typer.Option(300, help="Total time of the run, in minutes."),
    max_recheck: Optional[int] = typer.Option(400, help="Maximum number of open jobs to revisit."),
    sleep_mean: float = SleepMean,
    sleep_std: float = SleepStd,
    engine: str = typer.Option("requests", help='"requests" (default here) or "playwright".'),
):
    """
    One machine of the intensive (parallel) collection: general listing (shard 0),
    listings by occupation back to --min-job-id, details and rechecks of its share.
    """
    run_shard(
        data_folder, shard, n_shards, state_file, min_job_id, listing_minutes=listing_minutes,
        total_minutes=total_minutes, max_recheck=max_recheck, sleep_mean=sleep_mean, sleep_std=sleep_std,
        engine=engine, partial_path=partial,
    )


@app.command("merge")
def merge_partials(
    partials: list[str] = typer.Argument(..., help="Partial CSVs written by the shards."),
    data_folder: str = DataFolder,
):
    """Merges the partial CSVs of the shards into <data-folder>/vagas.csv (nothing is removed)."""
    base = load_jobs(data_folder)
    merged = merge_jobs(base, [load_jobs_file(path) for path in partials])
    if len(merged) < len(base):
        raise typer.Exit(code=1)
    save_jobs(data_folder, merged)
    print(f"vagas.csv: {len(base)} -> {len(merged)} job(s) ({len(partials)} partial file(s))")
