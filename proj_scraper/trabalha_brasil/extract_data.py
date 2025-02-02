from bs4 import BeautifulSoup


def _extract_title(job_data_block: str) -> str:
    title = job_data_block.find("h2")
    return title.text


def _extract_company(job_data_block: str) -> str:
    company = job_data_block.find("p")
    return company.text


def _extract_city(job_data_block: str) -> str:
    city = job_data_block.findall("strong")[0]
    return city.text


def _extract_state(job_data_block: str) -> str:
    state = job_data_block.findall("strong")[1]
    return state.text


def extract_page_data(page: str) -> list[dict]:
    """
    Extracts the data from a page.
    """
    page_bs4 = BeautifulSoup(page, "html.parser")
    jobs_blocks = page_bs4.find_all(class_="jobCard")
    extracted_jobs = []

    for job_block in jobs_blocks:
        job_data_block = job_block.find(class_="jobCard")
        job_header = job_data_block.find(class_="jobHeader")
        job_body = job_data_block.find(class_="jobBody")

        title = _extract_title(job_header)
        company = _extract_company(job_header)
        city = _extract_city(job_body)
        state = _extract_state(job_body)
        job_doc = {
            "title": title,
            "company": company,
            "city": city,
            "state": state,
        }
        extracted_jobs.append(job_doc)
    return extracted_jobs
