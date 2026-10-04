from bs4 import BeautifulSoup


def _extract_title(job_data_block: str) -> str:
    """
    Extracts the job title from a block of job data.

    Args:
        job_data_block (str): A string containing the HTML block of job data.

    Returns:
        str: The extracted job title.
    """
    title = job_data_block.find("h2")
    return title.text


def _extract_company(job_data_block: str) -> str:
    """
    Extracts the company name from a job data block.

    Args:
        job_data_block (str): The HTML block containing job data.

    Returns:
        str: The name of the company.
    """
    company = job_data_block.find("p")
    return company.text


def _extract_location(job_data_block: str) -> str:
    """
    Extracts the location (city) from a job data block.

    Args:
        job_data_block (str): The HTML block containing job data.

    Returns:
        str: The name of the city extracted from the job data block.
    """
    city = job_data_block.find_all("strong")[0]
    return city.text


def _extract_job_description(job_data_block: str) -> str:
    """
    Extracts the job description from a block of job data.

    Args:
        job_data_block (str): A string containing the HTML block of job data.

    Returns:
        str: The extracted job description text.
    """
    state = job_data_block.find_all("p")[0]
    return state.text


def extract_page_data(page: str) -> list[dict]:
    """
    Extracts job data from an HTML page.
    Args:
        page (str): The HTML content of the page as a string.
    Returns:
        list[dict]: A list of dictionaries, each containing job information with the following keys:
            - title (str): The job title.
            - company (str): The company offering the job.
            - location (str): The location of the job.
            - description (str): The job description.
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
