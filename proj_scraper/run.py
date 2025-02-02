import typer
from trabalha_brasil.get_pages import get_pages

app = typer.Typer()


@app.command()
def get_trabalha_brasil_pages():
    base_url = "https://www.trabalhabrasil.com.br/vagas-empregos"
    output_folder = "./data"
    sleep_mean = 2
    sleep_std = 0.5
    get_pages(base_url, output_folder, sleep_mean, sleep_std)    

@app.command("extract")
def extract_trabalha_brasil_data():
    print("Extracting data from Trabalha Brasil")



def main(name: str):
    print(f"Hello, {name}!")


if __name__ == "__main__":
    typer.run(main)
