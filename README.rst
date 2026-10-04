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

- ``daily``: incremental collection meant to run once a day. Reads the listing ordered by
  "Mais recentes" (``--order recent``) until it finds pages with only jobs already in
  ``vagas.csv``, collects the details of the new jobs and revisits open jobs to detect closings.
  ::

    poetry run python proj_scraper/run.py trabalha-brasil daily --max-pages 100 --max-jobs 2000 --max-recheck 1000

Use ``--help`` on any command to see all the options (``--sleep-mean``, ``--sleep-std``,
``--engine playwright|requests``...).

About the dates
~~~~~~~~~~~~~~~
- ``date_posted`` comes from the job page structured data (schema.org ``JobPosting``).
- The website does not publish when a job closes. ``valid_through`` is filled automatically
  by the site (usually ``date_posted`` + 1 year) and should not be used as the closing date.
  The closing date is inferred: run ``get-details --recheck`` periodically and use
  ``closed_detected_at`` (precision = interval between runs).

About the salary
~~~~~~~~~~~~~~~~
When the employer states a salary, ``salary_min`` is that value and ``salary_max`` is empty.
When the listing says "a combinar", the job page still brings a range (``salary_min`` /
``salary_max``) that is an estimate made by the site: those rows have ``salary_estimated = True``.

Automatic daily collection (GitHub Actions)
-------------------------------------------
``.github/workflows/coleta-diaria.yml`` runs ``daily`` every day at 06:17 (Brasília) on GitHub's
servers, so the computer can be off. Each run downloads ``vagas.csv`` from the Google Drive folder,
collects, checks that ``vagas.csv`` did not shrink and uploads it back, together with the day's
listing pages (``listings_compactadas/``) and the log (``logs/``). A copy is also kept as a
GitHub artifact for 7 days.

Setup (once), on a computer with a browser:

1. Install rclone: https://rclone.org/install/ (macOS: ``brew install rclone``).
2. Create the ``drive`` remote pointing to the Drive folder (log in with the account that owns it).
   ``root_folder_id`` is the id at the end of the folder URL
   (``https://drive.google.com/drive/folders/<id>``)::

    rclone config create drive drive scope=drive root_folder_id=<id-da-pasta-IC_scraper>
    rclone lsf drive:        # must list vagas.csv

3. Save the remote configuration as a repository secret named ``RCLONE_CONFIG``
   (GitHub > Settings > Secrets and variables > Actions > New repository secret), with the
   output of::

    rclone config show drive

4. Run it once by hand: GitHub > Actions > "Coleta diária" > Run workflow.

Notes:

- Without the secret the workflow runs in test mode (2 pages, 5 jobs) and uploads nothing.
- The secret gives access to the Google Drive of that account. Keep it only in the repository
  secrets and never commit ``rclone.conf``.
- Do not run the collection from Colab at the same time as the scheduled run: both write
  ``vagas.csv``. Use the notebook to look at the data.
- GitHub disables scheduled workflows of public repositories after 60 days without commits;
  re-enable it in the Actions tab if that happens.

Google Colab
------------
``notebooks/colab_trabalha_brasil.ipynb`` runs the whole pipeline on Google Colab and
saves the pages and ``vagas.csv`` to Google Drive.

Tests
-----
::

    pip install pytest beautifulsoup4 typer requests playwright
    python -m pytest
