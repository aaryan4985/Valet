import os, re
p = os.path.expandvars(r'%LOCALAPPDATA%\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json')
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()
c = re.sub(r'"backgroundImage"\s*:\s*".*?"\s*,?\s*', '', c)
c = re.sub(r'"backgroundImageOpacity"\s*:\s*[0-9.]+\s*,?\s*', '', c)
with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
print('Wallpaper wiped.')
