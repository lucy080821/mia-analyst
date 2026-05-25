import os
import shutil

# Templates to duplicate
templates_to_duplicate = [
    "c:/Mia Analyst/templates/base.html",
    "c:/Mia Analyst/templates/accounts/login.html",
    "c:/Mia Analyst/templates/accounts/register.html",
    "c:/Mia Analyst/templates/blog/post_list.html",
    "c:/Mia Analyst/templates/blog/post_detail.html",
    "c:/Mia Analyst/templates/analytics/dashboard.html",
    "c:/Mia Analyst/templates/analytics/dataset_detail.html",
    "c:/Mia Analyst/templates/analytics/report_detail.html",
]

for src in templates_to_duplicate:
    dst = src.replace(".html", "_en.html")
    try:
        shutil.copy2(src, dst)
        
        # Read the destination and replace {% extends 'base.html' %} with {% extends 'base_en.html' %}
        with open(dst, "r", encoding="utf-8") as f:
            content = f.read()
            
        content = content.replace("{% extends 'base.html' %}", "{% extends 'base_en.html' %}")
        content = content.replace('{% extends "base.html" %}', '{% extends "base_en.html" %}')
        
        with open(dst, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"Duplicated {src} to {dst}")
    except Exception as e:
        print(f"Error duplicating {src}: {e}")
