import json
import os

wt_settings_path = os.path.expandvars(r"%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json")

with open(wt_settings_path, 'r', encoding='utf-8') as f:
    try:
        data = json.load(f)
    except json.JSONDecodeError:
        # If it's invalid due to our regex bug, let's fix it by regex
        pass

# Wait, if our regex bug made it invalid, json.load will fail!
