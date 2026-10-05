import csv
import os

import pytest

from tests.conftest import read_fixture
from trabalha_brasil import get_details as get_details_module
from trabalha_brasil import get_pages as get_pages_module
from trabalha_brasil.extract_data import extract_job_details, extract_page_data, is_job_closed
from trabalha_brasil.storage import list_page_files, listings_folder, load_jobs, merge_jobs, save_jobs


@pytest.fixture(autouse=True)
def no_retry_wait(monkeypatch):
    monkeypatch.setattr(get_pages_module, "EMPTY_PAGE_WAIT", 0)


# ---------- extraction ----------


def test_extract_page_data_new_layout():
    jobs = extract_page_data(read_fixture("listing_page.html"))
    assert len(jobs) == 2

    first, second = jobs
    assert first == {
        "job_id": "13684778",
        "url": "https://www.trabalhabrasil.com.br/vagas-de-emprego-em-mongagua-sp/atendente-comercial/13684778",
        "title": "Vaga de Atendente Comercial",
        "company": "Empresa Confidencial",
        "location": "Mongaguá/SP",
        "salary": "R$ 1.800,00 por mês",
        "workplace": "Presencial",
        "employment_type": "Efetivo/CLT +1",
        "posted_label": "Últimos 3 dias",
        "trending": True,
    }
    # Card without salary: location must still be the city, salary empty.
    assert second["location"] == "Cuiabá/MT"
    assert second["salary"] == ""
    assert second["trending"] is False


def test_extract_job_details():
    details = extract_job_details(read_fixture("job_page.html"))
    assert details["date_posted"] == "2026-10-02"
    assert details["valid_through"] == "2027-10-02T19:57:31-03:00"
    assert details["hiring_organization"] == "Rh Vagas"
    assert (details["city"], details["state"]) == ("Belém", "PA")
    assert (details["salary_min"], details["salary_max"]) == (1980.32, 2662.4)
    assert details["salary_unit"] == "MONTH"
    assert details["employment_type_code"] == "FULL_TIME"
    assert "<div>" not in details["full_description"]
    assert "Estamos contratando" in details["full_description"]
    assert details["closed"] is False


def test_extract_job_details_closed_job():
    page = read_fixture("closed_job_page.html")
    details = extract_job_details(page)
    assert details["closed"] is True
    assert details["date_posted"] == ""
    assert is_job_closed(page)


# ---------- listing pages ----------


class FakeScraper:
    """Serves pages from a dict {url_substring: html} instead of the internet."""

    def __init__(self, pages):
        self.pages = pages
        self.requested = []
        self.closed = False

    def _find(self, url):
        self.requested.append(url)
        for key, html in self.pages.items():
            if url.endswith(key):
                return html
        return "<html><body>Nenhuma vaga encontrada</body></html>"

    get_page = _find
    get_html = _find

    def close_down(self):
        self.closed = True


def _listing(*job_ids):
    cards = "".join(
        f'<a class="job-link" href="/vagas-de-emprego-em-x/y/{i}" data-job-url="/vagas-de-emprego-em-x/y/{i}">'
        f'<h2 class="job-title">Vaga {i}</h2><p class="job-location"><span>Rio de Janeiro/RJ</span></p></a>'
        for i in job_ids
    )
    return f"<html><body>{cards}</body></html>"


def test_get_pages_resumes_stops_and_sorts_numerically(tmp_path, monkeypatch):
    pages = {f"?pagina={n}": _listing(n * 100 + 1, n * 100 + 2) for n in range(1, 12)}
    fake = FakeScraper(pages)
    monkeypatch.setattr(get_pages_module, "create_scraper", lambda engine: fake)

    folder = str(tmp_path / "listings" / "2026-10-04")
    assert get_pages_module.get_pages("https://site/vagas", folder, max_pages=10) == 10
    assert fake.closed
    # Resumes at page 11 (page_10 sorted after page_9) and stops at the empty page 12.
    assert get_pages_module.get_pages("https://site/vagas", folder) == 1
    assert fake.requested[-1].endswith("?pagina=12")
    assert [n for n, _ in list_page_files(folder)] == list(range(1, 12))


def test_get_pages_stops_when_page_repeats(tmp_path, monkeypatch):
    fake = FakeScraper({"?pagina=1": _listing(1, 2), "?pagina=2": _listing(3), "?pagina=3": _listing(1, 2)})
    monkeypatch.setattr(get_pages_module, "create_scraper", lambda engine: fake)
    assert get_pages_module.get_pages("https://site/vagas", str(tmp_path)) == 2


def test_sleep_is_never_negative(monkeypatch):
    slept = []
    monkeypatch.setattr(get_pages_module.time, "sleep", slept.append)
    monkeypatch.setattr(get_pages_module.random, "gauss", lambda mean, std: -3.0)
    get_pages_module.sleep_between_requests(2, 0.5)
    assert slept == [get_pages_module.MIN_SLEEP_SECONDS]


# ---------- details and closing detection ----------


def test_get_details_and_closing_detection(tmp_path, monkeypatch):
    data = str(tmp_path)
    for run_date, html in [("2026-10-01", _listing(13687383, 2)), ("2026-10-03", _listing(13687383))]:
        os.makedirs(listings_folder(data, run_date))
        with open(os.path.join(listings_folder(data, run_date), "page_1.html"), "w", encoding="utf-8") as f:
            f.write(html)

    open_page = read_fixture("job_page.html")
    fake = FakeScraper({"/13687383": open_page, "/2": open_page})
    monkeypatch.setattr(get_details_module, "create_scraper", lambda engine: fake)

    get_details_module.get_details(data)
    jobs = load_jobs(data)
    assert set(jobs) == {"13687383", "2"}
    job = jobs["13687383"]
    assert (job["first_seen"], job["last_seen"]) == ("2026-10-01", "2026-10-03")
    assert job["date_posted"] == "2026-10-02"
    assert job["closed_detected_at"] == ""

    # Next day the job is closed: recheck records the closing and keeps the old details.
    fake.pages["/13687383"] = read_fixture("closed_job_page.html")
    for j in jobs.values():
        j["last_checked_at"] = "2000-01-01T00:00:00"
    save_jobs(data, jobs)
    get_details_module.get_details(data, recheck=True)
    job = load_jobs(data)["13687383"]
    assert job["closed_detected_at"] != ""
    assert job["closed"] == "True"
    assert job["date_posted"] == "2026-10-02"

    with open(os.path.join(data, "vagas.csv"), encoding="utf-8-sig") as f:
        assert len(list(csv.DictReader(f))) == 2


def test_create_scraper_rejects_unknown_engine():
    from lib.web_scraper import create_scraper

    with pytest.raises(ValueError):
        create_scraper("selenium")


# ---------- incremental (daily) collection ----------


def test_build_listing_url():
    assert get_pages_module.build_listing_url("https://site/vagas", 3) == "https://site/vagas?pagina=3"
    assert get_pages_module.build_listing_url("https://site/vagas", 3, "recent") == "https://site/vagas?Ordenacao=2&pagina=3"
    with pytest.raises(ValueError):
        get_pages_module.build_listing_url("https://site/vagas", 1, "oldest")


def test_get_pages_stops_after_known_pages(tmp_path, monkeypatch):
    # Pages 1-2 have new jobs; from page 3 on, only jobs collected on previous days.
    pages = {f"pagina={n}": _listing(n * 10 + 1, n * 10 + 2) for n in range(1, 10)}
    fake = FakeScraper(pages)
    monkeypatch.setattr(get_pages_module, "create_scraper", lambda engine: fake)
    known = {str(n * 10 + i) for n in range(3, 10) for i in (1, 2)}

    saved = get_pages_module.get_pages(
        "https://site/vagas", str(tmp_path), order="recent", known_job_ids=known, stop_after_known_pages=2
    )
    assert saved == 4  # pages 1, 2 (new) + 3, 4 (known) -> stop
    assert fake.requested[0] == "https://site/vagas?Ordenacao=2&pagina=1"


def test_jobs_to_visit_limits_new_and_rechecks():
    jobs = {str(i): {"job_id": str(i), "details_fetched_at": ""} for i in range(1, 6)}
    for i in range(6, 11):
        jobs[str(i)] = {"job_id": str(i), "details_fetched_at": "x", "last_checked_at": f"2026-01-{i:02d}", "closed_detected_at": ""}
    jobs["10"]["closed_detected_at"] = "2026-02-01"  # already closed: never revisited

    visit = get_details_module._jobs_to_visit(jobs, recheck=True, max_jobs=2, max_recheck=3)
    assert [job["job_id"] for job in visit] == ["5", "4", "6", "7", "8"]  # newest new jobs, then oldest checks


def test_daily_run_and_salary_estimated(tmp_path, monkeypatch):
    data = str(tmp_path)
    listing = _listing(13687383, 13684778)
    fake = FakeScraper({"pagina=1": listing, "/13687383": read_fixture("job_page.html"), "/13684778": read_fixture("closed_job_page.html")})
    monkeypatch.setattr(get_pages_module, "create_scraper", lambda engine: fake)
    monkeypatch.setattr(get_details_module, "create_scraper", lambda engine: fake)
    monkeypatch.setattr(get_pages_module.time, "sleep", lambda s: None)

    from trabalha_brasil.daily import run_daily

    run_daily(data, max_pages=5, stop_after_known_pages=1, min_pages=0, run_date="2026-10-05")
    jobs = load_jobs(data)
    assert set(jobs) == {"13687383", "13684778"}
    # The fixture job has no salary on the card but a min/max range on its page.
    assert jobs["13687383"]["salary_estimated"] == "True"
    assert jobs["13687383"]["first_seen"] == "2026-10-05"
    assert jobs["13684778"]["closed_detected_at"] != ""


def test_daily_runs_start_from_page_one_without_overwriting(tmp_path, monkeypatch):
    data = str(tmp_path)
    fake = FakeScraper({"pagina=1": _listing(1, 2), "pagina=2": _listing(3)})
    monkeypatch.setattr(get_pages_module, "create_scraper", lambda engine: fake)
    monkeypatch.setattr(get_details_module, "create_scraper", lambda engine: fake)
    monkeypatch.setattr(get_pages_module.time, "sleep", lambda s: None)
    import trabalha_brasil.daily as daily_module

    stamps = iter(["010000", "040000"])

    class FakeDatetime:
        @staticmethod
        def now():
            class _Now:
                def strftime(self, fmt):
                    return next(stamps)

            return _Now()

    monkeypatch.setattr(daily_module, "datetime", FakeDatetime)
    kwargs = dict(max_pages=5, stop_after_known_pages=1, min_pages=0, max_jobs=0, max_recheck=0, run_date="2026-10-05")
    daily_module.run_daily(data, **kwargs)
    fake.pages["pagina=1"] = _listing(4, 1)  # a new job (4) arrived at the top
    daily_module.run_daily(data, **kwargs)

    day = listings_folder(data, "2026-10-05")
    assert sorted(os.listdir(day)) == ["run_010000", "run_040000"]
    assert len(os.listdir(os.path.join(day, "run_010000"))) == 2  # first run pages kept
    assert set(load_jobs(data)) == {"1", "2", "3", "4"}
    # Second run started from page 1 again (found job 4) and stopped at the known page 2.
    assert [u for u in fake.requested if "pagina" in u][-2:] == [
        "https://www.trabalhabrasil.com.br/vagas-de-emprego?Ordenacao=2&pagina=1",
        "https://www.trabalhabrasil.com.br/vagas-de-emprego?Ordenacao=2&pagina=2",
    ]


# ---------- site structure found on 05/10/2026 ----------


def test_known_pages_only_count_after_min_pages(tmp_path, monkeypatch):
    # Block 1 (pages 1-3): sparse sample, all known. Block 2 (pages 4-7): new jobs, then
    # jobs collected in previous runs (the site does not repeat block 1 jobs in block 2).
    pages = {"pagina=1": _listing(901, 902), "pagina=2": _listing(801), "pagina=3": _listing(701)}
    pages.update({"pagina=4": _listing(950, 949), "pagina=5": _listing(948, 947), "pagina=6": _listing(900), "pagina=7": _listing(899)})
    fake = FakeScraper(pages)
    monkeypatch.setattr(get_pages_module, "create_scraper", lambda engine: fake)
    known = {"901", "902", "801", "701", "900", "899"}
    stats = {}
    saved = get_pages_module.get_pages(
        "https://site/vagas", str(tmp_path), order="recent", known_job_ids=known,
        stop_after_known_pages=2, min_pages=3, stats=stats,
    )
    assert saved == 7 and stats["stop_reason"] == "known"


def test_stops_at_jobs_older_than_min_job_id(tmp_path, monkeypatch):
    pages = {f"pagina={n}": _listing(1000 - n * 10, 999 - n * 10) for n in range(1, 20)}
    fake = FakeScraper(pages)
    monkeypatch.setattr(get_pages_module, "create_scraper", lambda engine: fake)
    stats = {}
    saved = get_pages_module.get_pages("https://site/cargo", str(tmp_path), order="recent", min_job_id=955, stats=stats)
    # Pages 1-4 have ids >= 955; pages 5 and 6 are older -> stop after 2 old pages.
    assert saved == 6 and stats["stop_reason"] == "old"


def test_temporarily_empty_page_is_retried(tmp_path, monkeypatch):
    calls = {"n": 0}
    fake = FakeScraper({"pagina=1": _listing(*range(100, 115))})  # a full page (15 jobs)

    def flaky(url):
        calls["n"] += 1
        if url.endswith("pagina=2") and calls["n"] == 2:
            return "<html><body>Nenhuma vaga</body></html>"
        if url.endswith("pagina=2"):
            return _listing(2)
        return FakeScraper._find(fake, url)

    fake.get_page = flaky
    monkeypatch.setattr(get_pages_module, "create_scraper", lambda engine: fake)
    saved = get_pages_module.get_pages("https://site/vagas", str(tmp_path), order="recent", max_pages=2)
    assert saved == 2


def test_merge_jobs_keeps_everything_and_best_values():
    base = {"1": {"job_id": "1", "first_seen": "2026-10-04", "last_seen": "2026-10-04", "date_posted": "2026-10-03",
                  "details_fetched_at": "2026-10-04T01:00:00", "last_checked_at": "2026-10-04T01:00:00", "closed": "False"},
            "2": {"job_id": "2", "first_seen": "2026-10-04", "last_seen": "2026-10-04"}}
    shard_a = {"1": {**base["1"], "last_seen": "2026-10-06", "last_checked_at": "2026-10-06T10:00:00", "closed": "True",
                     "closed_detected_at": "2026-10-06T10:00:00", "date_posted": ""},
               "3": {"job_id": "3", "first_seen": "2026-10-06", "last_seen": "2026-10-06", "date_posted": "2026-10-06"}}
    shard_b = {"2": {**base["2"], "date_posted": "2026-10-02", "details_fetched_at": "2026-10-06T11:00:00"},
               "3": {"job_id": "3", "first_seen": "2026-10-06", "last_seen": "2026-10-06"}}
    merged = merge_jobs(base, [shard_a, shard_b])
    assert set(merged) == {"1", "2", "3"}
    assert merged["1"]["date_posted"] == "2026-10-03"  # details from when it was open are kept
    assert merged["1"]["closed"] == "True" and merged["1"]["closed_detected_at"] == "2026-10-06T10:00:00"
    assert merged["1"]["last_seen"] == "2026-10-06" and merged["1"]["first_seen"] == "2026-10-04"
    assert merged["2"]["date_posted"] == "2026-10-02"
    assert merged["3"]["date_posted"] == "2026-10-06"
    assert merge_jobs(merged, [shard_a, shard_b]) == merged  # merging again changes nothing


def test_shard_collects_occupation_and_writes_partial(tmp_path, monkeypatch):
    from trabalha_brasil import intensive

    data = str(tmp_path / "data")
    save_jobs(data, {"13600000": {"job_id": "13600000", "url": "https://www.trabalhabrasil.com.br/x/y/13600000",
                                  "first_seen": "2026-10-04", "last_seen": "2026-10-04"}})
    pages = {"vendedor?Ordenacao=2&pagina=1": _listing(13687383, 13684778),
             "vendedor?Ordenacao=2&pagina=2": _listing(13500001), "vendedor?Ordenacao=2&pagina=3": _listing(13500000),
             "/13687383": read_fixture("job_page.html"), "/13684778": read_fixture("closed_job_page.html")}
    fake = FakeScraper(pages)
    for module in (get_pages_module, get_details_module):
        monkeypatch.setattr(module, "create_scraper", lambda engine: fake)
    monkeypatch.setattr(get_pages_module.time, "sleep", lambda s: None)
    state = str(tmp_path / "estado.json")
    with open(state, "w") as f:
        f.write('{"occupations": ["vendedor"]}')
    partial = str(tmp_path / "parcial.csv")
    intensive.run_shard(data, shard=intensive.shard_of("vendedor", 2), n_shards=2, state_path=state,
                        min_job_id=13600000, max_recheck=0, sleep_mean=None, partial_path=partial)
    from trabalha_brasil.storage import load_jobs_file

    changed = load_jobs_file(partial)
    assert {"13687383", "13684778", "13500001", "13500000"} <= set(changed)
    assert changed["13687383"]["validated"] == "True" and changed["13687383"]["date_posted"] == "2026-10-02"
    assert changed["13684778"]["validated"] == "False" and changed["13684778"]["closed_detected_at"]
    import json
    assert json.load(open(state))["done"] == ["vendedor"]


def test_page_with_marker_but_no_job_cards_is_the_end(tmp_path, monkeypatch):
    # Rare occupations: page 2 has no job card, but "job-link" still appears in the HTML.
    empty = '<html><head><style>.job-link{color:red}</style></head><body>Nenhuma vaga</body></html>'
    fake = FakeScraper({"pagina=1": _listing(13600001), "pagina=2": empty, "pagina=3": empty})
    monkeypatch.setattr(get_pages_module, "create_scraper", lambda engine: fake)
    stats = {}
    saved = get_pages_module.get_pages("https://site/cargo", str(tmp_path), order="recent", min_job_id=1, stats=stats)
    assert saved == 1 and stats["stop_reason"] == "end"
