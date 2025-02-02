from bs4 import BeautifulSoup


def _extract_title(job_data_block: str) -> str:
    pass


def _extract_company(job_data_block: str) -> str:
    pass


def _extract_city(job_data_block: str) -> str:
    pass


def _extract_state(job_data_block: str) -> str:
    pass


def extract_page_data(page: str) -> list[dict]:
    """
    Extracts the data from a page.
    """
    page_bs4 = BeautifulSoup(page, "html.parser")
    jobs_blocks = page_bs4.find_all(class_="jobCard")
    extracted_jobs = []

    for job_block in jobs_blocks:
        job_data_block = job_block.find(class_="jobCard__info")
        title = _extract_title(job_data_block)
        company = _extract_company(job_data_block)
        city = _extract_city(job_data_block)
        state = _extract_state(job_data_block)
        job_doc = {
            "title": title,
            "company": company,
            "city": city,
            "state": state,
        }
        extracted_jobs.append(job_doc)
    return extracted_jobs

