import os
import json
import random
import urllib.request
import requests

def test_wallpaper():
    wt_settings_path = os.path.expandvars(r"%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json")
    print(f"Path exists: {os.path.exists(wt_settings_path)}")
    if not os.path.exists(wt_settings_path):
        return

    with open(wt_settings_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    default_guid = data.get("defaultProfile", "")
    print(f"Default GUID: {default_guid}")
    
    profile_to_mod = None
    if isinstance(data.get("profiles"), dict) and "list" in data["profiles"]:
        for p in data["profiles"]["list"]:
            if p.get("guid") == default_guid:
                profile_to_mod = p
                print(f"Found profile matching GUID: {p.get('name')}")
                break

    if not profile_to_mod:
        profile_to_mod = data.get("profiles", {}).get("defaults", {})
        print("Using defaults")

    api_url = "https://api.github.com/repos/orangci/walls/contents/"
    r = requests.get(api_url)
    print(f"API Status: {r.status_code}")
    if r.status_code == 200:
        files = [f for f in r.json() if f['name'].endswith(('.png', '.jpg', '.jpeg'))]
        if files:
            choice = random.choice(files)
            dl_url = choice['download_url']
            img_path = os.path.join(os.environ['TEMP'], choice['name']).replace("\\", "/")
            print(f"Downloading to: {img_path}")
            urllib.request.urlretrieve(dl_url, img_path)

            profile_to_mod["backgroundImage"] = img_path
            profile_to_mod["backgroundImageOpacity"] = 1.0

            with open(wt_settings_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            print(f"Updated successfully. Check terminal settings!")
        else:
            print("No image files found.")

test_wallpaper()
