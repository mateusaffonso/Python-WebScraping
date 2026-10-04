import json
import re

from bs4 import BeautifulSoup

BASE_SITE_URL = "https://www.trabalhabrasil.com.br"

# Text shown by the site when a job posting is no longer available.
CLOSED_JOB_MARKER = "A vaga foi encerrada"

LISTING_FIELDS = [
    "job_id",
    "url",
    "title",
    "company",
    "location",
    "salary",
    "workplace",
    "employment_type",
    "posted_label",
    "trending",
]

DETAIL_FIELDS = [
    "date_posted",
    "valid_through",
    "hiring_organization",
    "city",
    "state",
    "salary_min",
    "salary_max",
    "salary_currency",
    "salary_unit",
    "employment_type_code",
    "full_description",
]


def _text(element) -> str:
    """Returns the stripped text of a BeautifulSoup element, or "" if it is None."""
    if element is None:
        return ""
    return " ".join(element.get_text(" ", strip=True).split())


def _job_id_from_url(url: str) -> str:
    """Extracts the numeric job id from the end of a job URL."""
    match = re.search(r"/(\d+)/?$", url or "")
    return match.group(1) if match else ""


def _extract_job_card(card) -> dict:
    """
    Extracts the fields of a single job card (an <a class="job-link"> element)
    from the listing page.
    """
    href = card.get("href") or card.get("data-job-url") or ""
    url = href if href.startswith("http") else BASE_SITE_URL + href
    return {
        "job_id": _job_id_from_url(href),
        "url": url,
        "title": _text(card.find(class_="job-title")),
        "company": _text(card.find(class_="job-company")),
        "location": _text(card.find(class_="job-location")),
        "salary": _text(card.find(class_="salary")),
        "workplace": _text(card.find(class_="workplace")),
        "employment_type": _text(card.find(class_="employment-type")),
        "posted_label": _text(card.find(class_="posted")),
        "trending": card.find(class_="job-badge--trending") is not None,
    }


def extract_page_data(page: str) -> list[dict]:
    """
    Extracts job data from a listing page
    (https://www.trabalhabrasil.com.br/vagas-de-emprego?pagina=N).

    Args:
        page (str): The HTML content of the page as a string.

    Returns:
        list[dict]: One dictionary per job card, with the keys in LISTING_FIELDS.
            Fields not shown on the card (e.g. salary "a combinar") are "".
    """
    page_bs4 = BeautifulSoup(page, "html.parser")
    cards = page_bs4.select("a.job-link")
    return [_extract_job_card(card) for card in cards]


def _find_job_posting(page_bs4) -> dict | None:
    """Returns the schema.org JobPosting JSON-LD object of a job page, if any."""
    for script in page_bs4.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        candidates = data if isinstance(data, list) else data.get("@graph", [data])
        for item in candidates:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item
    return None


def is_job_closed(page: str) -> bool:
    """Returns True if the job page says the job posting was closed."""
    return CLOSED_JOB_MARKER.lower() in BeautifulSoup(page, "html.parser").get_text(" ").lower()


def extract_job_details(page: str) -> dict:
    """
    Extracts the details of a single job page using its schema.org JobPosting
    structured data (JSON-LD).

    Notes:
        - date_posted is the publication date informed by the site.
        - valid_through is filled automatically by the site (it is usually
          date_posted + 1 year), so it should NOT be used as the closing date.
          Closing dates are inferred by re-checking the job (see is_job_closed).

    Args:
        page (str): The full HTML of the job page (including <head>).

    Returns:
        dict: The keys in DETAIL_FIELDS plus "closed" (bool). If the page has no
            JobPosting data (e.g. closed jobs), the DETAIL_FIELDS are "".
    """
    page_bs4 = BeautifulSoup(page, "html.parser")
    details = {field: "" for field in DETAIL_FIELDS}
    details["closed"] = CLOSED_JOB_MARKER.lower() in page_bs4.get_text(" ").lower()

    posting = _find_job_posting(page_bs4)
    if posting is None:
        return details

    address = (posting.get("jobLocation") or {}).get("address") or {}
    salary = posting.get("baseSalary") or {}
    salary_value = salary.get("value") or {}
    employment_type = posting.get("employmentType") or ""
    if isinstance(employment_type, list):
        employment_type = ",".join(employment_type)

    details.update(
        {
            "date_posted": posting.get("datePosted", ""),
            "valid_through": posting.get("validThrough", ""),
            "hiring_organization": (posting.get("hiringOrganization") or {}).get("name", ""),
            "city": address.get("addressLocality", ""),
            "state": address.get("addressRegion", ""),
            "salary_min": salary_value.get("minValue", salary_value.get("value", "")),
            "salary_max": salary_value.get("maxValue", ""),
            "salary_currency": salary.get("currency", ""),
            "salary_unit": salary_value.get("unitText", ""),
            "employment_type_code": employment_type,
            "full_description": _text(BeautifulSoup(posting.get("description", ""), "html.parser")),
        }
    )
    return details
