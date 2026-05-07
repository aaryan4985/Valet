import sys
from valet.app import ValetApp

def cli():
    """Entry point for the Valet terminal."""
    app = ValetApp()
    app.run()

if __name__ == "__main__":
    cli()
