import typer
from trabalha_brasil import cli_commands


app = typer.Typer() 
app.add_typer(cli_commands.app, name="trabalha-brasil")




if __name__ == "__main__":
    app()
