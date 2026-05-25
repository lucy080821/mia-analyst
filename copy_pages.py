import os
import shutil
import re

files_to_copy = [
    ("c:/Mia Analyst/templates/pages/features.html", "c:/Mia Analyst/templates/pages/features_en.html"),
    ("c:/Mia Analyst/templates/pages/roadmap.html", "c:/Mia Analyst/templates/pages/roadmap_en.html"),
    ("c:/Mia Analyst/templates/pages/docs.html", "c:/Mia Analyst/templates/pages/docs_en.html"),
    ("c:/Mia Analyst/templates/pages/privacy.html", "c:/Mia Analyst/templates/pages/privacy_en.html"),
    ("c:/Mia Analyst/templates/pages/terms.html", "c:/Mia Analyst/templates/pages/terms_en.html"),
]

translations = {
    r'\{\% extends \'base.html\' \%\}': '{% extends \'base_en.html\' %}',
    r'Tính năng chính': 'Features',
    r'Lộ trình phát triển': 'Roadmap',
    r'Tài liệu hướng dẫn': 'Documentation',
    r'Chính sách bảo mật': 'Privacy Policy',
    r'Điều khoản dịch vụ': 'Terms of Service',
    # Since these are long text contents, we just provide basics.
    # The user wanted a demo of landing page, but these will be structural translated for now.
}

for src, dst in files_to_copy:
    try:
        shutil.copy2(src, dst)
        with open(dst, 'r', encoding='utf-8') as f:
            content = f.read()
        for vi, en in translations.items():
            content = re.sub(vi, en, content)
        with open(dst, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Copied and updated {dst}")
    except Exception as e:
        print(f"Failed {src}: {e}")
