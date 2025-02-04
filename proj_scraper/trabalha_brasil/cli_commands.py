
import os
import typer
from trabalha_brasil.get_pages import get_pages
from trabalha_brasil.extract_data import extract_page_data 

app = typer.Typer()


@app.command('get-pages')
def get_trabalha_brasil_pages():
    base_url = "https://www.trabalhabrasil.com.br/vagas-empregos"
    output_folder = "./data/"
    sleep_mean = 2
    sleep_std = 0.5
    log_num_pages = 1
    get_pages(base_url, output_folder, sleep_mean, sleep_std, log_num_pages)    

@app.command("extract-data")
def extract_trabalha_brasil_data():
   for file in os.listdir("./data"):
        print(f"Processing file {file}")
        with open(f"./data/{file}") as f:
           page = f.read() 
           jobs = extract_page_data(page)
           print(jobs)
           print("-"*50)    