import json
import os

wt_settings_path = os.path.expandvars(r"%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json")
with open(wt_settings_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for p in data.get("profiles", {}).get("list", []):
    if p.get("name") == "Command Prompt":
        print("CMD Profile:")
        print("Background:", p.get("backgroundImage"))
        print("Opacity:", p.get("backgroundImageOpacity"))
