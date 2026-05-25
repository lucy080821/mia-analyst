import os
import re
import json

directory = 'c:/Mia Analyst/templates'
vi_pattern = re.compile(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', re.IGNORECASE)

extracted_strings = set()

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith('_en.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extract {{ "..." }} or {{ '...' }}
                matches2 = re.findall(r'\{\{\s*[\"\']([^\"\']+)[\"\']\s*\}\}', content)
                for m in matches2:
                    if vi_pattern.search(m):
                        extracted_strings.add(m.strip())
                        
                # Extract standard text nodes: >text<
                matches1 = re.findall(r'>([^<]+)<', content)
                for m in matches1:
                    m = m.strip()
                    if vi_pattern.search(m) and '{%' not in m and '{{' not in m:
                        extracted_strings.add(m)

with open('c:/Mia Analyst/vi_strings_raw.json', 'w', encoding='utf-8') as f:
    json.dump(sorted(list(extracted_strings)), f, ensure_ascii=False, indent=4)
print(f"Extracted {len(extracted_strings)} strings.")
