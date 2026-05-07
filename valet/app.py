import time
import os
import subprocess
import re
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll, Container
from textual.widgets import Input, Static, RichLog
from textual.binding import Binding
from textual import work

from valet.assistant import ValetAssistant
from valet.config import config_manager
from valet.commands import handle_git, handle_todo
from valet.monitor import get_system_stats

class ValetApp(App):
    """The main TUI Application for Valet."""
    
    CSS_PATH = "ui/styles.css"
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear_chat", "Clear", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.assistant = ValetAssistant()
        self.user_name = config_manager.config.get("user_name", "Aaryan").lower()
        self.prompt_prefix = f"[bold green]{self.user_name}@valet[/] [bold blue]~[/] $ "
        self.log_widget = RichLog(id="terminal-log", markup=True, wrap=True)

    def compose(self) -> ComposeResult:
        with Container(id="main-area"):
            yield self.log_widget
            with Horizontal(id="input-container"):
                yield Static(self.prompt_prefix, id="prompt")
                yield Input(id="command-input")

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        
        # Check if wallpaper is set, if not, do it in background
        if not config_manager.config.get("wallpaper_set"):
            self.change_wallpaper(silent=True)
            config_manager.config["wallpaper_set"] = True
            config_manager.save_config()

        self.generate_startup()

    @work(exclusive=True, thread=True)
    def generate_startup(self) -> None:
        """Fetch the smart startup sequence in background."""
        stats = get_system_stats()
        
        logo = (
            "[cyan]"
            "      /\\      \n"
            "     /  \\     \n"
            "    /____\\    \n"
            "   /      \\   \n"
            "  /        \\  \n"
            "[/cyan]"
        )
        
        neofetch = (
            f"{logo}\n"
            f"[bold green]{self.user_name}@valet[/]\n"
            f"-------------------\n"
            f"[bold cyan]OS[/]: Arch Linux (Simulated)\n"
            f"[bold cyan]Uptime[/]: {stats['uptime']}\n"
            f"[bold cyan]CPU[/]: {stats['cpu_percent']}%\n"
            f"[bold cyan]RAM[/]: {stats['ram_used']} / {stats['ram_total']}\n"
            f"[bold cyan]Disk[/]: {stats['disk_free']} Free\n"
            f"[bold cyan]Weather[/]: {stats['weather']}\n"
        )
        
        greeting = self.assistant.generate_startup_greeting(stats)
        
        self.call_from_thread(self.show_startup_greeting, neofetch, greeting)

    def show_startup_greeting(self, neofetch: str, greeting: str) -> None:
        self.log_widget.write(neofetch)
        self.log_widget.write(f"\n[italic]{greeting}[/italic]\n")

    def action_clear_chat(self) -> None:
        self.log_widget.clear()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value.strip()
        if not user_input:
            return
            
        input_widget = self.query_one(Input)
        input_widget.value = ""
        
        # Write user command to log
        self.log_widget.write(f"{self.prompt_prefix}{user_input}")
        
        parts = user_input.split()
        cmd = parts[0].lower()
        
        # Check aliases
        aliases = config_manager.config.get("aliases", {})
        if cmd in aliases:
            resolved = aliases[cmd]
            try:
                out = subprocess.check_output(resolved, shell=True, text=True)
                self.log_widget.write(out)
            except Exception as e:
                self.log_widget.write(f"[red]Alias failed:[/] {str(e)}")
            return

        # Check workflows
        workflows = config_manager.config.get("workflows", {})
        if cmd in workflows:
            for step in workflows[cmd]:
                try:
                    subprocess.Popen(step, shell=True)
                    self.log_widget.write(f"[dim]Started:[/] {step}")
                except Exception as e:
                    self.log_widget.write(f"[red]Workflow step failed:[/] {str(e)}")
            return
        
        # Native commands
        response = ""
        if cmd == "clear":
            self.action_clear_chat()
            return
        elif cmd in ["exit", "quit"]:
            self.exit()
            return
        elif cmd == "git":
            response = handle_git()
        elif cmd == "todo":
            action = parts[1] if len(parts) > 1 else "list"
            item = " ".join(parts[2:]) if len(parts) > 2 else ""
            response = handle_todo(action, item)
        elif cmd == "status":
            try:
                stats = get_system_stats()
                response = f"CPU: {stats['cpu_percent']}% | RAM: {stats['ram_percent']}%\nUptime: {stats['uptime']}\nWeather: {stats['weather']}"
            except Exception:
                response = "Unable to fetch system status."
        elif cmd == "theme" and len(parts) > 1:
            theme_name = parts[1]
            response = f"Switched to theme '{theme_name}'."
            # We can also change wallpaper here if we want themed wallpapers
            self.app.dark = (theme_name != "light")
            self.change_wallpaper_thread()
        elif cmd == "wallpaper":
            self.log_widget.write("Fetching new wallpaper from orangci/walls...")
            self.change_wallpaper_thread()
            return
        else:
            self.process_ai(user_input)
            return
            
        if response:
            self.log_widget.write(response)
            
    @work(exclusive=True, thread=True)
    def change_wallpaper_thread(self):
        res = self.change_wallpaper(silent=False)
        self.call_from_thread(self.log_widget.write, res)

    @work(exclusive=True, thread=True)
    def process_ai(self, user_input: str) -> None:
        """Process AI requests without blocking UI."""
        response = self.assistant.process_input(user_input)
        self.call_from_thread(self.show_ai_response, response)

    def show_ai_response(self, response: str) -> None:
        self.log_widget.write(response)

    def change_wallpaper(self, silent=False) -> str:
        """Modify Windows Terminal settings.json safely via regex injection."""
        import random
        import urllib.request
        try:
            api_url = "https://api.github.com/repos/orangci/walls/contents/"
            import requests
            r = requests.get(api_url)
            if r.status_code == 200:
                files = [f for f in r.json() if f['name'].endswith(('.png', '.jpg', '.jpeg'))]
                if files:
                    choice = random.choice(files)
                    dl_url = choice['download_url']
                    img_path = os.path.join(os.environ['TEMP'], choice['name'])
                    img_path = img_path.replace("\\", "/") # Windows Terminal prefers forward slashes
                    urllib.request.urlretrieve(dl_url, img_path)
                    
                    wt_settings_path = os.path.expandvars(r"%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json")
                    if os.path.exists(wt_settings_path):
                        with open(wt_settings_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Remove existing backgroundImage and opacity from the file to avoid duplicates
                        content = re.sub(r'"backgroundImage"\s*:\s*".*?"\s*,?\s*', '', content)
                        content = re.sub(r'"backgroundImageOpacity"\s*:\s*[0-9.]+\s*,?\s*', '', content)
                        
                        # Inject directly into defaults
                        injection = f'"defaults": {{\n            "backgroundImage": "{img_path}",\n            "backgroundImageOpacity": 1.0,\n'
                        new_content = re.sub(r'"defaults"\s*:\s*\{', injection, content, count=1)
                        
                        with open(wt_settings_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                            
                        return f"Terminal wallpaper updated to {choice['name']}!" if not silent else ""
                    return "Error: Windows Terminal settings.json not found." if not silent else ""
            return "Failed to fetch wallpaper list from GitHub." if not silent else ""
        except Exception as e:
            return f"Wallpaper change error: {e}" if not silent else ""
