import os, django, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from analytics.export_utils import FONT_PATH
css_font_path = "file:///" + FONT_PATH.replace('\\', '/')
html_content = f"""
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @font-face {{
            font-family: Arial;
            src: url("{css_font_path}");
        }}
        body {{ font-family: Arial, sans-serif; }}
    </style>
</head>
<body>
    <h1>Test</h1>
</body>
</html>
"""
import io
from xhtml2pdf import pisa
buffer = io.BytesIO()
pisa_status = pisa.CreatePDF(html_content, dest=buffer, encoding='utf-8')
if pisa_status.err:
    print("Pisa error")
else:
    print(f"Success. Buffer size: {len(buffer.getvalue())}")

