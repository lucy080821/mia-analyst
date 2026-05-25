def fix_timeline_spacing(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content.replace('<div class="space-y-12 relative z-10">', '<div class="space-y-24 relative z-10">')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Fixed {filepath}")

fix_timeline_spacing('landing.html')
fix_timeline_spacing('landing_en.html')
