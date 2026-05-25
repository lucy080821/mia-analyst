import re

def fix_navs(filepath, is_en):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Desktop Nav Fix
    # Swap `#showcase` and `#about`
    desktop_pattern = re.compile(r'(<a href="#showcase"[^>]*>(.*?)</a>\s*)(<a href="#about"[^>]*>(.*?)</a>)')
    match = desktop_pattern.search(content)
    if match:
        showcase_tag = match.group(1)
        about_tag = match.group(3)
        # Swap them: about_tag then showcase_tag
        content = content[:match.start()] + about_tag + "\n                " + showcase_tag.strip() + "\n" + content[match.end():]
        print(f"Fixed desktop nav in {filepath}")
    else:
        print(f"Could not find desktop nav or already fixed in {filepath}")

    # Mobile Nav Fix
    # Find `#about` and insert `#showcase` after it, if not already there
    mobile_pattern = re.compile(r'(<a href="#about" class="mobile-link">([^<]+)</a>)')
    mobile_match = mobile_pattern.search(content)
    if mobile_match:
        # Check if #showcase is already right after
        showcase_check = content[mobile_match.end():mobile_match.end()+100]
        if 'href="#showcase"' not in showcase_check:
            about_tag_full = mobile_match.group(1)
            if is_en:
                showcase_mobile = '\n                <a href="#showcase" class="mobile-link">Product</a>'
            else:
                showcase_mobile = '\n                <a href="#showcase" class="mobile-link">{{ "Sản phẩm" }}</a>'
            
            content = content[:mobile_match.end()] + showcase_mobile + content[mobile_match.end():]
            print(f"Fixed mobile nav in {filepath}")
        else:
            print(f"Mobile nav already has showcase in {filepath}")
    else:
        print(f"Could not find mobile nav in {filepath}")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

fix_navs('landing.html', False)
fix_navs('landing_en.html', True)
