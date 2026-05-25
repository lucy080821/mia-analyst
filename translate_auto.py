import os
import re

directory = "c:/Mia Analyst/templates"

global_dict = {
# -- Global/Nav/Auth terms --
    "Đăng nhập": "Login",
    "Đăng ký": "Register",
    "Bạn chưa đăng nhập.": "You are not logged in.",
    "Tài khoản": "Account",
    "Hồ sơ": "Profile",
    "Mật khẩu": "Password",
    "Quên mật khẩu": "Forgot password?",
    "Đăng xuất": "Logout",
    "Xác nhận Đăng xuất": "Confirm Logout",
    "Bạn có chắc chắn muốn đăng xuất?": "Are you sure you want to logout?",
    "Quản trị hệ thống": "System Administration",
    "Sức khỏe doanh nghiệp": "Business Health",
    "Theo dõi hoạt động và doanh thu thời gian thực.": "Track real-time activities and revenue.",
    "Từ": "From",
    "Đến": "To",
    "Lọc dữ liệu": "Filter Data",
    "Xuất Excel": "Export Excel",
    "Tổng truy cập": "Total Visits",
    "Khách duy nhất": "Unique Visitors",
    "Thời gian trung bình": "Avg Time",
    "Doanh thu": "Revenue",
    "Doanh thu dự tính": "Expected Revenue",
    "Tổng khách hàng": "Total Customers",
    "Thông báo": "Notifications",
    "Đọc tất cả": "Mark all as read",
    "Đánh dấu đã đọc": "Mark as read",
    "Không có thông báo mới": "No new notifications",
    "Xem tất cả thông báo": "View all notifications",
    "Mia Thông báo": "Mia Notification",
    "Đồng ý": "Confirm",
    "Hủy": "Cancel",
    
    # -- Blog --
    "Góc nhìn chuyên sâu về dữ liệu": "In-depth Data Analytics Insights",
    "Cập nhật những xu hướng, kiến thức và case study mới nhất về ứng dụng AI trong phân tích dữ liệu doanh nghiệp.": "Stay updated with the latest trends, knowledge, and case studies on AI in enterprise data analytics.",
    "Tất cả": "All",
    "Giải pháp": "Solutions",
    "Kiến thức": "Knowledge",
    "Công nghệ": "Technology",
    "Case Study": "Case Study",
    "Chi tiết Báo cáo": "Report Details",
    "Tác giả": "Author",
    "Ngày": "Date",
    "phút đọc": "min read",
    "Trước": "Previous",
    "Sau": "Next",
    "Chia sẻ bài viết": "Share Post",
    "Tags:": "Tags:",
    "Bài viết liên quan": "Related Posts",
    "Sao chép link": "Copy Link",
    "Đã sao chép vào bộ nhớ tạm!": "Copied to clipboard!",
    "Lỗi khi sao chép link": "Error copying link",
    "Không tìm thấy bài viết nào trong chuyên mục này.": "No posts found in this category.",
    "Tóm tắt nội dung (Summary):": "Content Summary:",

    # -- Dashboard --
    "Tổng quan Hệ thống": "System Overview",
    "Số liệu thống kê thời gian thực": "Real-time statistics",
    "Đơn hàng hoàn tất": "Completed Orders",
    "Khách hàng mới": "New Customers",
    "Thống kê Lợi nhuận gộp": "Gross Profit Stats",
    "Phân tích hành vi": "Behavior Analysis",
    "AI Insights": "AI Insights",
    "Phân tích bằng Mia AI": "Analyze with Mia AI",
    "Cấu hình Báo cáo tự động": "Automated Report Configuration",
    "Cài đặt Telegram Bot": "Telegram Bot Setup",
    "Lưu cấu hình Telegram": "Save Telegram Config",
    "Tạo lịch gửi báo cáo (Task mới)": "Create Schedule (New Task)",
    "Tên báo cáo": "Report Name",
    "Câu hỏi AI (Prompt)": "AI Prompt",
    "Tần suất": "Frequency",
    "Hàng ngày": "Daily",
    "Hàng tuần": "Weekly",
    "Hàng tháng": "Monthly",
    "Chọn Thứ": "Select Day",
    "Thời gian nhận": "Receiving Time",
    "Trạng thái": "Status",
    "Hành động": "Actions",
    "Đang chạy": "Running",
    "Tạm dừng": "Paused",
    "Xóa": "Delete",
    "Bạn có thực sự muốn xóa lịch này không?": "Are you sure you want to delete this schedule?",
    "Quản lý Nguồn dữ liệu": "Manage Data Sources",
    "Kết nối ERP/CRM": "Connect ERP/CRM",
    "Tải lên CSV/Excel": "Upload CSV/Excel",
    "Chưa kết nối CSDL nào": "No DB connected yet",
    "Kết nối Shopee": "Connect Shopee",
    "Dữ liệu mẫu từ CSDL": "Sample DB Data",
    "Dự báo Doanh thu (AI)": "Revenue Forecast (AI)",
    "Tỉ lệ khách hàng quay lại": "Customer Retention Rate",

    # -- Add additional mappings for templates if they are standard words.
}

def translate_match(match):
    original_text = match.group(1)
    # Check if exact match exists
    if original_text in global_dict:
        return '{{ "' + global_dict[original_text] + '" }}'
    return match.group(0)

# Also let's handle words outside the tags like in Blog (e.g. "Ngày:", "Tác giả:")
replace_outside = {
    "Góc nhìn chuyên sâu về dữ liệu": "In-depth Data Analytics Insights",
    "Cập nhật những xu hướng, kiến thức và case study mới nhất về ứng dụng AI trong phân tích dữ liệu doanh nghiệp.": "Stay updated with the latest trends, knowledge, and case studies on AI in enterprise data analytics.",
    "Không tìm thấy bài viết nào trong chuyên mục này.": "No posts found in this category.",
    "Tóm tắt nội dung (Summary):": "Content Summary:",
    "Ngày:": "Date:",
    "Tác giả:": "Author:",
    "phút đọc": "min read",
    "Trước": "Previous",
    "Sau": "Next",
    "Bài viết liên quan": "Related Posts"
}

for root, _, files in os.walk(directory):
    for str_file in files:
        if str_file.endswith("_en.html"):
            path = os.path.join(root, str_file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                # 1. First Pass: Handle {{ "Vi Text" }}
                # {{ 'Vi text' }}
                content = re.sub(r'\{\{\s*\"(.*?)\"\s*\}\}', translate_match, content)
                content = re.sub(r"\{\{\s*\'(.*?)\'\s*\}\}", translate_match, content)

                # 2. Second Pass: Replace common standalone Vietnamese words
                for vi, en in replace_outside.items():
                    content = content.replace(vi, en)

                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Translated: {path}")
            except Exception as e:
                print(f"Error {path}: {e}")

