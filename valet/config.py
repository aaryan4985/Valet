import os
import json
from pathlib import Path
from typing import Dict, Any, List

class ConfigManager:
    """Manages persistent configuration, memory, and state for Valet."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "valet"
        self.config_file = self.config_dir / "config.json"
        self.history_file = self.config_dir / "history.json"
        self.todos_file = self.config_dir / "todos.json"
        self.plugins_dir = self.config_dir / "plugins"
        
        self.ensure_setup()
        self.config = self.load_json(self.config_file, self.default_config())
        self.todos = self.load_json(self.todos_file, [])
        self.history = self.load_json(self.history_file, [])

        # Update default API key if not set
        if "groq_api_key" not in self.config or not self.config["groq_api_key"]:
            self.config["groq_api_key"] = os.environ.get("GROQ_API_KEY", "")
            self.save_config()
            
        # Migrate old config model to a valid Groq model
        current_model = self.config.get("llm_model")
        if current_model in ["mistral", "llama3-70b-8192"]:
            self.config["llm_model"] = "llama-3.3-70b-versatile"
            self.save_config()

    def default_config(self) -> Dict[str, Any]:
        return {
            "theme": "dark",
            "assistant_name": "Valet",
            "user_name": "Aaryan",
            "prompt_style": "valet ❯ ",
            "llm_provider": "groq",
            "llm_model": "llama-3.3-70b-versatile",
            "groq_api_key": os.environ.get("GROQ_API_KEY", ""),
            "wallpaper_set": False,
            "aliases": {
                "l": "ls -la",
                "gs": "git status"
            },
            "workflows": {
                "devstart": [
                    "code .",
                    "echo 'Starting dev environment...'"
                ]
            }
        }

    def ensure_setup(self):
        """Ensure config directories and files exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        for path, default_data in [
            (self.config_file, self.default_config()),
            (self.history_file, []),
            (self.todos_file, [])
        ]:
            if not path.exists():
                self.save_json(path, default_data)

    def load_json(self, path: Path, default: Any) -> Any:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def save_json(self, path: Path, data: Any):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def save_config(self):
        self.save_json(self.config_file, self.config)
        
    def save_todos(self):
        self.save_json(self.todos_file, self.todos)
        
    def save_history(self):
        self.save_json(self.history_file, self.history)

config_manager = ConfigManager()
