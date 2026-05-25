def fix_dashboard(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Old string 1
    old1 = """chipsHtml = data.suggestions.map(function(q) {
                    const safeQ = q.replace(/"/g, '&quot;');
                    return `<button type="button" data-question="${safeQ}" onclick="window.submitSuggestedQuestion(this)" class="inline-block bg-white text-primary border border-primary/20 hover:bg-primary hover:text-white mt-2 mr-2 mb-1 px-3 py-1.5 rounded-full text-[11px] font-bold shadow-sm transition-all text-left leading-tight break-words max-w-full"><span class="mr-1 opacity-70">✨</span>${safeQ}</button>`;
                }).join('');"""
                
    new1 = """chipsHtml = data.suggestions.map(function(q) {
                    const safeQ = q.replace(/"/g, '&quot;');
                    return `<button type="button" data-question="${safeQ}" onclick="window.submitSuggestedQuestion(this)" class="marquee-chip"><span class="marquee-icon">✨</span><span class="text-left">${safeQ}</span></button>`;
                }).join('');
                if (chipsHtml) {
                    chipsHtml = `<div class="marquee-container mt-4"><div class="marquee-content">${chipsHtml}${chipsHtml}</div></div>`;
                }"""
                
    # Old string 2
    old2 = """${chipsHtml ? `<div class="mt-3 flex flex-wrap">${chipsHtml}</div>` : ''}"""
    new2 = """${chipsHtml}"""

    # Old string 3
    old3 = """let chipsHtml = data.suggested_questions.map(function(q) {
                const safeQ = q.replace(/"/g, '&quot;');
                return `<button type="button" data-question="${safeQ}" onclick="window.submitSuggestedQuestion(this)" class="inline-block bg-white text-primary border border-primary/20 hover:bg-primary hover:text-white mt-2 mr-2 mb-1 px-3 py-1.5 rounded-full text-[11px] font-bold shadow-sm transition-all focus:ring-2 focus:ring-primary/50 text-left leading-tight break-words max-w-full"><span class="mr-1 opacity-70">✨</span>${safeQ}</button>`;
            }).join('');"""
            
    new3 = """let chipsHtml = data.suggested_questions.map(function(q) {
                const safeQ = q.replace(/"/g, '&quot;');
                return `<button type="button" data-question="${safeQ}" onclick="window.submitSuggestedQuestion(this)" class="marquee-chip"><span class="marquee-icon">✨</span><span class="text-left">${safeQ}</span></button>`;
            }).join('');
            if (chipsHtml) {
                chipsHtml = `<div class="marquee-container mt-4"><div class="marquee-content">${chipsHtml}${chipsHtml}</div></div>`;
            }"""

    content = content.replace(old1, new1)
    content = content.replace(old2, new2)
    content = content.replace(old3, new3)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

fix_dashboard(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard.html')
fix_dashboard(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard_en.html')
print("Fixed JS logic")
