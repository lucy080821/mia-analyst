def update_view(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    old_logic = '''service_package = data.get('service_package', '').strip()'''
    new_logic = '''service_package = 'Unknown'
            if request.user.is_authenticated:
                try:
                    service_package = request.user.userprofile.get_tier_display()
                except:
                    try:
                        service_package = request.user.userprofile.tier
                    except:
                        pass'''
                        
    if "data.get('service_package'" in content:
        content = content.replace(old_logic, new_logic)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

update_view(r'C:\Leo Harrison\Mia Analyst\analytics\views.py')
print("View updated.")
