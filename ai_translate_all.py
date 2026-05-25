import os
import time
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor

# Configure GenAI
genai.configure(api_key='AIzaSyCnjMty4wBesIFNSy5Wu9z1PeUFNykpLcI')
model = genai.GenerativeModel('gemini-2.5-flash')

directory = "c:/Mia Analyst/templates"
files_to_translate = []

# Collect all _en.html files
for root, dirs, files in os.walk(directory):
    for str_file in files:
        if str_file.endswith("_en.html"):
            files_to_translate.append(os.path.join(root, str_file))

def translate_file(path):
    print(f"Translating {path}...")
    try:
        with open(path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Simple check if there's any Vietnamese. A lazy heuristic but let's just translate it.
        # It's better to just prompt Gemini.
        prompt = """You are an expert translator and developer.
I will give you a Django HTML template containing Vietnamese strings.
Translate ALL Vietnamese UI text and hardcoded strings into professional Business English.
DO NOT change any HTML tags, CSS classes, `{% ... %}` django template tags, or `{{ ... }}` variables.
If the text contains `{{ "Vietnamese" }}` you should translate it to `{{ "English" }}`.
Do NOT wrap your response in ```html, return ONLY the raw HTML string.
"""
        
        response = model.generate_content(
            [prompt, html_content], 
            generation_config={"temperature": 0.0}
        )
        
        translated_html = response.text
        if translated_html.startswith("```html"):
            translated_html = translated_html[7:]
        if translated_html.endswith("```"):
            translated_html = translated_html[:-3]
        
        translated_html = translated_html.strip()

        with open(path, "w", encoding="utf-8") as f:
            f.write(translated_html)
            
        print(f"SUCCESS: {path}")
    except Exception as e:
        print(f"FAILED: {path}: {e}")

# Process with 5 workers
start_time = time.time()
with ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(translate_file, files_to_translate)
end_time = time.time()
print(f"All translations completed in {end_time - start_time:.2f} seconds.")
