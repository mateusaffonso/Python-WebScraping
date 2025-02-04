from bs4 import BeautifulSoup


def _extract_title(job_data_block: str) -> str:
    title = job_data_block.find("h2")
    return title.text


def _extract_company(job_data_block: str) -> str:
    company = job_data_block.find("p")
    return company.text


def _extract_location(job_data_block: str) -> str:
    city = job_data_block.find_all("strong")[0]
    return city.text


def _extract_job_description(job_data_block: str) -> str:
    state = job_data_block.find_all("p")[0]
    return state.text


def extract_page_data(page: str) -> list[dict]:
    """
    Extracts the data from a page.
    """
    page_bs4 = BeautifulSoup(page, "html.parser")
    jobs_blocks = page_bs4.find_all(class_="jobCard")
    extracted_jobs = []

    for job_block in jobs_blocks:
        job_header = job_block.find(class_="jobHeader")
        job_body = job_block.find(class_="jobBody")
        title = _extract_title(job_header)
        company = _extract_company(job_header)
        location = _extract_location(job_body)
        description = _extract_job_description(job_body)
        job_doc = {
            "title": title,
            "company": company,
            "location": location,
            "description": description,
        }
        extracted_jobs.append(job_doc)
    return extracted_jobs
