import os
import re

file_path = "c:/Mia Analyst/templates/base_en.html"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

translations = {
    r'\{\{ "Bạn chưa đăng nhập." \}\}': 'You are not logged in.',
    r'\{\{ "Thông báo" \}\}': 'Notifications',
    r'\{\{ "Đọc tất cả" \}\}': 'Mark all as read',
    r'\{\{ "Đánh dấu đã đọc" \}\}': 'Mark as read',
    r'\{\{ "trước" \}\}': 'ago',
    r'\{\{ "Không có thông báo mới" \}\}': 'No new notifications',
    r'\{\{ "Xem thêm 5 thông báo" \}\}': 'View 5 more notifications',
    r'\{\{ "Xem tất cả thông báo" \}\}': 'View all notifications',
    r'\{\{ "Xác nhận xóa" \}\}': 'Confirm deletion',
    r'\{\{ "Hủy" \}\}': 'Cancel',
    r'\{\{ "Đồng ý" \}\}': 'Confirm',
    r'\{\{ "Tất cả quyền được bảo lưu." \}\}': 'All rights reserved.',
    r'\{\{ "Dashboard" \}\}': 'Dashboard',
    r'\{\{ "Tài khoản" \}\}': 'Account',
    r'\{\{ "Hồ sơ" \}\}': 'Profile',
    r'\{\{ "Nâng cấp" \}\}': 'Upgrade',
    r'\{\{ "Sản phẩm" \}\}': 'Products',
    r'\{\{ "Tính năng chính" \}\}': 'Features',
    r'\{\{ "Lộ trình phát triển" \}\}': 'Roadmap',
    r'\{\{ "Hỗ trợ" \}\}': 'Support',
    r'\{\{ "Tài liệu hướng dẫn" \}\}': 'Documentation',
    r'\{\{ "Chính sách bảo mật" \}\}': 'Privacy Policy',
    r'\{\{ "Điều khoản dịch vụ" \}\}': 'Terms of Service',
    r'\{\{ "Liên hệ" \}\}': 'Contact',
    r'\{\{ "Hỏi đáp" \}\}': 'FAQ',
    r'\{\{ "Đăng xuất" \}\}': 'Logout',
    r'href="/vi/': 'href="/en/',
}

for vi, en in translations.items():
    content = re.sub(vi, en, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("base_en.html translated successfully.")
