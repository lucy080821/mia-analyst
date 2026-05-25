def translate_feedback(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    replacements = {
        'Gửi góp ý': 'Send feedback',
        'Gửi Phản Hồi': 'Send Feedback',
        'Tên của bạn <span': 'Your Name <span',
        'Tên của bạn</label>': 'Your Name</label>',
        'Nhập tên của bạn': 'Enter your name',
        'Nội dung góp ý': 'Feedback Content',
        'Mọi ý kiến của bạn đều giúp hệ thống tuyệt vời hơn...': 'Your feedback helps us make the system better...',
        'Gửi đi ngay': 'Send Now',
        'Đang gửi...': 'Sending...',
        'Thành công!': 'Success!',
        'Cảm ơn bạn đã gửi phản hồi.': 'Thank you for your feedback.',
        "alert('Lỗi: '": "alert('Error: '",
        "alert('Đã xảy ra lỗi kết nối. Vui lòng thử lại sau.')": "alert('Connection error occurred. Please try again later.')",
        "'Cảm ơn bạn đã đóng góp ý kiến!'": "'Thank you for your feedback!'"
    }

    for vi, en in replacements.items():
        content = content.replace(vi, en)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

translate_feedback(r'C:\Leo Harrison\Mia Analyst\templates\analytics\dashboard_en.html')
print("Translated dashboard_en.html")
