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
        self.workflow_state = None
        from valet.assistant import ValetAssistant
        self.assistant = ValetAssistant()

    def action_history_up(self) -> None:
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            input_widget = self.query_one(Input)
            item = self.command_history[self.history_index]
            input_widget.value = item if isinstance(item, str) else item.get("user", "")
            input_widget.cursor_position = len(input_widget.value)

    def action_history_down(self) -> None:
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            input_widget = self.query_one(Input)
            item = self.command_history[self.history_index]
            input_widget.value = item if isinstance(item, str) else item.get("user", "")
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
            last_cmd = self.command_history[-1] if self.command_history else None
            if isinstance(last_cmd, dict):
                last_cmd = last_cmd.get("user", "")
            if not self.command_history or last_cmd != user_input:
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

        # Check if we are in workflow approval state
        if self.workflow_state is not None:
            self.handle_workflow_approval(user_input)
            return

        import shutil
        windows_builtins = {"dir", "echo", "type", "copy", "move", "ren", "md", "cd", "mkdir", "rmdir", "del", "erase", "cls", "start", "set", "call"}
        is_shell = cmd in windows_builtins or shutil.which(cmd) is not None
        if not is_shell:
            if os.path.exists(cmd) or cmd.startswith(".") or cmd.startswith("/") or cmd.startswith("\\") or ":" in cmd:
                is_shell = True
                
        if cmd == "valet":
            is_shell = False
                
        if not is_shell:
            if user_input.lower().startswith("valet ") or user_input.lower() == "valet":
                workflow_prompt = user_input[5:].strip()
                if not workflow_prompt:
                    self.log_widget.write(f"[magenta]Valet:[/] Yes? Try 'valet <prompt>' to generate a workflow.")
                    return
                self.log_widget.write(f"[dim]Analyzing workflow request with AI...[/]")
                self.generate_workflow_thread(workflow_prompt)
            else:
                self.log_widget.write(f"[dim]Asking AI Assistant...[/]")
                self.chat_with_assistant_thread(user_input)
            return

        # Pure OS Shell Execution
        self.execute_shell(user_input)

    @work(exclusive=True, thread=True)
    def generate_workflow_thread(self, prompt: str, modification: str = None) -> None:
        try:
            # We import here to avoid circular imports if any
            from valet.workflow import workflow_engine
            workflow = workflow_engine.generate_workflow(prompt, self.workflow_state, modification)
            self.workflow_state = workflow
            self.call_from_thread(self.display_workflow, workflow)
        except Exception as e:
            self.call_from_thread(self.log_widget.write, f"[red]Workflow Error:[/] {e}")
            self.workflow_state = None

    def display_workflow(self, workflow: dict) -> None:
        risk_color = "green"
        if workflow.get("risk", "low") == "medium":
            risk_color = "yellow"
        elif workflow.get("risk", "low") == "high":
            risk_color = "red"
            
        out = f"\n[bold underline]AI Workflow Plan[/]\n"
        out += f"[bold]Title:[/] {workflow.get('title', 'Unknown')}\n"
        out += f"[bold]Summary:[/] {workflow.get('summary', '')}\n"
        out += f"[bold]Risk:[/] [bold {risk_color}]{workflow.get('risk', 'low').upper()}[/]\n\n"
        
        for step in workflow.get("steps", []):
            danger = "[bold red](DANGEROUS)[/] " if step.get("dangerous") else ""
            out += f"  {step.get('id', 0)}. {danger}[cyan]{step.get('title', 'Step')}[/]\n"
            out += f"     [dim]> {step.get('command', '')}[/]\n"
            
        out += "\n[bold yellow]Do you approve this workflow? (y/n or type modification)[/]\n"
        self.log_widget.write(out)

    def handle_workflow_approval(self, user_input: str) -> None:
        inp = user_input.lower()
        if inp in ["y", "yes", "approve", "ok", "sure", "go"]:
            self.log_widget.write("[bold green]Workflow Approved. Executing...[/]")
            workflow = self.workflow_state
            self.workflow_state = None
            self.execute_workflow_thread(workflow)
        elif inp in ["n", "no", "cancel", "reject", "stop", "abort"]:
            self.log_widget.write("[bold red]Workflow Cancelled.[/]")
            self.workflow_state = None
        else:
            self.log_widget.write(f"[dim]Modifying workflow based on: '{user_input}'...[/]")
            self.generate_workflow_thread(prompt="", modification=user_input)

    @work(exclusive=True, thread=True)
    def execute_workflow_thread(self, workflow: dict) -> None:
        for step in workflow.get("steps", []):
            cmd = step.get("command", "")
            self.call_from_thread(self.log_widget.write, f"\n[bold blue]Executing Step {step.get('id')}:[/] {step.get('title')}")
            self.call_from_thread(self.log_widget.write, f"[dim]> {cmd}[/]")
            try:
                import subprocess
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.stdout:
                    self.call_from_thread(self.log_widget.write, result.stdout.strip())
                if result.stderr:
                    self.call_from_thread(self.log_widget.write, f"[red]{result.stderr.strip()}[/]")
                    
                if result.returncode != 0:
                    self.call_from_thread(self.log_widget.write, f"[bold red]Step failed with exit code {result.returncode}. Stopping workflow.[/]")
                    break
                else:
                    self.call_from_thread(self.log_widget.write, f"[bold green]Step completed.[/]")
                    
            except Exception as e:
                self.call_from_thread(self.log_widget.write, f"[bold red]Execution error:[/] {e}")
                break
        self.call_from_thread(self.log_widget.write, "\n[bold green]Workflow execution finished.[/]\n")

    @work(exclusive=True, thread=True)
    def chat_with_assistant_thread(self, prompt: str) -> None:
        try:
            response = self.assistant.process_input(prompt)
            self.call_from_thread(self.log_widget.write, f"\n[bold magenta]Valet:[/] {response}\n")
        except Exception as e:
            self.call_from_thread(self.log_widget.write, f"[red]Assistant Error:[/] {e}")

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
            
    def get_target_profile(self, data):
        # By targeting defaults, the wallpaper is guaranteed to show in any shell
        # We ensure it's safely removed on exit to not pollute other profiles permanently.
        if "profiles" not in data:
            data["profiles"] = {}
        if "defaults" not in data["profiles"]:
            data["profiles"]["defaults"] = {}
        return data["profiles"]["defaults"]
        
    def backup_and_set_wallpaper(self) -> str:
        """Modify Windows Terminal settings.json safely via json, targeting default profile."""
        import random
        import urllib.request
        import json
        try:
            wt_settings_path = os.path.expandvars(r"%LOCALAPPDATA%\\Packages\\Microsoft.WindowsTerminal_8wekyb3d8bbwe\\LocalState\\settings.json")
            if not os.path.exists(wt_settings_path):
                return ""
                
            with open(wt_settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            profile_to_mod = self.get_target_profile(data)

            bg_path = profile_to_mod.get("backgroundImage", "")
            op_val = profile_to_mod.get("backgroundImageOpacity", 1.0)

            # Do not backup if it's already a Valet wallpaper
            if "valet_wallpaper" in bg_path.lower():
                self.original_wallpaper = None
                self.original_opacity = None
            else:
                self.original_wallpaper = bg_path if bg_path else None
                self.original_opacity = op_val
                
            api_url = "https://api.github.com/repos/orangci/walls/contents/"
            import requests
            r = requests.get(api_url)
            if r.status_code == 200:
                files = [f for f in r.json() if f['name'].endswith(('.png', '.jpg', '.jpeg'))]
                if files:
                    choice = random.choice(files)
                    dl_url = choice['download_url']
                    img_path = str(config_manager.config_dir / f"valet_wallpaper_{choice['name']}").replace("\\", "/")
                    urllib.request.urlretrieve(dl_url, img_path)
                    
                    profile_to_mod["backgroundImage"] = img_path
                    profile_to_mod["backgroundImageOpacity"] = 0.4
                    
                    with open(wt_settings_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
                        
                    return f"Terminal wallpaper updated to {choice['name']}!"
            return ""
        except Exception as e:
            return f""

    def change_wallpaper(self) -> str:
        """Modify Windows Terminal settings.json safely via json."""
        import random
        import urllib.request
        import json
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
                    img_path = str(config_manager.config_dir / f"valet_wallpaper_{choice['name']}").replace("\\", "/")
                    urllib.request.urlretrieve(dl_url, img_path)
                    
                    wt_settings_path = os.path.expandvars(r"%LOCALAPPDATA%\\Packages\\Microsoft.WindowsTerminal_8wekyb3d8bbwe\\LocalState\\settings.json")
                    if os.path.exists(wt_settings_path):
                        with open(wt_settings_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                        profile_to_mod = self.get_target_profile(data)
                            
                        profile_to_mod["backgroundImage"] = img_path
                        profile_to_mod["backgroundImageOpacity"] = 0.4
                        
                        with open(wt_settings_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=4)
                            
                        return f"Terminal wallpaper updated to {choice['name']}!"
            return "Failed to fetch wallpaper list from GitHub."
        except Exception as e:
            return f"Wallpaper change error: {e}"

    def restore_wallpaper(self) -> None:
        """Restore original Windows Terminal wallpaper on exit."""
        import json
        import os
        wt_settings_path = os.path.expandvars(r"%LOCALAPPDATA%\\Packages\\Microsoft.WindowsTerminal_8wekyb3d8bbwe\\LocalState\\settings.json")
        if not os.path.exists(wt_settings_path):
            return
            
        try:
            with open(wt_settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            profile_to_mod = self.get_target_profile(data)
                
            if self.original_wallpaper is not None:
                profile_to_mod["backgroundImage"] = self.original_wallpaper
                profile_to_mod["backgroundImageOpacity"] = float(self.original_opacity) if self.original_opacity is not None else 1.0
            else:
                profile_to_mod.pop("backgroundImage", None)
                profile_to_mod.pop("backgroundImageOpacity", None)
                
            # Also clean up defaults if we accidentally polluted it previously
            defaults = data.get("profiles", {}).get("defaults", {})
            if isinstance(defaults, dict):
                bg = defaults.get("backgroundImage", "")
                if "valet_wallpaper" in bg.lower() or "temp" in bg.lower():
                    defaults.pop("backgroundImage", None)
                    defaults.pop("backgroundImageOpacity", None)
                    
            # And clean up specific profile if we touched it in older versions
            default_guid = data.get("defaultProfile", "")
            for p in data.get("profiles", {}).get("list", []):
                if p.get("guid") == default_guid:
                    bg = p.get("backgroundImage", "")
                    if "valet_wallpaper" in bg.lower() or "temp" in bg.lower():
                        p.pop("backgroundImage", None)
                        p.pop("backgroundImageOpacity", None)
                
            with open(wt_settings_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass
