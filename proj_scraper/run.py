import typer
from trabalha_brasil import cli_commands

"""
This script serves as the entry point for the 'proj_scraper' project. It uses the Typer library to create a command-line interface (CLI) application.

Modules:
    typer: A library for creating CLI applications.
    cli_commands: A module containing CLI commands for the 'trabalha_brasil' application.

Functions:
    main: The main function that runs the Typer application.

Usage:
    Run this script directly to start the CLI application.
"""


app = typer.Typer() 
app.add_typer(cli_commands.app, name="trabalha-brasil")



if __name__ == "__main__":
    app()
