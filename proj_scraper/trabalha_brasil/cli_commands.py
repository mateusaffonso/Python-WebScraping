from datetime import date
from typing import Optional

import typer

from trabalha_brasil.get_details import get_details, update_jobs_from_listings
from trabalha_brasil.get_pages import get_pages
from trabalha_brasil.storage import JOBS_CSV, listings_folder

app = typer.Typer()

BASE_URL = "https://www.trabalhabrasil.com.br/vagas-de-emprego"

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
    max_jobs: Optional[int] = typer.Option(None, help="Maximum number of job pages to visit in this run."),
    recheck: bool = typer.Option(False, "--recheck", help="Also revisit open jobs to detect the ones that were closed."),
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
        sleep_mean=sleep_mean,
        sleep_std=sleep_std,
        engine=engine,
    )
    with_details = sum(1 for job in jobs.values() if job.get("details_fetched_at"))
    closed = sum(1 for job in jobs.values() if job.get("closed_detected_at"))
    print(f"{len(jobs)} job(s) in {data_folder}/{JOBS_CSV}: {with_details} with details, {closed} detected as closed")
