import pandas as pd
import io
import base64
import unicodedata
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from typing import List, Dict, Any, Optional, Tuple
import google.generativeai as genai
import gc
from django.conf import settings

# ══════════════════════════════════════════════════════════════
# BUSINESS VOCABULARY LAYER — Bilingual (Vietnamese + English)
# Mỗi nhóm từ khóa = một khái niệm nghiệp vụ rõ ràng, không trộn lẫn
# ══════════════════════════════════════════════════════════════

# ── 1. DOANH THU THỰC (Actual Revenue) ────────────────────────
# Tiền thực sự thu về sau khi trừ hủy, hoàn trả
ACTUAL_REVENUE_KW = [
    # Tiếng Việt
    'doanh thu', 'doanh thu thực', 'doanh thu thuần', 'doanh thu ròng',
    'thu nhập', 'tiền thu về', 'thu về', 'tổng thu',
    'doanh thu bán hàng', 'doanh thu thực tế', 'doanh thu net',
    # Tiếng Anh
    'revenue', 'net revenue', 'actual revenue', 'net income',
    'net sales', 'receipts', 'proceeds', 'net_revenue',
    'actual_revenue', 'revenue_net',
]

# ── 2. DOANH SỐ GỘP (Gross Sales) ─────────────────────────────
# Tổng giá trị bán ra, kể cả đơn chưa xác nhận / chưa thanh toán
GROSS_SALES_KW = [
    # Tiếng Việt
    'doanh số', 'tổng doanh số', 'doanh số bán', 'doanh số thuần',
    'tổng giá trị bán', 'doanh số bán hàng', 'tổng doanh thu gộp',
    'doanh số gross', 'tổng bán',
    # Tiếng Anh
    'sales', 'gross sales', 'total sales', 'turnover',
    'gross revenue', 'gmv', 'gross_sales', 'total_sales',
    'gross_revenue', 'sales_volume',
]

# ── 3. THÀNH TIỀN (Line Amount) ────────────────────────────────
# Giá trị từng dòng đơn hàng (price × quantity trên 1 dòng)
LINE_AMOUNT_KW = [
    # Tiếng Việt
    'thành tiền', 'tổng tiền', 'số tiền', 'giá trị đơn',
    'tổng đơn hàng', 'tổng cộng', 'tổng thanh toán', 'thanh toán',
    'tiền hàng', 'giá trị hóa đơn', 'tổng hóa đơn',
    # Tiếng Anh
    'amount', 'total amount', 'order value', 'line total',
    'subtotal', 'order total', 'payment amount', 'invoice total',
    'total_amount', 'order_value', 'line_amount', 'bill_amount',
]

# ── 4. LỢI NHUẬN (Profit) ─────────────────────────────────────
PROFIT_KW = [
    # Tiếng Việt
    'lợi nhuận', 'lãi', 'lãi gộp', 'lãi thuần', 'lãi ròng',
    'lợi nhuận gộp', 'lợi nhuận thuần', 'lợi nhuận ròng',
    'biên lợi nhuận', 'biên lãi',
    # Tiếng Anh
    'profit', 'gross profit', 'net profit', 'net margin',
    'margin', 'earnings', 'ebit', 'ebitda',
    'profit_margin', 'gross_profit', 'net_profit',
]

# ── 5. SỐ LƯỢNG (Quantity) ─────────────────────────────────────
QUANTITY_KW = [
    # Tiếng Việt
    'số lượng', 'sl', 'số lượng bán', 'số lượng đặt',
    'số lượt', 'đã bán', 'số sp', 'số sản phẩm',
    'số lượng sản phẩm', 'khối lượng',
    # Tiếng Anh
    'quantity', 'qty', 'units sold', 'volume', 'count',
    'pieces', 'pcs', 'units', 'num_items', 'quantity_sold',
    'order_quantity', 'item_count',
]

# ── 6. GIÁ VỐN / CHI PHÍ (Cost) ───────────────────────────────
COST_KW = [
    # Tiếng Việt
    'giá vốn', 'giá nhập', 'chi phí', 'chi phí mua hàng',
    'giá vốn hàng bán', 'chi phí hàng bán', 'giá nhập kho',
    # Tiếng Anh
    'cost', 'cogs', 'cost of goods', 'purchase price',
    'unit cost', 'cost_price', 'cost_of_goods_sold',
    'buying_price', 'wholesale_price',
]

# ── 7. CHI PHÍ QUẢNG CÁO (Ads Spend) ─────────────────────────
ADS_KW = [
    # Tiếng Việt
    'chi phí quảng cáo', 'chi phí ads', 'ngân sách quảng cáo',
    'chi tiêu quảng cáo', 'phí ads',
    # Tiếng Anh
    'ads cost', 'ad spend', 'advertising cost', 'marketing spend',
    'cpc', 'cpm', 'ads_cost', 'ad_spend', 'adspend',
    'advertising_cost', 'marketing_cost',
]

# ── 8. GIẢM GIÁ / KHUYẾN MÃI (Discount) ──────────────────────
DISCOUNT_KW = [
    # Tiếng Việt
    'giảm giá', 'chiết khấu', 'khuyến mãi', 'mã giảm',
    'voucher', 'coupon', 'ưu đãi', 'phần trăm giảm',
    # Tiếng Anh
    'discount', 'coupon', 'promo', 'promotion',
    'rebate', 'markdown', 'discount_amount', 'discount_rate',
    'promo_code', 'offer',
]

# ── 9. TỒN KHO (Stock/Inventory) ──────────────────────────────
STOCK_KW = [
    # Tiếng Việt
    'tồn kho', 'số lượng tồn', 'kho', 'số tồn',
    'còn lại', 'tồn', 'tồn kho hiện tại',
    # Tiếng Anh
    'inventory', 'stock', 'quantity_in_stock', 'remaining_stock',
    'stock_level', 'on_hand', 'available_qty',
]

# ── 10. NGÀY THÁNG (Date) ──────────────────────────────────────
DATE_KW = [
    # Tiếng Việt
    'ngày', 'ngày đặt', 'ngày tạo', 'ngày mua',
    'ngày giao', 'thời gian', 'ngày thanh toán', 'ngày đơn',
    'ngày hóa đơn', 'ngày phát sinh',
    # Tiếng Anh
    'date', 'order_date', 'created_at', 'purchase_date',
    'delivery_date', 'timestamp', 'created_date', 'order_time',
    'transaction_date', 'invoice_date',
]

# ── 11. KHÁCH HÀNG (Customer) ─────────────────────────────────
CUSTOMER_KW = [
    # Tiếng Việt
    'khách hàng', 'tên khách', 'người mua', 'mã khách', 'id khách',
    'tên người mua', 'khách', 'người dùng', 'thành viên',
    # Tiếng Anh
    'customer', 'buyer', 'client', 'user', 'member',
    'customer_id', 'user_id', 'buyer_id', 'client_id', 'customer_name',
]

# ── 12. SẢN PHẨM / DỊCH VỤ (Product) ──────────────────────────
PRODUCT_KW = [
    # Tiếng Việt
    'sản phẩm', 'tên sản phẩm', 'mặt hàng', 'sku', 'mã sp',
    'dịch vụ', 'loại hình', 'tên hàng', 'tổng cục',
    # Tiếng Anh
    'product', 'item', 'sku', 'product_name', 'service',
    'category', 'product_id', 'item_name', 'description',
]

# ── 13. LĨNH VỰC NHÂN SỰ (HR/Human Resources) ──────────────────
HR_KW = [
    'nhân sự', 'nhân viên', 'lương', 'phòng ban', 'chức vụ',
    'tuyển dụng', 'nghỉ việc', 'tỉ lệ nghỉ', 'hiệu suất',
    'employee', 'hr', 'salary', 'department', 'position',
    'recruitment', 'attrition', 'turnover', 'performance',
]

# ── 14. LĨNH VỰC Y TẾ (Healthcare) ──────────────────────────
HEALTHCARE_KW = [
    'bệnh nhân', 'bác sĩ', 'khám', 'chẩn đoán', 'triệu chứng',
    'điều trị', 'hồi phục', 'thuốc', 'viện phí',
    'patient', 'doctor', 'diagnosis', 'symptoms', 'treatment',
    'recovery', 'medication', 'medical_cost',
]

# ── 15. LĨNH VỰC GIÁO DỤC (Education) ────────────────────────
EDUCATION_KW = [
    'sinh viên', 'học sinh', 'điểm', 'kết quả', 'môn học',
    'giảng viên', 'lớp', 'học phí', 'học kỳ',
    'student', 'grade', 'score', 'results', 'subject',
    'teacher', 'class', 'tuition', 'semester',
]

# ── 16. LĨNH VỰC LOGISTICS / VẬN TẢI ─────────────────────────
LOGISTICS_KW = [
    'vận chuyển', 'giao hàng', 'vận đơn', 'kho hàng',
    'phí vận chuyển', 'thời gian giao', 'địa chỉ nhận',
    'shipping', 'delivery', 'tracking', 'warehouse',
    'logistics', 'lead_time', 'carrier', 'origin', 'destination',
]

# ── 13. ĐƠN HÀNG (Order Identifier) ──────────────────────────
# Cột định danh — KHÔNG được tính SUM hay AVG
IDENTIFIER_KW = [
    # Tiếng Việt
    'mã đơn', 'số đơn', 'mã hóa đơn', 'mã giao dịch',
    'id đơn', 'mã đơn hàng', 'số hóa đơn',
    # Tiếng Anh
    'order_id', 'invoice_id', 'transaction_id', 'tracking_id',
    'record_id', 'order_number', 'invoice_number', 'reference_id',
]

# ── 14. TRẠNG THÁI (Status) ────────────────────────────────────
STATUS_KW = [
    # Tiếng Việt
    'trạng thái', 'tình trạng', 'trạng thái đơn', 'tình trạng đơn',
    # Tiếng Anh
    'status', 'state', 'order_status', 'delivery_status',
]

# ── Giá trị trạng thái HỦY ────────────────────────────────────
CANCEL_VALUES = [
    'cancelled', 'canceled', 'hủy', 'huỷ', 'đã hủy',
    'cancel', 'hủy đơn', 'returned', 'refunded', 'hoàn trả',
]

# ══════════════════════════════════════════════════════════════
# COLUMN ROLE MAP — Ánh xạ từ keyword group → business role
# ══════════════════════════════════════════════════════════════
ROLE_MAP: List[Tuple[str, List[str]]] = [
    ('identifier', IDENTIFIER_KW),   # Ưu tiên cao: detect trước để tránh sum nhầm
    ('date',       DATE_KW),
    ('status',     STATUS_KW),
    ('revenue',    ACTUAL_REVENUE_KW),
    ('gross_sales', GROSS_SALES_KW),
    ('line_amount', LINE_AMOUNT_KW),
    ('profit',     PROFIT_KW),
    ('cost',       COST_KW),
    ('quantity',   QUANTITY_KW),
    ('ads',        ADS_KW),
    ('discount',   DISCOUNT_KW),
    ('stock',      STOCK_KW),
    ('customer',   CUSTOMER_KW),
    ('product',    PRODUCT_KW),
]

# Centralized config is now in settings.py


# ══════════════════════════════════════════════════════════════
# HELPER: Normalize tên cột để so sánh chịu được mọi format
# ══════════════════════════════════════════════════════════════
def _normalize(text: str) -> str:
    """
    Chuẩn hóa chuỗi để so sánh:
    - Bỏ dấu tiếng Việt
    - Chuyển về lowercase
    - Thay _, -, . bằng space
    - Bỏ ký tự đặc biệt dư thừa
    Ví dụ: 'Doanh_Thu' → 'doanh thu', 'Tổng Tiền' → 'tong tien'
    """
    text = text.lower().strip()
    # Bỏ dấu tiếng Việt
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    # Thay ký tự phân cách bằng space
    text = re.sub(r'[_\-\.\s]+', ' ', text)
    # Bỏ ký tự đặc biệt còn lại
    text = re.sub(r'[^a-z0-9 ]', '', text)
    return text.strip()


def _match_keywords(col_name: str, keywords: List[str]) -> bool:
    """
    Kiểm tra tên cột có khớp với danh sách từ khóa không.
    So sánh theo normalized form, hỗ trợ 3 mức:
    1. Khớp chính xác
    2. Tên cột bắt đầu bằng từ khóa
    3. Tên cột chứa từ khóa
    """
    col_norm = _normalize(col_name)
    kw_norms = [_normalize(kw) for kw in keywords]

    # 1. Exact match
    if col_norm in kw_norms:
        return True
    # 2. Starts with
    for kw in kw_norms:
        if kw and col_norm.startswith(kw):
            return True
    # 3. Contains (chỉ với từ khóa >= 4 ký tự để tránh false positive "sl", "id"...)
    for kw in kw_norms:
        if len(kw) >= 4 and kw in col_norm:
            return True
    return False


# ══════════════════════════════════════════════════════════════
# CORE: Gán role nghiệp vụ cho từng cột
# ══════════════════════════════════════════════════════════════
def _classify_column_role(df: pd.DataFrame) -> Dict[str, str]:
    """
    Tự động gán role nghiệp vụ cho từng cột trong DataFrame.
    
    Returns:
        Dict[col_name → role_string]
        Roles: 'identifier' | 'date' | 'status' | 'revenue' | 'gross_sales' |
               'line_amount' | 'profit' | 'cost' | 'quantity' | 'ads' |
               'discount' | 'stock' | 'customer' | 'product' | 'unknown'
    """
    roles = {}
    for col in df.columns:
        assigned = 'unknown'
        for role, keywords in ROLE_MAP:
            if _match_keywords(col, keywords):
                assigned = role
                break
        
        # Fallback thông minh dựa vào kiểu dữ liệu
        if assigned == 'unknown':
            if df[col].dtype in ['datetime64[ns]', 'datetime64[ns, UTC]']:
                assigned = 'date'
            elif df[col].dtype == 'object':
                # Kiểm tra có phải ngày không
                try:
                    pd.to_datetime(df[col].dropna().head(5))
                    assigned = 'date'
                except Exception:
                    assigned = 'category'
        
        roles[col] = assigned
    return roles


# ══════════════════════════════════════════════════════════════
# CORE: Tạo profile chi tiết cho từng cột (gửi cho AI)
# ══════════════════════════════════════════════════════════════
def _build_column_profile(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Tạo profile đầy đủ cho từng cột để AI hiểu dữ liệu sâu hơn.
    
    Mỗi profile gồm:
    - name, role, dtype
    - Với cột số: min, max, mean, sum, null_pct, zero_pct
    - Với cột text: top_values (tối đa 5), unique_count, null_pct
    - warning: cảnh báo nếu dữ liệu bất thường
    """
    roles = _classify_column_role(df)
    profiles = []

    for col in df.columns:
        role = roles[col]
        null_count = int(df[col].isna().sum())
        null_pct = round(null_count / len(df) * 100, 1) if len(df) > 0 else 0
        warnings = []

        profile: Dict[str, Any] = {
            'name': col,
            'role': role,
            'dtype': str(df[col].dtype),
            'null_pct': null_pct,
            'warning': [],
        }

        # Cột số
        if df[col].dtype in ['int64', 'int32', 'float64', 'float32']:
            numeric_s = pd.to_numeric(df[col], errors='coerce')
            zero_count = int((numeric_s == 0).sum())
            zero_pct = round(zero_count / len(df) * 100, 1) if len(df) > 0 else 0
            neg_count = int((numeric_s < 0).sum())

            profile.update({
                'min': round(float(numeric_s.min()), 2) if not numeric_s.empty else None,
                'max': round(float(numeric_s.max()), 2) if not numeric_s.empty else None,
                'mean': round(float(numeric_s.mean()), 2) if not numeric_s.empty else None,
                'sum': round(float(numeric_s.sum()), 2) if not numeric_s.empty else None,
                'zero_pct': zero_pct,
            })

            if role in ('revenue', 'gross_sales', 'line_amount', 'profit') and zero_pct >= 30:
                warnings.append(f"⚠️ {zero_pct}% giá trị = 0 — kết quả có thể bị lệch")
            if role in ('revenue', 'gross_sales', 'line_amount') and neg_count > 0:
                warnings.append(f"⚠️ Có {neg_count} giá trị âm — có thể là hoàn trả/điều chỉnh")
            if null_pct >= 20:
                warnings.append(f"⚠️ {null_pct}% null — cẩn thận khi tính trung bình")
            if role == 'identifier':
                warnings.append("🚫 Cột định danh — KHÔNG tính SUM/AVG")

        else:
            # Cột text / categorical / date
            unique_count = int(df[col].nunique())
            top_values = (
                df[col].astype(str)
                       .value_counts()
                       .head(5)
                       .to_dict()
            )
            profile.update({
                'unique_count': unique_count,
                'top_values': {str(k): int(v) for k, v in top_values.items()},
            })
            if null_pct >= 20:
                warnings.append(f"⚠️ {null_pct}% null")

        profile['warning'] = warnings
        profiles.append(profile)

    return profiles


# ══════════════════════════════════════════════════════════════
# CORE: Data Quality Guard
# ══════════════════════════════════════════════════════════════
def _check_data_quality(df: pd.DataFrame, profiles: List[Dict]) -> List[str]:
    """
    Kiểm tra chất lượng dữ liệu, trả về danh sách cảnh báo.
    Không block phân tích — chỉ cung cấp context cho AI.
    """
    alerts = []
    total_rows = len(df)

    if total_rows == 0:
        alerts.append("🚫 Dataset rỗng — không có dữ liệu để phân tích.")
        return alerts

    for p in profiles:
        for w in p.get('warning', []):
            alerts.append(f"Cột '{p['name']}' [{p['role']}]: {w}")

    # Kiểm tra tổng revenue = 0
    revenue_profiles = [p for p in profiles if p['role'] in ('revenue', 'gross_sales', 'line_amount')]
    for rp in revenue_profiles:
        if rp.get('sum', 1) == 0:
            alerts.append(f"🚫 Cột '{rp['name']}' có tổng = 0 — dữ liệu chưa được điền hoặc sai định dạng")

    # Kiểm tra ngày hợp lệ
    date_profiles = [p for p in profiles if p['role'] == 'date']
    for dp in date_profiles:
        if dp['null_pct'] >= 50:
            alerts.append(f"⚠️ Cột ngày '{dp['name']}' có {dp['null_pct']}% null — dự báo thời gian sẽ không chính xác")

    return alerts


# ══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS (Backward-compatible)
# ══════════════════════════════════════════════════════════════
def _find_col_by_role(df: pd.DataFrame, roles: List[str]) -> Optional[str]:
    """
    Tìm cột đầu tiên có role khớp với danh sách roles đã cho.
    """
    col_roles = _classify_column_role(df)
    for col, role in col_roles.items():
        if role in roles:
            return col
    return None


def _find_col(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
    """
    Backward-compatible: tìm cột theo danh sách từ khóa tùy ý.
    Giữ lại để dùng trong code cũ.
    """
    cols_lower = {col: col.lower().strip() for col in df.columns}
    for col, col_l in cols_lower.items():
        if col_l in [kw.lower() for kw in keywords]:
            return col
    for col, col_l in cols_lower.items():
        for kw in keywords:
            if col_l.startswith(kw.lower()):
                return col
    for col, col_l in cols_lower.items():
        for kw in keywords:
            if kw.lower() in col_l:
                return col
    return None


def _to_numeric_series(series: pd.Series) -> pd.Series:
    """Ép cột về numeric, loại bỏ ký tự tiền tệ / dấu phẩy."""
    return pd.to_numeric(
        series.astype(str)
              .str.replace(r'[^\d.\-]', '', regex=True)
              .replace('', '0'),
        errors='coerce'
    ).fillna(0)


def _get_revenue_col(df: pd.DataFrame) -> str:
    """
    Tìm cột doanh thu/doanh số/thành tiền tốt nhất.
    Ưu tiên: revenue → line_amount → gross_sales → cột số có tổng lớn nhất
    """
    # Dùng role-based detection
    col = _find_col_by_role(df, ['revenue', 'line_amount', 'gross_sales'])
    if col:
        return col

    # Fallback: cột số có tổng lớn nhất
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    # Loại bỏ cột identifier
    roles = _classify_column_role(df)
    numeric_cols = [c for c in numeric_cols if roles.get(c) != 'identifier']
    if numeric_cols:
        return max(numeric_cols, key=lambda c: df[c].sum())

    return df.columns[-1]


# ══════════════════════════════════════════════════════════════
# TIERED ANALYTICS SERVICE
# ══════════════════════════════════════════════════════════════
class TieredAnalyticsService:

    @staticmethod
    def get_df_from_file(file_content: bytes, filename: str, sheet_name=0) -> pd.DataFrame:
        """Đọc file từ bộ nhớ vào DataFrame."""
        buffer = io.BytesIO(file_content)
        if filename.endswith('.csv'):
            return pd.read_csv(buffer)
        else:
            return pd.read_excel(buffer, sheet_name=sheet_name)

    @staticmethod
    def get_ai_insight(summary: str, quality_alerts: List[str] = None, user_question: str = "") -> str:
        """Gọi Gemini AI để lấy nhận xét chiến lược từ tóm tắt dữ liệu toàn diện."""
        try:
            quality_context = ""
            if quality_alerts:
                quality_context = "CẢNH BÁO CHẤT LƯỢNG DỮ LIỆU:\n" + "\n".join([f"- {a}" for a in quality_alerts]) + "\n\n"

            # Detect language from user question
            lang_instruction = ""
            if user_question:
                lang_instruction = f"\nNgười dùng hỏi: \"{user_question}\" — HÃY TRẢ LỜI HOÀN TOÀN BẰNG NGÔN NGỮ CỦA CÂU HỎI ĐÓ."
            else:
                lang_instruction = "\nHÃY LUÔN TRẢ LỜI BẰNG NGÔN NGỮ PHÙ HỢP VỚI NGỮ CẢNH."

            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # Sử dụng model resolver an toàn — loại bỏ hoàn toàn lỗi 404
            from .ai_utils import get_generative_model
            model = get_generative_model()
            prompt = (
                "Bạn là chuyên gia phân tích dữ liệu cao cấp. Dưới đây là thông tin chi tiết về dataset:\n"
                f"{summary}\n\n"
                f"{quality_context}"
                "NHIỆM VỤ: Hãy quét qua tất cả các cột, tìm ra các mối liên hệ chéo và đưa ra đúng 3 nhận xét chiến lược chuyên sâu. "
                "Câu đầu tiên PHẢI đi thẳng vào số liệu hoặc phát hiện quan trọng nhất. KHÔNG dùng câu dạo đầu sáo rỗng. "
                f"{lang_instruction}"
            )
            response = model.generate_content(prompt)
            return response.text.strip() if response.text else "No insight available."
        except Exception as e:
            return f"AI Insight error: {str(e)}"

    @classmethod
    def _extract_basics(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """Trích xuất các chỉ số cơ bản từ DataFrame, sử dụng role-based detection."""
        profiles = _build_column_profile(df)
        quality_alerts = _check_data_quality(df, profiles)
        col_roles = _classify_column_role(df)

        # --- Doanh thu ---
        revenue_col = _get_revenue_col(df)
        revenue_series = _to_numeric_series(df[revenue_col])
        revenue = float(revenue_series.sum())

        # --- Xác định tên đúng theo role ---
        revenue_role = col_roles.get(revenue_col, 'unknown')
        revenue_label_map = {
            'revenue': 'Doanh thu',
            'gross_sales': 'Doanh số',
            'line_amount': 'Thành tiền',
            'profit': 'Lợi nhuận',
        }
        revenue_label = revenue_label_map.get(revenue_role, 'Giá trị')

        # --- Số đơn hàng ---
        orders = len(df)

        # --- Sản phẩm ---
        product_col = _find_col_by_role(df, ['product'])
        if not product_col:
            product_col = _find_col(df, PRODUCT_KW)

        top_products = []
        product_revenue = {}
        if product_col:
            if revenue_col and revenue_col != product_col:
                tmp = df[[product_col, revenue_col]].copy()
                tmp[revenue_col] = _to_numeric_series(tmp[revenue_col])
                grp = tmp.groupby(product_col)[revenue_col].sum().sort_values(ascending=False)
                top_products = [str(p) for p in grp.head(5).index.tolist()]
                product_revenue = {str(k): float(v) for k, v in grp.head(5).items()}
            else:
                grp = df[product_col].value_counts().head(5)
                top_products = [str(p) for p in grp.index.tolist()]
                product_revenue = {str(k): int(v) for k, v in grp.items()}

        # --- Lợi nhuận & Biên lợi nhuận ---
        cost_col = _find_col_by_role(df, ['cost'])
        profit = 0
        margin = 0
        if cost_col:
            cost_series = _to_numeric_series(df[cost_col])
            total_cost = float(cost_series.sum())
            profit = revenue - total_cost
            if revenue > 0:
                margin = (profit / revenue) * 100
        
        # --- 4. Tổng hợp toàn bộ cột (Full Column Summary cho AI) ---
        full_column_summary = []
        for p in profiles:
            line = f"- {p['name']} ({p['role']}): null={p['null_pct']}%"
            if 'mean' in p and p['mean'] is not None:
                line += f", mean={p['mean']:,.2f}"
            if 'unique_count' in p:
                line += f", unique={p['unique_count']}"
            full_column_summary.append(line)
        
        full_summary_text = "\n".join(full_column_summary)

        # --- 5. Ngữ cảnh dữ liệu (Industry Detection) ---
        context = cls._detect_dataset_context(df, col_roles)

        # --- 6. Tạo bảng Insight thông minh (JSON table cho UI) ---
        insight_table = cls._generate_insight_table(df, profiles, {
            'revenue': revenue,
            'orders': orders,
            'profit': profit,
            'margin': margin,
            'context': context,
            'revenue_label': revenue_label
        })

        return {
            'revenue': revenue,
            'revenue_col': revenue_col,
            'revenue_label': revenue_label,
            'profit': profit,
            'margin': margin,
            'orders': orders,
            'top_products': top_products,
            'product_revenue': product_revenue,
            'col_roles': col_roles,
            'profiles': profiles,
            'quality_alerts': quality_alerts,
            'product_col': product_col,
            'context': context,
            'full_column_summary': full_summary_text,
            'insight_table': insight_table,
        }

    @classmethod
    def _generate_insight_table(cls, df: pd.DataFrame, profiles: List[Dict], stats: Dict) -> List[Dict]:
        """Tạo bảng chỉ số thông minh Smart Business Overview."""
        table = []
        
        # 1. Chỉ số Quy mô (Mọi Dataset đều có)
        table.append({
            "Chỉ số": "Quy mô dữ liệu",
            "Giá trị": f"{stats['orders']:,} dòng",
            "Trạng thái": "✅ Ổn định" if stats['orders'] > 100 else "⚠️ Dữ liệu ít",
            "Đề xuất": "Tiếp tục thu thập thêm dữ liệu để tăng độ chính xác của AI."
        })
        
        table.append({
            "Chỉ số": "Chất lượng (Null)",
            "Giá trị": f"{sum(p['null_pct'] for p in profiles)/len(profiles):.1f}%",
            "Trạng thái": "✅ Tốt" if sum(p['null_pct'] for p in profiles)/len(profiles) < 10 else "❌ Cần làm sạch",
            "Đề xuất": "Sử dụng tính năng 'Làm sạch dữ liệu' nếu tỉ lệ trống quá cao."
        })

        # 2. Chỉ số Doanh thu (Nếu có)
        if stats['revenue'] > 0:
            table.append({
                "Chỉ số": f"Tổng {stats['revenue_label']}",
                "Giá trị": f"{stats['revenue']:,.0f}",
                "Trạng thái": "💰 Tích cực",
                "Đề xuất": "Tập trung tối ưu hóa các dòng sản phẩm đóng góp chính vào con số này."
            })

        # 3. Lợi nhuận & Biên độ (Nếu có)
        if stats.get('profit', 0) != 0:
            table.append({
                "Chỉ số": "Biên lợi nhuận",
                "Giá trị": f"{stats['margin']:.1f}%",
                "Trạng thái": "📈 Cao" if stats['margin'] > 20 else "⚠️ Cần tối ưu",
                "Đề xuất": "Xem xét lại giá vốn hoặc giảm chi phí vận hành để cải thiện biên lãi."
            })

        # 4. Chỉ số theo Ngữ cảnh (Context-specific)
        ctx = stats.get('context', 'Tổng quát')
        if ctx == 'HR':
            table.append({
                "Chỉ số": "Ngữ cảnh Nhân sự",
                "Giá trị": f"{len(profiles)} cột liên quan",
                "Trạng thái": "👤 Phân tích",
                "Đề xuất": "Phân tích tỉ lệ biến động nhân sự và chi phí lương trên hiệu suất."
            })
        elif ctx == 'Logistics':
            table.append({
                "Chỉ số": "Vận hành & Kho",
                "Giá trị": "Đang quét",
                "Trạng thái": "🚚 Logistics",
                "Đề xuất": "Tối ưu hóa thời gian giao hàng và lộ trình vận chuyển để giảm chi phí."
            })

        return table

    @classmethod
    def _detect_dataset_context(cls, df: pd.DataFrame, roles: Dict[str, str]) -> str:
        """Tự động nhận diện lĩnh vực của dữ liệu dựa trên các cột đã phân tích."""
        score = {
            'SME/Retail': 0,
            'HR': 0,
            'Healthcare': 0,
            'Education': 0,
            'Logistics': 0,
        }
        
        # 1. Check roles
        if 'revenue' in roles.values() or 'gross_sales' in roles.values():
            score['SME/Retail'] += 5
        if 'cost' in roles.values():
            score['SME/Retail'] += 3
        if 'product' in roles.values():
            score['SME/Retail'] += 2

        # 2. Check keyword groups
        cols = [c.lower() for c in df.columns]
        for c in cols:
            if any(kw in c for kw in HR_KW): score['HR'] += 1
            if any(kw in c for kw in HEALTHCARE_KW): score['Healthcare'] += 1
            if any(kw in c for kw in EDUCATION_KW): score['Education'] += 1
            if any(kw in c for kw in LOGISTICS_KW): score['Logistics'] += 1
        
        # Get highest score
        max_score = max(score.values())
        if max_score > 0:
            return [k for k, v in score.items() if v == max_score][0]
        return "Tổng quát"

    @classmethod
    def _generate_chart(cls, df: pd.DataFrame, basics: Dict) -> str:
        """Tạo biểu đồ từ dữ liệu thực, trả về base64 PNG."""
        try:
            fig, axes = plt.subplots(1, 2, figsize=(12, 4))
            fig.patch.set_facecolor('#f8f9ff')
            colors = ['#6366f1', '#8b5cf6', '#ec4899', '#3b82f6', '#10b981']

            # --- Biểu đồ 1: Top sản phẩm theo doanh thu ---
            ax1 = axes[0]
            ax1.set_facecolor('#f8f9ff')
            product_revenue = basics.get('product_revenue', {})
            revenue_label = basics.get('revenue_label', 'Doanh thu')
            if product_revenue:
                labels = list(product_revenue.keys())
                values = list(product_revenue.values())
                short_labels = [str(l)[:18] + '…' if len(str(l)) > 18 else str(l) for l in labels]
                ax1.barh(short_labels[::-1], values[::-1], color=colors[:len(labels)], height=0.6)
                ax1.set_title(f'Top {len(labels)} Sản phẩm theo {revenue_label}',
                              fontsize=9, fontweight='bold', color='#1e293b', pad=8)
                ax1.set_xlabel(revenue_label, fontsize=7, color='#64748b')
                ax1.tick_params(axis='y', labelsize=7, colors='#1e293b')
                ax1.tick_params(axis='x', labelsize=6, colors='#64748b')
                ax1.xaxis.set_major_formatter(mticker.FuncFormatter(
                    lambda x, _: f'{x/1e6:.1f}M' if x >= 1e6 else (f'{x/1e3:.0f}K' if x >= 1e3 else f'{x:.0f}')
                ))
                ax1.spines['top'].set_visible(False)
                ax1.spines['right'].set_visible(False)
                ax1.spines['left'].set_visible(False)
                ax1.grid(axis='x', linestyle='--', alpha=0.3)
            else:
                ax1.text(0.5, 0.5, 'Không tìm thấy\ncột sản phẩm', ha='center', va='center',
                         fontsize=9, color='#94a3b8', transform=ax1.transAxes)
                ax1.set_title('Top Sản phẩm', fontsize=9, fontweight='bold', color='#1e293b')
                ax1.axis('off')

            # --- Biểu đồ 2: Phân bố giá trị ---
            ax2 = axes[1]
            ax2.set_facecolor('#f8f9ff')
            revenue_col = basics.get('revenue_col')
            if revenue_col and revenue_col in df.columns:
                rev_series = _to_numeric_series(df[revenue_col])
                rev_series = rev_series[rev_series > 0]
                if len(rev_series) > 0:
                    ax2.hist(rev_series, bins=min(20, len(rev_series)), color='#6366f1',
                             alpha=0.75, edgecolor='white', linewidth=0.5)
                    ax2.set_title(f'Phân bố {revenue_label}', fontsize=9, fontweight='bold',
                                  color='#1e293b', pad=8)
                    ax2.set_xlabel('Giá trị', fontsize=7, color='#64748b')
                    ax2.set_ylabel('Số lượng', fontsize=7, color='#64748b')
                    ax2.xaxis.set_major_formatter(mticker.FuncFormatter(
                        lambda x, _: f'{x/1e6:.1f}M' if x >= 1e6 else (f'{x/1e3:.0f}K' if x >= 1e3 else f'{x:.0f}')
                    ))
                    ax2.spines['top'].set_visible(False)
                    ax2.spines['right'].set_visible(False)
                    ax2.grid(axis='y', linestyle='--', alpha=0.3)
                    ax2.tick_params(labelsize=6)
                else:
                    ax2.text(0.5, 0.5, 'Không có dữ liệu số', ha='center', va='center',
                             fontsize=9, color='#94a3b8', transform=ax2.transAxes)
                    ax2.axis('off')
            else:
                ax2.axis('off')

            plt.tight_layout(pad=2.0)
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#f8f9ff')
            buf.seek(0)
            chart_b64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
            return chart_b64
        except Exception:
            plt.close('all')
            return ''

    @classmethod
    def analyze_basic(cls, df: pd.DataFrame, user_question: str = "") -> Dict[str, Any]:
        """FREE TIER: Phân tích cơ bản."""
        basics = cls._extract_basics(df)
        revenue = basics['revenue']
        orders = basics['orders']
        top_products = basics['top_products']
        revenue_col = basics['revenue_col']
        revenue_label = basics['revenue_label']
        quality_alerts = basics['quality_alerts']

        top_str = ', '.join(top_products[:3]) if top_products else 'Chưa xác định'
        alert_str = (' Lưu ý chất lượng dữ liệu: ' + '; '.join(quality_alerts)) if quality_alerts else ''

        summary_text = basics['full_column_summary']
        ai_insight = cls.get_ai_insight(summary_text, quality_alerts=quality_alerts, user_question=user_question)

        return {
            "tier": "FREE",
            "context": basics['context'],
            "revenue": revenue,
            "revenue_col": revenue_col,
            "revenue_label": revenue_label,
            "orders": orders,
            "top_products": top_products,
            "product_revenue": basics['product_revenue'],
            "quality_alerts": quality_alerts,
            "insight_table": basics['insight_table'],
            "ai_insight": ai_insight,
        }

    @classmethod
    def analyze_professional(cls, df: pd.DataFrame, user_question: str = "") -> Dict[str, Any]:
        """PLUS TIER: Phân tích chuyên nghiệp + Biểu đồ."""
        basic = cls.analyze_basic(df)
        basics_raw = cls._extract_basics(df)
        revenue = basic['revenue']
        revenue_col = basic['revenue_col']
        revenue_label = basic['revenue_label']
        col_roles = basics_raw['col_roles']

        # --- ROAS ---
        ads_col = _find_col_by_role(df, ['ads'])
        if not ads_col:
            ads_col = _find_col(df, ADS_KW)
        ads_cost = 0.0
        if ads_col:
            try:
                ads_cost = float(_to_numeric_series(df[ads_col]).sum())
            except Exception:
                ads_cost = 0.0
        roas = (revenue / ads_cost) if ads_cost > 0 else 0.0

        # --- Tỉ lệ hủy ---
        status_col = _find_col_by_role(df, ['status'])
        if not status_col:
            status_col = _find_col(df, STATUS_KW)
        cancel_count = 0
        cancel_rate = 0.0
        if status_col:
            cancel_count = int(df[status_col].astype(str).str.lower().isin(CANCEL_VALUES).sum())
            cancel_rate = (cancel_count / len(df)) * 100 if len(df) > 0 else 0.0

        # --- Biểu đồ ---
        chart_b64 = cls._generate_chart(df, basics_raw)

        summary_text = basics_raw['full_column_summary']
        ai_insight = cls.get_ai_insight(summary_text, quality_alerts=basic.get('quality_alerts'), user_question=user_question)

        return {
            **basic,
            "tier": "PLUS",
            "context": basics_raw['context'],
            "ads_cost": ads_cost,
            "ads_col": ads_col,
            "roas": roas,
            "cancel_count": cancel_count,
            "cancel_rate": cancel_rate,
            "status_col": status_col,
            "insight_table": basics_raw['insight_table'],
            "chart": chart_b64,
            "ai_insight": ai_insight,
        }

    @classmethod
    def analyze_enterprise(cls, dfs: List[pd.DataFrame], user_question: str = "") -> Dict[str, Any]:
        """PREMIUM TIER: Phân tích đa kênh."""
        combined_df = pd.concat(dfs, ignore_index=True)
        pro = cls.analyze_professional(combined_df)

        # --- Tồn kho thấp ---
        stock_col = _find_col_by_role(combined_df, ['stock'])
        if not stock_col:
            stock_col = _find_col(combined_df, STOCK_KW)
        low_stock_items = []
        if stock_col:
            stock_series = _to_numeric_series(combined_df[stock_col])
            product_col_real = _find_col_by_role(combined_df, ['product'])
            if product_col_real and product_col_real in combined_df.columns:
                low_mask = stock_series < 10
                low_items = combined_df[low_mask][product_col_real].astype(str).unique()[:5]
                low_stock_items = low_items.tolist()
            else:
                low_stock_items = [f"{stock_col} < 10: {(stock_series < 10).sum()} dòng"]
        else:
            low_stock_items = ["Không tìm thấy cột tồn kho trong dữ liệu"]

        # --- LTV ---
        revenue = pro['revenue']
        unique_customers = 1
        customer_col = _find_col_by_role(combined_df, ['customer'])
        if customer_col:
            unique_customers = int(max(1, combined_df[customer_col].nunique()))
        ltv_value = float(revenue / unique_customers)
        ltv_summary = (
            f"LTV trung bình: {ltv_value:,.0f} VNĐ / khách hàng "
            f"({unique_customers} khách hàng duy nhất)"
            if customer_col else
            f"LTV ước lượng: {ltv_value:,.0f} VNĐ / đơn hàng"
        )

        # --- Flash Sale ---
        top3 = pro['top_products'][:3]
        flash_sale_script = (
            f"Đề xuất Flash Sale 20% cho: {', '.join(top3)} vào khung giờ 12h-14h ngày mai."
            if top3 else
            "Chưa đủ dữ liệu sản phẩm để đề xuất Flash Sale."
        )

        # basics_raw cần thiết cho context và insight_table
        basics_raw = cls._extract_basics(combined_df)

        summary_text = (
            f"DỮ LIỆU ĐA KÊNH: {basics_raw['full_column_summary']}\n\n"
            f"CẢNH BÁO TỒN KHO: {', '.join(low_stock_items)}."
        )
        ai_insight = cls.get_ai_insight(summary_text, quality_alerts=pro.get('quality_alerts'), user_question=user_question)

        return {
            **pro,
            "tier": "ENTERPRISE",
            "context": basics_raw['context'],
            "low_stock": low_stock_items,
            "flash_sale_script": flash_sale_script,
            "ltv_summary": ltv_summary,
            "ltv_value": ltv_value,
            "insight_table": basics_raw['insight_table'],
            "ai_insight": ai_insight,
        }

    @classmethod
    def suggest_data_cleaning(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """Đề xuất các bước làm sạch dữ liệu dựa trên AI."""
        try:
            profiles = _build_column_profile(df)
            quality_alerts = _check_data_quality(df, profiles)
            
            # Count duplicates
            duplicate_count = int(df.duplicated().sum())
            if duplicate_count > 0:
                quality_alerts.append(f"Có {duplicate_count} dòng trùng lặp hoàn toàn.")

            if not quality_alerts:
                return {"status": "success", "suggestions": [], "message": "Dữ liệu đã sạch, không cần xử lý thêm."}

            context = "\n".join([f"- {a}" for a in quality_alerts])
            
            from .ai_utils import get_generative_model
            model = get_generative_model()
            prompt = f"""
Bạn là chuyên gia Data Engineer. Dưới đây là các vấn đề chất lượng dữ liệu:
{context}

Hãy đề xuất các bước làm sạch dữ liệu. PHẢI TRẢ VỀ JSON array chứa các object, mỗi object có định dạng:
{{
    "action": "Tên hành động: dropna, fillna, drop_duplicates, hoặc drop_column",
    "column": "Tên cột (nếu áp dụng, hoặc null)",
    "value": "Giá trị điền vào nếu là fillna (ví dụ 0, 'Unknown'), hoặc null",
    "reason": "Giải thích ngắn gọn lý do bằng tiếng Việt"
}}
Ví dụ:
[
  {{"action": "drop_duplicates", "column": null, "value": null, "reason": "Xóa các dòng trùng lặp"}},
  {{"action": "fillna", "column": "Doanh thu", "value": 0, "reason": "Điền 0 cho doanh thu bị trống"}},
  {{"action": "dropna", "column": "Mã đơn", "value": null, "reason": "Xóa dòng nếu thiếu mã đơn"}}
]
TRẢ VỀ DUY NHẤT JSON ARRAY. KHÔNG CHỨA MARKDOWN.
            """
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3].strip()
            
            import json
            suggestions = json.loads(text)
            return {"status": "success", "suggestions": suggestions, "message": "Đã tạo đề xuất làm sạch."}
        except Exception as e:
            return {"status": "error", "suggestions": [], "message": f"Lỗi tạo đề xuất: {str(e)}"}

    @classmethod
    def apply_data_cleaning(cls, df: pd.DataFrame, rules: List[Dict]) -> pd.DataFrame:
        """Áp dụng các rules làm sạch lên DataFrame."""
        cleaned_df = df.copy()
        try:
            for rule in rules:
                action = rule.get('action')
                col = rule.get('column')
                val = rule.get('value')
                
                if action == 'drop_duplicates':
                    cleaned_df = cleaned_df.drop_duplicates()
                elif action == 'dropna':
                    if col and col in cleaned_df.columns:
                        cleaned_df = cleaned_df.dropna(subset=[col])
                    else:
                        cleaned_df = cleaned_df.dropna()
                elif action == 'fillna':
                    if col and col in cleaned_df.columns:
                        cleaned_df[col] = cleaned_df[col].fillna(val)
                    else:
                        cleaned_df = cleaned_df.fillna(val)
                elif action == 'drop_column':
                    if col and col in cleaned_df.columns:
                        cleaned_df = cleaned_df.drop(columns=[col])
                        
            return cleaned_df
        except Exception as e:
            print(f"Error applying cleaning rules: {e}")
            return df # Return original if failed

    @classmethod
    def calculate_root_cause(cls, df: pd.DataFrame, metric_col: str = None, date_col: str = None) -> Dict[str, Any]:
        """Tự động drill-down để tìm nguyên nhân giảm chỉ số (Root Cause Analysis)."""
        try:
            if df.empty:
                return {"status": "error", "message": "Dữ liệu trống"}

            # Auto-detect date_col if not provided
            if not date_col:
                date_col = _find_col_by_role(df, ['date'])
                if not date_col:
                    return {"status": "error", "message": "Không tìm thấy cột ngày tháng để so sánh kỳ."}
            
            # Auto-detect metric_col if not provided
            if not metric_col:
                metric_col = _get_revenue_col(df)

            df_temp = df.copy()
            df_temp[date_col] = pd.to_datetime(df_temp[date_col], errors='coerce')
            df_temp = df_temp.dropna(subset=[date_col])
            if df_temp.empty:
                 return {"status": "error", "message": "Cột ngày tháng bị rỗng hoặc sai định dạng."}
            
            df_temp[metric_col] = _to_numeric_series(df_temp[metric_col])
            
            max_date = df_temp[date_col].max()
            
            # Compare last 30 days vs previous 30 days
            from datetime import timedelta
            current_start = max_date - timedelta(days=30)
            prev_start = current_start - timedelta(days=30)
            
            curr_df = df_temp[df_temp[date_col] > current_start]
            prev_df = df_temp[(df_temp[date_col] > prev_start) & (df_temp[date_col] <= current_start)]
            
            curr_val = curr_df[metric_col].sum()
            prev_val = prev_df[metric_col].sum()
            
            delta = curr_val - prev_val
            if prev_val == 0:
                pct_change = 100 if curr_val > 0 else 0
            else:
                pct_change = (delta / prev_val) * 100
                
            variance_analysis = {
                "metric": metric_col,
                "current_val": float(curr_val),
                "prev_val": float(prev_val),
                "delta": float(delta),
                "pct_change": float(pct_change),
                "root_cause_insight": "Không có sự sụt giảm."
            }

            # Only find root cause if it dropped
            if delta < 0:
                # Find categorical columns for drill-down
                cat_cols = [c for c in df_temp.columns if c != metric_col and c != date_col and df_temp[c].nunique() < 20]
                
                biggest_drop_col = None
                biggest_drop_cat = None
                biggest_drop_val = 0
                
                for col in cat_cols:
                    curr_grp = curr_df.groupby(col)[metric_col].sum()
                    prev_grp = prev_df.groupby(col)[metric_col].sum()
                    
                    diff = curr_grp.subtract(prev_grp, fill_value=0)
                    if diff.empty: continue
                    min_diff = diff.min()
                    if min_diff < biggest_drop_val:
                        biggest_drop_val = min_diff
                        biggest_drop_col = col
                        biggest_drop_cat = diff.idxmin()
                
                if biggest_drop_col:
                    variance_analysis["root_cause_insight"] = (
                        f"Chỉ số {metric_col} giảm {abs(pct_change):.1f}% "
                        f"nguyên nhân lớn nhất do '{biggest_drop_cat}' (trong nhóm {biggest_drop_col}) "
                        f"giảm {abs(biggest_drop_val):,.0f} so với kỳ trước."
                    )
                else:
                    variance_analysis["root_cause_insight"] = f"Chỉ số {metric_col} giảm {abs(pct_change):.1f}% đều trên toàn hệ thống."
            
            return {"status": "success", "analysis": variance_analysis}

        except Exception as e:
            return {"status": "error", "message": f"Lỗi RCA: {str(e)}"}

    @staticmethod
    def cleanup():
        """Giải phóng bộ nhớ."""
        plt.close('all')
        gc.collect()
