import os
import re

files_to_update = [
    "c:/Mia Analyst/analytics/views.py",
    "c:/Mia Analyst/accounts/views.py",
    "c:/Mia Analyst/management/views.py",
    "c:/Mia Analyst/blog/views.py"
]

import_statement = "from core.views import get_template_name\n"

for filepath in files_to_update:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Add import if not present
    if "from core.views import get_template_name" not in content and "get_template_name" not in content:
        # Find the last import statement or just put it at top
        content = import_statement + content

    # Use regex to find `render(request, 'string', ...)` and replace with `render(request, get_template_name(request, 'string'), ...)`
    # This matches string enclosed in single quotes or double quotes
    content = re.sub(
        r"render\(\s*request\s*,\s*(['\"][a-zA-Z0-9_\/\.]+['\"])\s*(,|\))",
        r"render(request, get_template_name(request, \1)\2",
        content
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
print("Updated view files with get_template_name wrappers.")
