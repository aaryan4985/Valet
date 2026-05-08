import json
import os

wt_settings_path = os.path.expandvars(r"%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json")

with open(wt_settings_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

default_guid = data.get("defaultProfile", "")
print("Default GUID:", default_guid)
for p in data.get("profiles", {}).get("list", []):
    if p.get("guid") == default_guid:
        print("Default Profile:", p.get("name"))
        print("Background:", p.get("backgroundImage"))
        print("Opacity:", p.get("backgroundImageOpacity"))
