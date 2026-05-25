import pandas as pd
import numpy as np
import re

def prepare_df_for_sqlite(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuẩn hóa DataFrame để lưu vào SQLite an toàn:
    1. Chuẩn hóa tên cột (Unique, SQL-safe).
    2. Chuyển các cột ID/SKU/SĐT về chuỗi (TEXT).
    3. Chống lỗi 'int too large for SQLite' bằng cách chuyển số cực lớn về chuỗi.
    4. Xử lý giá trị trống.
    """
    if df is None or df.empty:
        return df

    # --- 1. Chuẩn hóa tên cột (Unique & SQL-safe) ---
    def normalize_name(col):
        col = str(col).strip()
        if not col or 'Unnamed' in col: return None
        col = col.replace(' ', '_')
        col = ''.join(c if c.isalnum() or c in '_-' else '' for c in col)
        col = col.strip('_-')
        return col if col else None

    new_columns = []
    used_names = set()
    for i, col in enumerate(df.columns):
        norm = normalize_name(col)
        if not norm:
            norm = f"col_{i+1}"
        
        original_norm = norm
        counter = 1
        while norm.lower() in used_names:
            norm = f"{original_norm}_{counter}"
            counter += 1
        
        used_names.add(norm.lower())
        new_columns.append(norm)
    df.columns = new_columns

    # --- 2. Xử lý định dạng dữ liệu (ID keywords & Overflow protection) ---
    id_keywords = ['id', 'sku', 'code', 'ma', 'mã', 'phone', 'số_điện_thoại', 'barcode', 'serial', 'isbn', 'vận_đơn', 'post', 'zip']
    sqlite_max_int = 9223372036854775807
    sqlite_min_int = -9223372036854775808

    for col in df.columns:
        # A. Tự động chuyển ID/SKU/SĐT về chuỗi
        is_id_like = any(kw in col.lower() for kw in id_keywords)
        if is_id_like:
            df[col] = df[col].astype(str).replace(['nan', 'None', 'NaN', 'null'], '')
            continue

        # B. Bảo vệ lỗi tràn số SQLite (Overflow Error)
        # Kiểm tra cả Int và Float (vì số lớn có thể được read là float64)
        if pd.api.types.is_numeric_dtype(df[col]) or df[col].dtype == 'object':
            try:
                # Tìm các giá trị vượt ngưỡng 64-bit int
                # Dùng absolute để bao quát cả âm/dương lớn
                mask = df[col].apply(lambda x: isinstance(x, (int, float)) and not pd.isna(x) and (x > sqlite_max_int or x < sqlite_min_int))
                if mask.any():
                    df[col] = df[col].astype(str).replace(['nan', 'None', 'NaN', 'null'], '')
            except:
                pass

    return df
