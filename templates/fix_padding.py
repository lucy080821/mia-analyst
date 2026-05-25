import re

def fix_hero_padding(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find hero section and add pb-24
    pattern = r'(<section class="hero-section relative min-h-screen flex items-center pt-20) (overflow-hidden">)'
    new_content = re.sub(pattern, r'\1 pb-24 \2', content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed padding in {filepath}")
    else:
        print(f"No changes made to {filepath} or already fixed.")

fix_hero_padding('landing.html')
fix_hero_padding('landing_en.html')
