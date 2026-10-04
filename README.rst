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
    cd /home/fabricio/projects/Python-WebScraping
    ```

3. Install the project dependencies:
    ```
    poetry install
    ```

4. Run the project:
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
The project includes a command-line interface (CLI) with the following main commands:

- `scrape`: Initiates the web scraping process.
  ```
  poetry run python cli.py scrape
  ```

- `process`: Processes the scraped data.
  ```
  poetry run python cli.py process
  ```

- `report`: Generates a report from the processed data.
  ```
  poetry run python cli.py report
  ```

Make sure to replace `main.py` and `cli.py` with the actual entry points of your project if they differ.