Python Web Scraping Project
===========================

Purpose
-------
This project is designed to perform web scraping tasks using Python. It extracts data from websites and processes it for various use cases such as data analysis, reporting, and more.

Development Mode
----------------
To execute the project in development mode using Poetry, follow these steps:

1. Install Poetry if you haven't already:
    ```
    curl -sSL https://install.python-poetry.org | python3 -
    ```

2. Navigate to the project directory:
    ```
    cd Python-WebScraping
    ```

3. Install the project dependencies:
    ```
    poetry install
    ```

4. Run the project (see CLI Commands below):
    ```
    poetry run python proj_scraper/run.py trabalha-brasil --help
    ```

Deploying with Docker
---------------------
To deploy the project using Docker, follow these steps:

1. Build the Docker image:
    ```
    docker build -t python-webscraping .
    ```

2. Run the Docker container:
    ```
    docker run -d -p 8000:8000 python-webscraping
    ```

CLI Commands
------------
The CLI collects job postings from the Trabalha Brasil website
(https://www.trabalhabrasil.com.br/vagas-de-emprego). Every command accepts
``--data-folder`` (default ``./data``), which can point to a Google Drive folder.

- ``get-pages``: downloads the listing pages to ``<data-folder>/listings/<YYYY-MM-DD>/page_N.html``.
  Running it again on the same day resumes after the last saved page.
  ::

    poetry run python proj_scraper/run.py trabalha-brasil get-pages --max-pages 20

- ``extract-data``: extracts the jobs of all saved listing pages into ``<data-folder>/vagas.csv``
  (one row per job, with ``first_seen`` / ``last_seen`` collection days).
  ::

    poetry run python proj_scraper/run.py trabalha-brasil extract-data

- ``get-details``: visits each job page to collect the publication date (``date_posted``),
  salary range and full description. With ``--recheck`` it also revisits open jobs and
  fills ``closed_detected_at`` when a job page starts saying "A vaga foi encerrada".
  ::

    poetry run python proj_scraper/run.py trabalha-brasil get-details --max-jobs 100
    poetry run python proj_scraper/run.py trabalha-brasil get-details --recheck

Use ``--help`` on any command to see all the options (``--sleep-mean``, ``--sleep-std``,
``--engine playwright|requests``...).

About the dates
~~~~~~~~~~~~~~~
- ``date_posted`` comes from the job page structured data (schema.org ``JobPosting``).
- The website does not publish when a job closes. ``valid_through`` is filled automatically
  by the site (usually ``date_posted`` + 1 year) and should not be used as the closing date.
  The closing date is inferred: run ``get-details --recheck`` periodically and use
  ``closed_detected_at`` (precision = interval between runs).

Google Colab
------------
``notebooks/colab_trabalha_brasil.ipynb`` runs the whole pipeline on Google Colab and
saves the pages and ``vagas.csv`` to Google Drive.

Tests
-----
::

    pip install pytest beautifulsoup4 typer requests playwright
    python -m pytest
