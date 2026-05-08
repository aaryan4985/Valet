with open(r'c:\Users\Aaryan Pradhan\coding\valet\valet\app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the escaped quotes
content = content.replace(r'\"', '"')
# Fix the escaped backslashes (where \\\\ was meant to be \\)
content = content.replace(r'\\\\', r'\\')

with open(r'c:\Users\Aaryan Pradhan\coding\valet\valet\app.py', 'w', encoding='utf-8') as f:
    f.write(content)
