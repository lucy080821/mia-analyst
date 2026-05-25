import re

def process_file(filepath, is_en):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Define the English and Vietnamese texts correctly
    chat_text_en_target = '<div class="text-sm text-gray-400 text-left px-2">Ask Mia about your data...</div>'
    
    # In VN, there's a corrupted script right now. Let's find it and replace it.
    # We can use regex to replace the entire floating chat input div content.
    # The div starts with: <div class="absolute bottom-4 left-1/2 ... flex flex-col space-y-3 z-20">
    # and ends with </div> just before `</div> <!-- Dashboard Mockup Container -->`
    
    floating_chat_pattern = re.compile(
        r'(<!-- Floating Chat Input -->\s*<div class="absolute bottom-4 left-1/2 [^"]* flex flex-col space-y-3 z-20">)(.*?)(<div class="flex items-center justify-between mt-2">)',
        re.DOTALL
    )

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

    typewriter_html = f'''
                        <div class="text-sm text-gray-600 text-left px-2 font-medium h-5 flex items-center">
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
                                let started = false;
                                
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

                                // Intersection Observer to start animation when visible
                                const observer = new IntersectionObserver((entries) => {{
                                    if (entries[0].isIntersecting && !started) {{
                                        started = true;
                                        setTimeout(type, 800);
                                    }}
                                }}, {{ threshold: 0.5 }});
                                
                                const showcaseSec = document.getElementById('showcase');
                                if (showcaseSec) {{
                                    observer.observe(showcaseSec);
                                }} else {{
                                    setTimeout(type, 1000); // fallback
                                }}
                            }});
                        </script>
                        '''

    match = floating_chat_pattern.search(content)
    if match:
        new_content = content[:match.start(2)] + typewriter_html + content[match.start(3):]
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Successfully updated {filepath}")
    else:
        print(f"Could not find floating chat section in {filepath}")

process_file('landing.html', False)
process_file('landing_en.html', True)
