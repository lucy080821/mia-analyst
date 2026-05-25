import re

def process_file(filepath, is_en):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Extract sections
    showcase_pattern = re.compile(r'(<!-- Product Showcase Section -->\s*<section.*?(?:\n.*?)*?)(?=\n\s*<!-- About Section -->)', re.DOTALL)
    about_pattern = re.compile(r'(<!-- About Section -->\s*<section.*?(?:\n.*?)*?)(?=\n\s*<!-- Services Section -->)', re.DOTALL)

    showcase_match = showcase_pattern.search(content)
    about_match = about_pattern.search(content)

    if not showcase_match or not about_match:
        print(f"Could not find sections in {filepath}")
        return

    showcase_html = showcase_match.group(1)
    about_html = about_match.group(1)

    # 2. Add typewriter effect to showcase
    chat_text_vn = '<div class="text-sm text-gray-400 text-left px-2">Hỏi Mia bất cứ điều gì về dữ liệu...</div>'
    chat_text_en = '<div class="text-sm text-gray-400 text-left px-2">Ask Mia anything about your data...</div>'
    
    chat_text = chat_text_en if is_en else chat_text_vn
    
    texts_vn = [
        "Phân tích doanh thu quý này theo từng khu vực?",
        "Tại sao chi phí marketing tháng 5 lại tăng đột biến?",
        "Dự báo lợi nhuận tháng tới dựa trên dữ liệu hiện tại."
    ]
    texts_en = [
        "Analyze this quarter's revenue by region?",
        "Why did marketing costs spike in May?",
        "Forecast next month's profit based on current data."
    ]
    
    texts_to_use = texts_en if is_en else texts_vn
    texts_js = ", ".join(f'"{t}"' for t in texts_to_use)

    typewriter_html = f'''<div class="text-sm text-gray-600 text-left px-2 font-medium h-5 flex items-center">
                            <span id="chat-input-typewriter" class="text-gray-800"></span><span class="animate-pulse border-r-2 border-primary/70 inline-block h-4 ml-[2px]"></span>
                        </div>
                        <script>
                            document.addEventListener('DOMContentLoaded', () => {{
                                const texts = [{texts_js}];
                                const el = document.getElementById('chat-input-typewriter');
                                if(!el) return;
                                let textIdx = 0;
                                let charIdx = 0;
                                let isDeleting = false;
                                
                                function type() {{
                                    const currentText = texts[textIdx];
                                    if (!isDeleting) {{
                                        el.textContent = currentText.substring(0, charIdx + 1);
                                        charIdx++;
                                        if (charIdx === currentText.length) {{
                                            isDeleting = true;
                                            setTimeout(type, 2500);
                                            return;
                                        }}
                                    }} else {{
                                        el.textContent = currentText.substring(0, charIdx - 1);
                                        charIdx--;
                                        if (charIdx === 0) {{
                                            isDeleting = false;
                                            textIdx = (textIdx + 1) % texts.length;
                                        }}
                                    }}
                                    setTimeout(type, isDeleting ? 20 : 60);
                                }}
                                setTimeout(type, 1000);
                            }});
                        </script>'''

    new_showcase_html = showcase_html.replace(chat_text, typewriter_html)

    # 3. Reorder
    # We replace both with About + Showcase
    content = content.replace(showcase_html, '')
    content = content.replace(about_html, about_html + "\n" + new_showcase_html)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Successfully updated {filepath}")

process_file('landing.html', False)
process_file('landing_en.html', True)
