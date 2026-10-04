import csv
import os

import pytest

from tests.conftest import read_fixture
from trabalha_brasil import get_details as get_details_module
from trabalha_brasil import get_pages as get_pages_module
from trabalha_brasil.extract_data import extract_job_details, extract_page_data, is_job_closed
from trabalha_brasil.storage import list_page_files, listings_folder, load_jobs, save_jobs


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
