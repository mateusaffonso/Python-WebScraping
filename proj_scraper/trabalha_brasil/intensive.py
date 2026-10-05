"""
Intensive collection: several machines (shards) in parallel, each with its own
share of the work, merged afterwards into a single vagas.csv (see merge_jobs).

Each shard:
    1. (shard 0 only) reads the general "Mais recentes" listing, up to the site's
       limit of 500 pages, stopping when it reaches jobs already collected;
    2. reads the "Mais recentes" listing of its share of the occupations
       (/vagas-de-emprego/<occupation>), going back until jobs older than
       min_job_id (the start of the period of interest). An occupation read to the
       end is recorded in the state file and is not read again;
    3. downloads the job page of the new jobs it found and of its share of the
       jobs still without details (validation on the site itself), newest first;
    4. revisits its share of the open jobs to detect closings.
It then writes a partial CSV with only the jobs it added or changed.
"""

import csv
import json
import os
import re
import time
import zlib
from datetime import date, datetime

from lib.web_scraper import create_scraper
from trabalha_brasil.get_details import get_details, update_jobs_from_listings
from trabalha_brasil.get_pages import BASE_URL, get_pages, sleep_between_requests
from trabalha_brasil.storage import JOB_FIELDS, listings_folder, load_jobs

AREAS_URL = "https://www.trabalhabrasil.com.br/vagas-de-emprego-por-area-de-atuacao"
SITE_URL = "https://www.trabalhabrasil.com.br"

# When the site refuses a listing (e.g. 403), pause this long; give up the
# listings of the run after MAX_FAILURES_IN_A_ROW refusals in a row.
BLOCK_PAUSE = 120
MAX_FAILURES_IN_A_ROW = 5


def shard_of(key: str, n_shards: int) -> int:
    """Stable shard number of a job id or occupation (the same on every machine)."""
    return zlib.crc32(key.encode()) % n_shards


def list_occupations(engine: str = "requests", sleep_seconds: float = 0.7) -> list[str]:
    """
    Returns the occupation slugs of the site (e.g. "vendedor"), read from the
    pages of each area of activity.
    """
    scraper = create_scraper(engine)
    try:
        areas_page = scraper.get_html(AREAS_URL)
        areas = sorted(set(re.findall(r'href="(/busca-de-vagas-area/[^"]+)"', areas_page)))
        occupations = set()
        for area in areas:
            try:
                page = scraper.get_html(SITE_URL + area)
            except Exception as e:
                print(f"Error on area {area}: {e}")
                continue
            occupations |= set(re.findall(r'href="/vagas-de-emprego/([^"/?#]+)"', page))
            time.sleep(sleep_seconds)
    finally:
        scraper.close_down()
    print(f"{len(occupations)} occupations in {len(areas)} areas")
    return sorted(occupations)


def _load_state(path: str) -> dict:
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_state(path: str, state: dict) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os.replace(tmp_path, path)


def run_shard(
    data_folder: str,
    shard: int,
    n_shards: int,
    state_path: str,
    min_job_id: int,
    listing_minutes: float = 90,
    total_minutes: float = 300,
    max_recheck: int | None = 400,
    sleep_mean: float = 2.0,
    sleep_std: float = 0.5,
    engine: str = "requests",
    partial_path: str | None = None,
) -> dict[str, dict]:
    """One shard of the intensive collection (see the module docstring)."""
    start = time.time()
    deadline = start + total_minutes * 60
    state = _load_state(state_path)
    if not state.get("occupations"):
        state["occupations"] = list_occupations(engine)
        _save_state(state_path, state)
    listing_deadline = time.time() + listing_minutes * 60
    base = load_jobs(data_folder)
    print(f"== Shard {shard}/{n_shards}: {len(base)} job(s) already known")

    run_folder = os.path.join(
        listings_folder(data_folder, date.today().isoformat()), f"intensiva_{datetime.now():%H%M%S}_s{shard}"
    )
    if shard == 0:
        print("== General listing (most recent first)")
        try:
            get_pages(
                BASE_URL, os.path.join(run_folder, "geral"), sleep_mean=sleep_mean, sleep_std=sleep_std,
                log_num_pages=50, max_pages=500, engine=engine, order="recent", known_job_ids=set(base),
                stop_after_known_pages=3, min_pages=40, deadline=listing_deadline,
            )
        except RuntimeError as e:
            print(f"General listing interrupted ({e}); the pages saved so far are used.")
            time.sleep(BLOCK_PAUSE)

    state.setdefault("done", [])
    state["min_job_id"] = min_job_id
    done = set(state["done"])
    mine = [o for o in state["occupations"] if shard_of(o, n_shards) == shard and o not in done]
    print(f"== Occupations: {len(mine)} to read in this shard ({len(done)} already read)")
    failures_in_a_row = 0
    for i, occupation in enumerate(mine, 1):
        if time.time() > listing_deadline:
            print("Listing time limit reached: the remaining occupations stay for the next run.")
            break
        stats = {}
        try:
            get_pages(
                f"{BASE_URL}/{occupation}", os.path.join(run_folder, "cargos", occupation), sleep_mean=sleep_mean,
                sleep_std=sleep_std, log_num_pages=100, max_pages=500, engine=engine, order="recent",
                min_job_id=min_job_id, deadline=listing_deadline, stats=stats,
            )
            failures_in_a_row = 0
        except RuntimeError as e:
            # e.g. "403 Forbidden": the site is limiting requests. Pause; the occupation
            # is not marked as read, so it is read again in the next run.
            failures_in_a_row += 1
            print(f"Occupation {occupation} interrupted ({e}); pausing {BLOCK_PAUSE} s")
            if failures_in_a_row >= MAX_FAILURES_IN_A_ROW:
                print("Too many failures in a row: leaving the listings for the next run.")
                break
            time.sleep(BLOCK_PAUSE)
            continue
        if stats.get("stop_reason") != "deadline":
            state["done"].append(occupation)
            _save_state(state_path, state)
        if i % 50 == 0:
            print(f"{i}/{len(mine)} occupations read")
        sleep_between_requests(sleep_mean, sleep_std)
    _save_state(state_path, state)

    # Details: this shard's share of the known jobs + every job it found now.

    jobs = update_jobs_from_listings(data_folder)
    eligible = {job_id for job_id in jobs if job_id not in base or shard_of(job_id, n_shards) == shard}
    print(f"== Job pages: {len(jobs) - len(base)} new job(s) found in this run")
    jobs = get_details(
        data_folder, recheck=True, max_recheck=max_recheck, sleep_mean=sleep_mean, sleep_std=sleep_std,
        engine=engine, log_num_jobs=200, eligible_ids=eligible, deadline=deadline,
    )

    tracked = ("last_seen", "last_checked_at", "details_fetched_at", "fetch_errors")
    changed = {
        job_id: job
        for job_id, job in jobs.items()
        if job_id not in base or any(str(job.get(f) or "") != str(base[job_id].get(f) or "") for f in tracked)
    }
    if partial_path:
        _save_partial(partial_path, changed)
    with_details = sum(1 for job in changed.values() if job.get("date_posted"))
    print(f"== Summary shard {shard}: {len(changed)} job(s) added or changed ({with_details} validated)")
    return jobs


def _save_partial(path: str, jobs: dict[str, dict]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=JOB_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for job in jobs.values():
            writer.writerow(job)
