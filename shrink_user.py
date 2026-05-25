def shrink_user_msg(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Change max-w-[90%] md:max-w-[60%] to max-w-[85%] md:max-w-[48%]
    content = content.replace('max-w-[90%] md:max-w-[60%]', 'max-w-[85%] md:max-w-[48%]')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

shrink_user_msg(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard.html')
shrink_user_msg(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard_en.html')
print("User message width adjusted to under 50%")
