import os
import re

directory = "c:/Mia Analyst/templates"

global_dict = {
    # Accounts & Auth
    r'\{\{ "Đăng nhập" \}\}': 'Login',
    r'\{\{ "Đăng ký" \}\}': 'Register',
    r'\{\{ "Bạn chưa đăng nhập." \}\}': 'You are not logged in.',
    r'\{\{ "Tài khoản" \}\}': 'Account',
    r'\{\{ "Hồ sơ" \}\}': 'Profile',
    r'\{\{ "Mật khẩu" \}\}': 'Password',
    r'\{\{ "Quên mật khẩu" \}\}': 'Forgot password?',
    r'\{\{ "Đăng xuất" \}\}': 'Logout',
    r'\{\{ "Xác nhận Đăng xuất" \}\}': 'Confirm Logout',
    r'\{\{ "Bạn có chắc chắn muốn đăng xuất\?"\|escapejs \}\}': 'Are you sure you want to logout?',
    r'Đăng nhập': 'Login',
    r'Đăng ký': 'Register',
    
    # Common UI
    r'\{\{ "Quản trị hệ thống" \}\}': 'System Administration',
    r'\{\{ "Sức khỏe doanh nghiệp" \}\}': 'Business Health',
    r'\{\{ "Theo dõi hoạt động và doanh thu thời gian thực." \}\}': 'Track real-time activities and revenue.',
    r'\{\{ "Từ" \}\}': 'From',
    r'\{\{ "Đến" \}\}': 'To',
    r'\{\{ "Lọc dữ liệu" \}\}': 'Filter Data',
    r'\{\{ "Xuất Excel" \}\}': 'Export Excel',
    r'\{\{ "Tổng truy cập" \}\}': 'Total Visits',
    r'\{\{ "Khách duy nhất" \}\}': 'Unique Visitors',
    r'\{\{ "Thời gian trung bình" \}\}': 'Avg Time',
    r'\{\{ "Doanh thu" \}\}': 'Revenue',
    r'\{\{ "Doanh thu dự tính" \}\}': 'Expected Revenue',
    r'\{\{ "Tổng khách hàng" \}\}': 'Total Customers',
    
    # Notifications
    r'\{\{ "Thông báo" \}\}': 'Notifications',
    r'\{\{ "Đọc tất cả" \}\}': 'Mark all as read',
    r'\{\{ "Đánh dấu đã đọc" \}\}': 'Mark as read',
    r'\{\{ "Không có thông báo mới" \}\}': 'No new notifications',
    r'\{\{ "Xem tất cả thông báo" \}\}': 'View all notifications',
    r'\{\{ "Mia Thông báo"\|escapejs \}\}': 'Mia Notification',
    r'\{\{ "Đồng ý"\|escapejs \}\}': 'Confirm',
    r'\{\{ "Hủy"\|escapejs \}\}': 'Cancel',
    r'\{\{ "Đồng ý" \}\}': 'Confirm',
    r'\{\{ "Hủy" \}\}': 'Cancel',
}

for root, _, files in os.walk(directory):
    for str_file in files:
        if str_file.endswith("_en.html"):
            path = os.path.join(root, str_file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                for vi, en in global_dict.items():
                    content = re.sub(vi, en, content)
                
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Translated: {path}")
            except Exception as e:
                print(f"Error {path}: {e}")
