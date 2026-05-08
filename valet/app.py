import time
import os
import subprocess
import re
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll, Container
from textual.widgets import Input, Static, RichLog
from textual.binding import Binding
from textual import work

from textual.containers import Horizontal, Container
from textual.widgets import Input, Static, RichLog
from textual.binding import Binding
from textual import work
import atexit

from valet.config import config_manager
from valet.monitor import get_system_stats

class ValetApp(App):
    """The main TUI Application for Valet."""
    
    CSS_PATH = "ui/styles.css"
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear_chat", "Clear", show=True),
        Binding("up", "history_up", "Previous Command", show=False),
        Binding("down", "history_down", "Next Command", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.user_name = config_manager.config.get("user_name", "Aaryan").lower()
        self.prompt_prefix = ""
        self.log_widget = RichLog(id="terminal-log", markup=True, wrap=True)
        self.original_wallpaper = None
        self.original_opacity = None
        self.command_history = config_manager.history
        self.history_index = len(self.command_history)

    def action_history_up(self) -> None:
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            input_widget = self.query_one(Input)
            input_widget.value = self.command_history[self.history_index]
            input_widget.cursor_position = len(input_widget.value)

    def action_history_down(self) -> None:
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            input_widget = self.query_one(Input)
            input_widget.value = self.command_history[self.history_index]
            input_widget.cursor_position = len(input_widget.value)
        elif self.history_index == len(self.command_history) - 1:
            self.history_index = len(self.command_history)
            input_widget = self.query_one(Input)
            input_widget.value = ""

    def update_prompt(self) -> None:
        cwd = os.getcwd()
        self.prompt_prefix = f"[bold green]{self.user_name}@valet[/] [bold blue]{cwd}[/] $ "
        try:
            self.query_one("#prompt").update(self.prompt_prefix)
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        with Container(id="main-area"):
            yield self.log_widget
            with Horizontal(id="input-container"):
                yield Static(self.prompt_prefix, id="prompt")
                yield Input(id="command-input")

    def on_mount(self) -> None:
        self.update_prompt()
        self.query_one(Input).focus()
        
        # Backup and set wallpaper
        atexit.register(self.restore_wallpaper)
        self.backup_and_set_wallpaper()
        
        # Clean terminal start
        self.run_startup_sequence()

    def action_clear_chat(self) -> None:
        self.log_widget.clear()
        
    def on_unmount(self) -> None:
        self.restore_wallpaper()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.value.strip()
        if not user_input:
            return
            
        input_widget = self.query_one(Input)
        input_widget.value = ""
        
        if user_input:
            if not self.command_history or self.command_history[-1] != user_input:
                self.command_history.append(user_input)
                config_manager.save_history()
            self.history_index = len(self.command_history)
        
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
        
        # Custom Valet Commands
        if cmd == "clear":
            self.action_clear_chat()
            return
        elif cmd in ["exit", "quit"]:
            self.exit()
            return
        elif cmd == "theme" and len(parts) > 1:
            theme_name = parts[1]
            self.log_widget.write(f"Switched to theme '{theme_name}'.")
            self.app.dark = (theme_name != "light")
            self.change_wallpaper_thread()
            return
        elif cmd == "wallpaper":
            self.log_widget.write("Fetching new wallpaper from orangci/walls...")
            self.change_wallpaper_thread()
            return
        elif cmd == "cd":
            try:
                from pathlib import Path
                target = " ".join(parts[1:]) if len(parts) > 1 else str(Path.home())
                os.chdir(target)
                self.update_prompt()
            except Exception as e:
                self.log_widget.write(f"[red]cd error:[/] {e}")
            return

        # Pure OS Shell Execution
        self.execute_shell(user_input)

    @work(exclusive=True, thread=True)
    def execute_shell(self, user_input: str) -> None:
        """Run as a normal shell command."""
        try:
            result = subprocess.run(user_input, shell=True, capture_output=True, text=True)
            err = result.stderr.strip()
            
            if result.stdout:
                self.call_from_thread(self.log_widget.write, result.stdout.strip())
            if err:
                self.call_from_thread(self.log_widget.write, f"[red]{err}[/]")
                
        except Exception as e:
            self.call_from_thread(self.log_widget.write, f"[red]Execution failed:[/] {e}")
            
    @work(exclusive=True, thread=True)
    def change_wallpaper_thread(self):
        res = self.change_wallpaper()
        self.call_from_thread(self.log_widget.write, res)
        
    @work(exclusive=True, thread=True)
    def run_startup_sequence(self):
        ascii_art = [
            " __      __   _      _   ",
            " \\ \\    / /  | |    | |  ",
            "  \\ \\  / /_ _| | ___| |_ ",
            "   \\ \\/ / _` | |/ _ \\ __|",
            "    \\  / (_| | |  __/ |_ ",
            "     \\/ \\__,_|_|\\___|\\__|",
            "                         "
        ]
        # Animated ASCII
        for line in ascii_art:
            self.call_from_thread(self.log_widget.write, f"[bold cyan]{line}[/]")
            time.sleep(0.05)
            
        time.sleep(0.1)
        
        self.call_from_thread(self.log_widget.write, "[dim]Gathering system telemetry...[/]")
        stats = get_system_stats()
        
        # GitHub activity (mocked or fetched)
        import requests
        github_activity = "No recent activity"
        try:
            github_username = config_manager.config.get("github_username", "aaryan4985")
            r = requests.get(f"https://api.github.com/users/{github_username}/events/public", timeout=2)
            if r.status_code == 200:
                events = r.json()
                if events:
                    github_activity = f"Last action: {events[0]['type']} at {events[0]['repo']['name']}"
        except:
            pass

        # Productivity Summary
        todos_count = len(config_manager.todos)
        productivity = f"You have {todos_count} pending tasks." if todos_count > 0 else "All caught up on tasks!"

        # AI Greeting
        greeting = f"Welcome back, {self.user_name.capitalize()}."
        try:
            prompt = f"Write a very short 1 sentence greeting for a developer named {self.user_name}. Keep it cool and terminal-like."
            from groq import Groq
            client = Groq(api_key=config_manager.config["groq_api_key"])
            response = client.chat.completions.create(
                model=config_manager.config["llm_model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=40
            )
            greeting = response.choices[0].message.content.strip()
        except:
            pass

        startup_text = f"""
[bold yellow]System Status:[/] CPU: {stats['cpu_percent']}% | RAM: {stats['ram_used']}/{stats['ram_total']}
[bold green]Uptime:[/] {stats['uptime']}
[bold blue]Weather:[/] {stats['weather']}
[bold magenta]GitHub:[/] {github_activity}
[bold red]Productivity:[/] {productivity}

[bold bright_white]AI:[/] {greeting}
"""
        self.call_from_thread(self.log_widget.write, "")
        for line in startup_text.strip().split('\n'):
            self.call_from_thread(self.log_widget.write, line)
            time.sleep(0.05)
            
        self.call_from_thread(self.log_widget.write, "\n[dim]Ready.[/]\n")
            
    def backup_and_set_wallpaper(self) -> str:
        """Modify Windows Terminal settings.json safely via regex, backing up the original."""
        import random
        import urllib.request
        import json
        try:
            wt_settings_path = os.path.expandvars(r"%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json")
            if os.path.exists(wt_settings_path):
                with open(wt_settings_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Backup using simple regex extraction
                bg_match = re.search(r'"backgroundImage"\s*:\s*"([^"]+)"', content)
                op_match = re.search(r'"backgroundImageOpacity"\s*:\s*([0-9.]+)', content)
                
                bg_path = bg_match.group(1) if bg_match else ""
                # If the current wallpaper is a Valet temporary file, do NOT back it up!
                if "Temp" in bg_path or "temp" in bg_path.lower() or "voyager" in bg_path:
                    self.original_wallpaper = None
                    self.original_opacity = None
                else:
                    self.original_wallpaper = bg_path if bg_path else None
                    self.original_opacity = op_match.group(1) if op_match else None
                
            api_url = "https://api.github.com/repos/orangci/walls/contents/"
            import requests
            r = requests.get(api_url)
            if r.status_code == 200:
                files = [f for f in r.json() if f['name'].endswith(('.png', '.jpg', '.jpeg'))]
                if files:
                    choice = random.choice(files)
                    dl_url = choice['download_url']
                    img_path = os.path.join(os.environ['TEMP'], choice['name'])
                    img_path = img_path.replace("\\", "/")
                    urllib.request.urlretrieve(dl_url, img_path)
                    
                    if os.path.exists(wt_settings_path):
                        # Remove existing
                        content = re.sub(r'"backgroundImage"\s*:\s*".*?"\s*,?\s*', '', content)
                        content = re.sub(r'"backgroundImageOpacity"\s*:\s*[0-9.]+\s*,?\s*', '', content)
                        
                        # Inject new
                        injection = f'"defaults": {{\n            "backgroundImage": "{img_path}",\n            "backgroundImageOpacity": 1.0,\n'
                        new_content = re.sub(r'"defaults"\s*:\s*\{', injection, content, count=1)
                        
                        with open(wt_settings_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                            
                        return f"Terminal wallpaper updated to {choice['name']}!"
            return ""
        except Exception as e:
            return ""

    def change_wallpaper(self) -> str:
        """Modify Windows Terminal settings.json safely via regex injection."""
        import random
        import urllib.request
        import json
        import re
        import os
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
                    img_path = img_path.replace("\\", "/")
                    urllib.request.urlretrieve(dl_url, img_path)
                    
                    wt_settings_path = os.path.expandvars(r"%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json")
                    if os.path.exists(wt_settings_path):
                        with open(wt_settings_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        content = re.sub(r'"backgroundImage"\s*:\s*".*?"\s*,?\s*', '', content)
                        content = re.sub(r'"backgroundImageOpacity"\s*:\s*[0-9.]+\s*,?\s*', '', content)
                        
                        injection = f'"defaults": {{\n            "backgroundImage": "{img_path}",\n            "backgroundImageOpacity": 1.0,\n'
                        new_content = re.sub(r'"defaults"\s*:\s*\{', injection, content, count=1)
                        
                        with open(wt_settings_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                            
                        return f"Terminal wallpaper updated to {choice['name']}!"
            return "Failed to fetch wallpaper list from GitHub."
        except Exception as e:
            return f"Wallpaper change error: {e}"

    def restore_wallpaper(self) -> None:
        """Restore original Windows Terminal wallpaper on exit."""
        wt_settings_path = os.path.expandvars(r"%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json")
        if not os.path.exists(wt_settings_path):
            return
            
        try:
            with open(wt_settings_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Remove current
            content = re.sub(r'"backgroundImage"\s*:\s*".*?"\s*,?\s*', '', content)
            content = re.sub(r'"backgroundImageOpacity"\s*:\s*[0-9.]+\s*,?\s*', '', content)
            
            # Inject original if it existed
            if self.original_wallpaper is not None:
                opacity = self.original_opacity if self.original_opacity is not None else "1.0"
                injection = f'"defaults": {{\n            "backgroundImage": "{self.original_wallpaper}",\n            "backgroundImageOpacity": {opacity},\n'
                content = re.sub(r'"defaults"\s*:\s*\{', injection, content, count=1)
                
            with open(wt_settings_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception:
            pass
