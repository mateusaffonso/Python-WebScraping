"""
Storage layout inside the data folder:

    <data_folder>/
        listings/<YYYY-MM-DD>/page_<N>.html   raw listing pages, one folder per collection day
        listings/<YYYY-MM-DD>/run_<HHMMSS>/   pages of each run of the "daily" command
        vagas.csv                             one row per job (the main dataset)
"""

import csv
import os
import re

from trabalha_brasil.extract_data import DETAIL_FIELDS, LISTING_FIELDS

LISTINGS_DIR = "listings"
JOBS_CSV = "vagas.csv"

TRACKING_FIELDS = [
    "first_seen",  # first collection day in which the job appeared in the listing
    "last_seen",  # last collection day in which the job appeared in the listing
    "details_fetched_at",  # when the job page was downloaded for the first time
    "last_checked_at",  # last time the job page was (re)visited
    "closed_detected_at",  # first time the job page said "A vaga foi encerrada"
    "fetch_errors",  # failed attempts to download the job page (not retried after 3)
]

DERIVED_FIELDS = [
    "closed",  # job page said "A vaga foi encerrada" in the last visit
    # True when the listing shows no salary ("a combinar") but the job page has a
    # salary range: the range is an estimate made by the site, not the employer's offer.
    "salary_estimated",
    # True when the job page was downloaded and had the site's structured job data
    # (JobPosting): publication date, company etc. confirmed on the site itself.
    "validated",
]

JOB_FIELDS = LISTING_FIELDS + TRACKING_FIELDS + DETAIL_FIELDS + DERIVED_FIELDS

PAGE_FILE_PATTERN = re.compile(r"^page_(\d+)\.html$")


def listings_folder(data_folder: str, run_date: str) -> str:
    """Returns the folder for the listing pages collected on run_date (YYYY-MM-DD)."""
    return os.path.join(data_folder, LISTINGS_DIR, run_date)


def list_page_files(folder: str) -> list[tuple[int, str]]:
    """
    Returns (page_number, path) for every page_<N>.html in the folder,
    sorted numerically (page_2 before page_10).
    """
    if not os.path.isdir(folder):
        return []
    pages = []
    for file_name in os.listdir(folder):
        match = PAGE_FILE_PATTERN.match(file_name)
        if match:
            pages.append((int(match.group(1)), os.path.join(folder, file_name)))
    return sorted(pages)


def list_page_files_recursive(folder: str) -> list[str]:
    """Returns the paths of every page_<N>.html in the folder and its subfolders (sorted)."""
    paths = []
    for root, dirs, _ in os.walk(folder):
        dirs.sort()
        paths += [path for _, path in list_page_files(root)]
    return paths


def list_listing_runs(data_folder: str) -> list[str]:
    """Returns the collection days (folder names) available, oldest first."""
    folder = os.path.join(data_folder, LISTINGS_DIR)
    if not os.path.isdir(folder):
        return []
    return sorted(d for d in os.listdir(folder) if os.path.isdir(os.path.join(folder, d)))


def write_text_atomic(path: str, content: str) -> None:
    """
    Writes a file through a temporary file and a rename, so that an interrupted
    run (e.g. a Colab disconnection) never leaves a half-written file behind.
    """
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp_path, path)


def load_jobs(data_folder: str) -> dict[str, dict]:
    """Loads vagas.csv as {job_id: row}. Returns {} if it does not exist yet."""
    path = os.path.join(data_folder, JOBS_CSV)
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {row["job_id"]: {field: row.get(field, "") for field in JOB_FIELDS} for row in csv.DictReader(f)}


def save_jobs(data_folder: str, jobs: dict[str, dict]) -> str:
    """Saves the jobs to vagas.csv (atomically) and returns the file path."""
    os.makedirs(data_folder, exist_ok=True)
    path = os.path.join(data_folder, JOBS_CSV)
    tmp_path = path + ".tmp"
    # utf-8-sig so that Excel / Google Sheets open the accents correctly
    with open(tmp_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=JOB_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for job in jobs.values():
            if job.get("details_fetched_at"):
                job["salary_estimated"] = bool(job.get("salary_max")) and not job.get("salary")
            job["validated"] = bool(job.get("date_posted"))
            writer.writerow(job)
    os.replace(tmp_path, path)
    return path


def _min_filled(*values: str) -> str:
    return min((v for v in values if v), default="")


def merge_jobs(base: dict[str, dict], partials: list[dict[str, dict]]) -> dict[str, dict]:
    """
    Merges the vagas.csv of parallel collections (each one started from base)
    into base. Nothing is removed: a job present in any input is in the result.

    For a job present in more than one input:
        - first dates (first_seen, details_fetched_at, closed_detected_at) take the earliest;
        - last dates (last_seen, last_checked_at) take the latest;
        - listing fields come from the input that saw the job last in the listing;
        - details come from the first input that has them (details collected while
          the job was open are never replaced by an empty closed page);
        - "closed" comes from the most recent visit.
    """
    merged = {job_id: dict(job) for job_id, job in base.items()}
    for partial in partials:
        for job_id, new in partial.items():
            old = merged.get(job_id)
            if old is None:
                merged[job_id] = dict(new)
                continue
            job = dict(old)
            if (new.get("last_seen") or "") > (old.get("last_seen") or ""):
                job.update({field: new.get(field, "") for field in LISTING_FIELDS})
            job["first_seen"] = _min_filled(old.get("first_seen"), new.get("first_seen"))
            job["last_seen"] = max(old.get("last_seen") or "", new.get("last_seen") or "")
            if not old.get("date_posted") and new.get("date_posted"):
                job.update({field: new.get(field, "") for field in DETAIL_FIELDS})
            job["details_fetched_at"] = _min_filled(old.get("details_fetched_at"), new.get("details_fetched_at"))
            if (new.get("last_checked_at") or "") > (old.get("last_checked_at") or ""):
                job["last_checked_at"] = new["last_checked_at"]
                job["closed"] = new.get("closed", "")
            job["closed_detected_at"] = _min_filled(old.get("closed_detected_at"), new.get("closed_detected_at"))
            job["fetch_errors"] = str(max(int(old.get("fetch_errors") or 0), int(new.get("fetch_errors") or 0)) or "")
            merged[job_id] = job
    return merged


def load_jobs_file(path: str) -> dict[str, dict]:
    """Loads any CSV with the vagas.csv columns as {job_id: row}."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        return {row["job_id"]: {field: row.get(field, "") for field in JOB_FIELDS} for row in csv.DictReader(f)}
