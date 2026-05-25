def shrink_dashboard(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Shrink bot messages width
    content = content.replace('max-w-[95%]', 'max-w-[95%] md:max-w-[65%]')
    
    # 2. Shrink user messages width
    content = content.replace('max-w-[85%]', 'max-w-[90%] md:max-w-[60%]')

    # 3. Stack the chips vertically for cleaner look (remove flex-wrap)
    content = content.replace('mt-3 flex flex-wrap', 'mt-3 flex flex-col space-y-2 items-start')
    
    # 4. Remove margins from chips since we use space-y-2 now
    content = content.replace('mt-2 mr-2 mb-1 px-3 py-1.5', 'px-3 py-2')
    
    # Also adjust the button class to have slightly less padding if needed or make it look better
    # The button has text-left leading-tight break-words max-w-full. This is good.

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

shrink_dashboard(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard.html')
shrink_dashboard(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard_en.html')
print("Shrink applied")
