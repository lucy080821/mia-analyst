import os
import re

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add CSS
    css_to_add = '''
    /* Infinite Marquee Styles */
    @keyframes marquee {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }
    .marquee-container {
        overflow: hidden;
        width: 100%;
        position: relative;
        padding: 6px 0;
        margin-bottom: -10px; /* Reduce bottom margin */
        -webkit-mask-image: linear-gradient(to right, transparent, black 10%, black 90%, transparent);
        mask-image: linear-gradient(to right, transparent, black 10%, black 90%, transparent);
    }
    .marquee-content {
        display: flex;
        width: max-content;
        animation: marquee 25s linear infinite;
    }
    .marquee-container:hover .marquee-content {
        animation-play-state: paused;
    }
    .marquee-chip {
        display: inline-flex;
        align-items: center;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(8px);
        color: var(--primary);
        border: 1px solid rgba(99, 102, 241, 0.2);
        padding: 10px 18px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        margin-right: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
        max-width: 350px;
        white-space: normal;
        line-height: 1.4;
    }
    .marquee-chip:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.2);
        border-color: var(--primary);
        color: var(--secondary);
    }
    .marquee-chip:hover .marquee-icon {
        transform: rotate(20deg) scale(1.2);
    }
    .marquee-icon {
        font-size: 16px;
        margin-right: 8px;
        flex-shrink: 0;
        transition: transform 0.3s ease;
    }
'''
    if '/* Infinite Marquee Styles */' not in content:
        content = content.replace('</style>', css_to_add + '\n</style>')

    # 2. Update initOnboardingSuggestions
    new_init = '''chipsHtml = data.suggestions.map(function(q) {
                    const safeQ = q.replace(/"/g, '&quot;');
                    return `<button type="button" data-question="${safeQ}" onclick="window.submitSuggestedQuestion(this)" class="marquee-chip"><span class="marquee-icon">✨</span><span class="text-left">${safeQ}</span></button>`;
                }).join('');
                if (chipsHtml) {
                    chipsHtml = `<div class="marquee-container mt-4"><div class="marquee-content">${chipsHtml}${chipsHtml}</div></div>`;
                }'''

    pattern_init = re.compile(r'chipsHtml\s*=\s*data\.suggestions\.map\(function\(q\)\s*\{\s*const safeQ[^}]+\}\)\.join\(\'\'\);\s*')
    if pattern_init.search(content):
        content = pattern_init.sub(new_init + '\n                ', content)

    # 3. Update the HTML insertion part
    # original: ${chipsHtml ? `<div class="mt-3 flex flex-wrap">${chipsHtml}</div>` : ''}
    # new: ${chipsHtml}
    target_str = '${chipsHtml ? `<div class="mt-3 flex flex-wrap">${chipsHtml}</div>` : \'\'}'
    content = content.replace(target_str, '${chipsHtml}')

    # 4. Update runDatasetAnalysis
    pattern_run = re.compile(r'let chipsHtml\s*=\s*data\.suggested_questions\.map\(function\(q\)\s*\{\s*const safeQ[^}]+\}\)\.join\(\'\'\);\s*')
    
    new_run = '''let chipsHtml = data.suggested_questions.map(function(q) {
                const safeQ = q.replace(/"/g, '&quot;');
                return `<button type="button" data-question="${safeQ}" onclick="window.submitSuggestedQuestion(this)" class="marquee-chip"><span class="marquee-icon">✨</span><span class="text-left">${safeQ}</span></button>`;
            }).join('');
            if (chipsHtml) {
                chipsHtml = `<div class="marquee-container mt-4"><div class="marquee-content">${chipsHtml}${chipsHtml}</div></div>`;
            }'''
            
    if pattern_run.search(content):
        content = pattern_run.sub(new_run + '\n\n            ', content)


    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated {filepath}")

process_file(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard.html')
process_file(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard_en.html')
