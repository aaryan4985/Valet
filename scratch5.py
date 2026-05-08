import os
import psutil
import json

def get_current_profile(data):
    # Try WT_PROFILE_ID
    wt_id = os.environ.get("WT_PROFILE_ID")
    if wt_id:
        for p in data.get("profiles", {}).get("list", []):
            if p.get("guid") == wt_id:
                return p
                
    # Fallback: check parent process
    try:
        parent = psutil.Process(os.getpid()).parent()
        while parent:
            name = parent.name().lower()
            if "cmd" in name:
                # Find CMD profile
                for p in data.get("profiles", {}).get("list", []):
                    if "cmd.exe" in p.get("commandline", "").lower() or p.get("name") == "Command Prompt":
                        return p
            elif "powershell" in name or "pwsh" in name:
                # Find PowerShell profile
                for p in data.get("profiles", {}).get("list", []):
                    if "powershell" in p.get("commandline", "").lower() or "pwsh" in p.get("commandline", "").lower():
                        return p
            parent = parent.parent()
    except Exception:
        pass
        
    # Final fallback
    default_guid = data.get("defaultProfile", "")
    for p in data.get("profiles", {}).get("list", []):
        if p.get("guid") == default_guid:
            return p
            
    return data.get("profiles", {}).get("defaults", {})

wt_settings_path = os.path.expandvars(r"%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json")
with open(wt_settings_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
    
profile = get_current_profile(data)
print("Detected Profile:", profile.get("name"))
