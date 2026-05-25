import os
import shutil
import re

templates_dir = "c:/Mia Analyst/templates"

for root, dirs, files in os.walk(templates_dir):
    for file in files:
        if file.endswith(".html") and not file.endswith("_en.html"):
            base_path = os.path.join(root, file)
            en_path = os.path.join(root, file.replace(".html", "_en.html"))
            
            if not os.path.exists(en_path):
                # Copy the file
                shutil.copy2(base_path, en_path)
                
                # Replace extends and include
                with open(en_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # If the template extends something, try to make it extend the _en version
                # Usually {% extends 'base.html' %} or {% extends "management/base.html" %}
                def replace_extends(match):
                    quote = match.group(1)
                    template_name = match.group(2)
                    if not template_name.endswith("_en.html"):
                        new_template_name = template_name.replace(".html", "_en.html")
                        return f"{{% extends {quote}{new_template_name}{quote} %}}"
                    return match.group(0)
                
                content = re.sub(r'\{%\s*extends\s+([\'"])([a-zA-Z0-9_/\.-]+)\1\s*%\}', replace_extends, content)
                
                with open(en_path, "w", encoding="utf-8") as f:
                    f.write(content)
                    
                print(f"Created: {en_path}")
