from textual.app import App
from textual.widgets import Static

class TestApp(App):
    CSS = """
    Screen {
        background: transparent;
    }
    """
    def compose(self):
        yield Static("Hello world. If you see your wallpaper, Textual transparency works.")

if __name__ == "__main__":
    app = TestApp()
    app.run()
