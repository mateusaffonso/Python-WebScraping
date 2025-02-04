import os
import typer
from trabalha_brasil.get_pages import get_pages
from trabalha_brasil.extract_data import extract_page_data

app = typer.Typer()


@app.command("get-pages")
def get_trabalha_brasil_pages():
    """
    Command to scrape job listing pages from the Trabalha Brasil website.

    This function uses the `get_pages` function to scrape job listings from the
    Trabalha Brasil website and save them to the specified output folder. The
    function is registered as a command with the name 'get-pages'.

    Parameters:
    None

    Returns:
    None

    Notes:
    - The base URL for the job listings is "https://www.trabalhabrasil.com.br/vagas-empregos".
    - The output folder for the scraped data is "./data/".
    - The mean sleep time between requests is 2 seconds.
    - The standard deviation of the sleep time is 0.5 seconds.
    - The number of pages to log is 1.
    """
    base_url = "https://www.trabalhabrasil.com.br/vagas-empregos"
    output_folder = "./data/"
    sleep_mean = 2
    sleep_std = 0.5
    log_num_pages = 1
    get_pages(base_url, output_folder, sleep_mean, sleep_std, log_num_pages)


@app.command("extract-data")
def extract_trabalha_brasil_data():
    """
    Extracts job data from HTML files located in the './data' directory.

    This function iterates over all files in the './data' directory, reads the content of each file,
    and processes the HTML content to extract job data using the `extract_page_data` function.
    The extracted job data is then printed to the console.

    Note:
        The function assumes that the files in the './data' directory are HTML files containing job listings.

    Raises:
        FileNotFoundError: If the './data' directory does not exist or if any of the files cannot be found.
        IOError: If there is an error reading any of the files.

    Example:
        >>> extract_trabalha_brasil_data()
        Processing file example.html
        [{'title': 'Software Engineer', 'company': 'Tech Company', 'location': 'City, Country', 'salary': '1000-2000'}]
        --------------------------------------------------
    """
    for file in os.listdir("./data"):
        print(f"Processing file {file}")
        with open(f"./data/{file}") as f:
            page = f.read()
            jobs = extract_page_data(page)
            print(jobs)
            print("-" * 50)
