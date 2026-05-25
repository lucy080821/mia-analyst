import os
import time
import requests
import pandas as pd
from .db_utils import get_sqlalchemy_engine

def fetch_shopee_orders(partner_id, shop_id, access_token):
    """
    1. Kết nối với Shopee API dùng requests để lấy danh sách đơn hàng.
    Lưu ý: API Shopee v2 thực tế yêu cầu tạo chữ ký HMAC-SHA256 bảo mật dựa trên path, timestamp, partner_key, etc.
    Do tính chất bảo mật, dưới đây là logic khung (kèm mock data) để bạn tham khảo.
    """
    url = "https://partner.shopeemobile.com/api/v2/order/get_order_list"
    
    timestamp = int(time.time())
    
    # Các tham số query mẫu
    params = {
        "time_range_field": "create_time",
        "time_from": timestamp - 86400 * 7,  # Lấy đơn 7 ngày qua
        "time_to": timestamp,
        "page_size": 20,
        "shop_id": shop_id,
        "access_token": access_token,
        "partner_id": partner_id
        # "sign": "CHU_KY_HMAC_CUA_BAN"  <- Bạn sẽ tạo chữ ký và gắn vào đây
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Thực hiện gọi API thật (bỏ comment 2 dòng dưới nếu đã cấu hình xong token/sign)
    # response = requests.get(url, headers=headers, params=params)
    # data = response.json()
    
    # DỮ LIỆU GIẢ LẬP (Mock JSON Data) cho mục đích test quá trình Pandas/SQL
    data = {
        "error": "",
        "message": "",
        "response": {
            "order_list": [
                {"order_sn": "230801ABCDEFGH", "order_status": "COMPLETED", "create_time": 1690858000, "total_amount": 150000},
                {"order_sn": "230802IJKLMNOP", "order_status": "READY_TO_SHIP", "create_time": 1690944400, "total_amount": 250000},
                {"order_sn": "230803QRSTUVWX", "order_status": "UNPAID", "create_time": 1691030800, "total_amount": 110000},
                {"order_sn": "230804HHSDFKKK", "order_status": "CANCELLED", "create_time": 1691130800, "total_amount": 50000},
            ]
        }
    }
    
    if data.get("error"):
        print(f"Lỗi gọi API: {data.get('message')}")
        return []
        
    order_list = data.get("response", {}).get("order_list", [])
    print(f"[API] Lấy thành công {len(order_list)} đơn hàng.")
    return order_list


def convert_to_dataframe(orders_json):
    """
    2. Chuyển đổi dữ liệu JSON thành Pandas DataFrame.
    """
    if not orders_json:
        return pd.DataFrame()
        
    df = pd.DataFrame(orders_json)
    
    # Bổ sung một cột định dạng ngày tháng dễ đọc từ Timestamp
    if 'create_time' in df.columns:
        df['create_time_dt'] = pd.to_datetime(df['create_time'], unit='s')
        
    print(f"[Pandas] DataFrame được tạo với Shape: {df.shape}")
    return df


def save_to_temp_sql(df, db_path, table_name="temp_shopee_orders"):
    """
    3. Viết hàm lưu dữ liệu vào bảng tạm thời trong SQL Database (SQLite)
    """
    if df.empty:
        print("[SQL] DataFrame rỗng, không có dữ liệu để lưu.")
        return
        
    try:
        # Lấy SQLAlchemy engine
        engine = get_sqlalchemy_engine()
        
        # Chuẩn hóa và bảo vệ dữ liệu (Global logic: ID strings + Overflow protection)
        from .utils import prepare_df_for_sqlite # Có thể giữ tên prepare_df_for_sqlite vì logic clean giống nhau
        df = prepare_df_for_sqlite(df)
        
        # Hàm to_sql của Pandas tự động tạo bảng hoặc ghi đè
        df.to_sql(name=table_name, con=engine, if_exists="replace", index=False)
        print(f"[SQL] Lưu dữ liệu thành công vào bảng tạm: '{table_name}'.")
        
    except Exception as e:
        print(f"[SQL] Lỗi lưu bảng CSDL: {e}")


if __name__ == "__main__":
    # Thay đổi thông tin thực tế từ tài khoản Shopee Open API của bạn
    PARTNER_ID = 123456
    SHOP_ID = 98765432
    ACCESS_TOKEN = "TEST_TOKEN"
    
    # 1. Fetch data
    orders_data = fetch_shopee_orders(PARTNER_ID, SHOP_ID, ACCESS_TOKEN)
    
    # 2. Transform to DataFrame
    df_orders = convert_to_dataframe(orders_data)
    
    # Hiển thị vài dòng đầu trước khi lưu
    if not df_orders.empty:
        print("\n--- Dữ liệu Preview ---")
        print(df_orders.head())
        print("-----------------------\n")
    
    # 3. Load to Database
    # Sử dụng db.sqlite3 mặc định của project Django hiện tại
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sqlite_db_path = os.path.join(BASE_DIR, "db.sqlite3")
    
    save_to_temp_sql(df_orders, db_path=sqlite_db_path)
