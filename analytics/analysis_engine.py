"""
Hybrid Analysis Engine — SQL + Python + Machine Learning
Linh hoạt chọn phương pháp phân tích phù hợp theo câu hỏi và tier người dùng.
"""
import pandas as pd
import numpy as np
import io
import json
import re
import traceback
from typing import Dict, Any, Optional, Tuple, List

from django.conf import settings
import google.generativeai as genai

# Import Business Vocabulary Layer từ services
from .services import _build_column_profile, _classify_column_role


# ============================================================
# 1. METHOD SELECTOR — AI quyết định phương pháp phân tích
# ============================================================

def determine_analysis_method(
    question: str, columns: list, sample_data: list,
    tier: str, api_key: str,
    df: pd.DataFrame = None,
    model_name: str = None
) -> Dict[str, Any]:
    """
    Gọi Gemini để quyết định phương pháp phân tích phù hợp.
    Gửi column profiles đầy đủ (role, min/max/mean, warnings) thay vì chỉ tên cột.
    Returns: {"method": "sql"|"python"|"ml_cluster"|"ml_forecast"|"ml_anomaly", "params": {...}}
    """
    available_methods = ["sql", "python"]
    ml_note = ""
    if tier == "PREMIUM":
        available_methods.extend(["ml_cluster", "ml_forecast", "ml_anomaly", "dashboard"])
        ml_note = """
        - "ml_cluster": Phân cụm dữ liệu (K-Means). Dùng khi user hỏi về phân nhóm/phân cụm/segment.
        - "ml_forecast": Dự báo xu hướng. Dùng khi user hỏi về dự báo/forecast/xu hướng tương lai. CẦN cột ngày.
        - "ml_anomaly": Phát hiện bất thường. Dùng khi user hỏi về outlier/bất thường/đơn hàng lạ.
        - "dashboard": Multi-chart (2-4 biểu đồ). CHỈ dùng khi user ĐÍCH DANH yêu cầu "tạo dashboard".
        """

    sample_str = json.dumps(sample_data[:3], ensure_ascii=False, default=str) if sample_data else "[]"

    # ── Build rich column profiles ──────────────────────────────────────────
    col_profile_lines = []
    numeric_cols_for_ml = []
    date_cols = []

    if df is not None:
        try:
            profiles = _build_column_profile(df)
            roles = _classify_column_role(df)
            for p in profiles:
                name = p['name']
                role = p['role']
                dtype = p['dtype']
                null = p['null_pct']
                warns = ' | '.join(p.get('warning', [])) or 'OK'

                if 'mean' in p:  # numeric column
                    line = (
                        f"  - '{name}' [ROLE:{role}] — số — "
                        f"mean:{p['mean']:,.0f} min:{p['min']:,.0f} max:{p['max']:,.0f} "
                        f"null:{null}% — {warns}"
                    )
                    if role not in ('identifier',):
                        numeric_cols_for_ml.append(name)
                else:  # text/date column
                    top = list(p.get('top_values', {}).keys())[:3]
                    line = (
                        f"  - '{name}' [ROLE:{role}] — text — "
                        f"unique:{p.get('unique_count','?')} top:[{', '.join(top)}] "
                        f"null:{null}% — {warns}"
                    )
                    if role == 'date':
                        date_cols.append(name)

                col_profile_lines.append(line)
        except Exception:
            pass

    # Fallback nếu không có df
    if not col_profile_lines:
        if sample_data and sample_data[0]:
            first = sample_data[0]
            for col in columns:
                val = first.get(col)
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    numeric_cols_for_ml.append(col)
                    col_profile_lines.append(f"  - '{col}' [ROLE:unknown] — số")
                else:
                    col_profile_lines.append(f"  - '{col}' [ROLE:unknown] — text")
        else:
            col_profile_lines = [f"  - '{c}'" for c in columns]
            numeric_cols_for_ml = columns

    col_profile_str = '\n'.join(col_profile_lines)
    ml_safe_cols = json.dumps(numeric_cols_for_ml, ensure_ascii=False)
    date_col_hint = f"Cột ngày tốt nhất: {date_cols[0]}" if date_cols else "Không tìm thấy cột ngày"

    prompt = f"""Bạn là AI phân tích dữ liệu. Chọn PHƯƠNG PHÁP PHÂN TÍCH phù hợp nhất cho câu hỏi.

THÔNG TIN CHI TIẾT TỪNG CỘT (đã phân tích):
{col_profile_str}

CỘT SỐ AN TOÀN CHO ML (không phải identifier): {ml_safe_cols}
{date_col_hint}
DỮ LIỆU MẪU: {sample_str}

CÁC PHƯƠNG PHÁP KHẢ DỤNG:
- "sql": Truy vấn SQL. Dùng khi câu hỏi chỉ cần lọc/đếm/tổng/nhóm cơ bản.
- "python": Python/Pandas nâng cao. Dùng khi cần: correlation, pivot phức tạp, phân bố, tỉ lệ %.
- "dashboard": Tổng hợp nhiều biểu đồ. Dùng khi người dùng yêu cầu "dashboard", "nhiều biểu đồ", hoặc yêu cầu phân tích từ 2 khía cạnh trở lên cùng lúc.
{ml_note}

CÂU HỎI: "{question}"

TRẢ VỀ JSON DUY NHẤT (không text thừa, không markdown):
{{
    "method": "<phương pháp>",
    "reason": "<lý do ngắn gọn, đề cập tên cột cụ thể>",
    "chart_type": "<bar|line|pie|none>",
    "params": {{
        "features": ["<CHỈ dùng cột từ danh sách CỘT SỐ AN TOÀN>"],
        "date_col": "<cột ngày nếu forecast>",
        "value_col": "<cột số nếu forecast — KHÔNG dùng identifier>",
        "periods": 30
    }}
}}

QUY TẮC CHỌN CHART:
- So sánh hạng mục / top N → "bar"
- Xu hướng thời gian → "line"
- Tỉ lệ phần trăm → "pie"
- Chỉ bảng, không vẽ → "none"

QUY TẮC QUAN TRỌNG:
- ƯU TIÊN TUYỆT ĐỐI: Nếu người dùng yêu cầu rõ loại biểu đồ (ví dụ: "vẽ bar chart", "dùng biểu đồ cột", "vẽ line chart", "biểu đồ tròn") → BẮT BUỘC chọn đúng chart_type đó (bar/line/pie).
- CẤM TUYỆT ĐỐI: Không bao giờ dùng "line" chart nếu dữ liệu trục X là văn bản, tên hãng, tên người, ID (Categorical data). CHỈ dùng "line" cho chuỗi thời gian (Date/Time).
- TOP N / SO SÁNH: Luôn luôn dùng "bar" chart.
- KHÔNG BAO GIỜ chọn cột [ROLE:identifier] vào features/value_col
- Nếu câu hỏi đơn giản → "sql"
- Nếu cần tính toán phức tạp → "python"
- Nếu không phải PREMIUM, ML methods không khả dụng → dùng "python"
- Nếu người dùng yêu cầu "dashboard", "nhiều biểu đồ" hoặc liệt kê danh sách nhiều chart cần vẽ → BẮT BUỘC chọn "dashboard".
- Phương pháp "dashboard" hiện đã khả dụng cho tất cả các gói (FREE giới hạn 2 charts, PLUS/PREMIUM lên đến 4 charts).
- Nếu user hỏi "doanh số": ưu tiên cột ROLE:gross_sales
- QUY TẮC CHART: Với Bar/Pie, nếu không có yêu cầu số lượng cụ thể, luôn lấy Top 15 để đảm bảo UI đẹp.
- QUY TẮC ƯU TIÊN: Nếu user yêu cầu rõ chart type, KHÔNG ĐƯỢC tự ý thay đổi.
"""
    
    try:
        from .ai_utils import get_generative_model
        model = get_generative_model(model_name)
        response = model.generate_content(prompt)
        if not (response.candidates and response.candidates[0].content.parts):
            return {"method": "sql", "reason": "AI response blocked by safety filter", "chart_type": "none", "params": {}}
        text = response.text.strip()
        
        # Clean markdown wrappers
        text = text.replace("```json", "").replace("```", "").strip()
        
        result = json.loads(text)
        
        # Safety: Validate method is allowed for this tier
        if result.get("method") not in available_methods:
            if result.get("method", "").startswith("ml_"):
                result["method"] = "python"
                result["reason"] = f"ML không khả dụng cho gói {tier}. Chuyển sang phân tích Python."
            else:
                result["method"] = "sql"
        
        return result
        
    except (json.JSONDecodeError, Exception) as e:
        # Fallback: dùng keyword matching đơn giản
        return _fallback_method_selection(question, tier)


def _fallback_method_selection(question: str, tier: str) -> Dict[str, Any]:
    """Fallback khi AI không trả về JSON hợp lệ — dùng keyword matching."""
    q = question.lower()
    
    ml_keywords_cluster = ["phân cụm", "clustering", "segment", "nhóm hóa", "phân nhóm", "k-means", "chia nhóm"]
    ml_keywords_forecast = ["dự báo", "forecast", "predict", "dự đoán", "xu hướng tương lai", "tháng tới", "ngày tới"]
    ml_keywords_anomaly = ["bất thường", "anomaly", "outlier", "lạ", "đột biến", "ngoại lệ"]
    python_keywords = ["phân bố", "distribution", "correlation", "tương quan", "percentile", "pivot", 
                       "xu hướng", "trend", "so sánh", "tỷ lệ", "tỉ lệ", "phân tích sâu", "chi tiết",
                       "histogram", "biểu đồ phân bố"]
    
    if tier == "PREMIUM":
        if any(kw in q for kw in ml_keywords_cluster):
            return {"method": "ml_cluster", "reason": "Keyword match: clustering", "chart_type": "bar", "params": {"features": []}}
        if any(kw in q for kw in ml_keywords_forecast):
            return {"method": "ml_forecast", "reason": "Keyword match: forecast", "chart_type": "line", "params": {"periods": 30}}
        if any(kw in q for kw in ml_keywords_anomaly):
            return {"method": "ml_anomaly", "reason": "Keyword match: anomaly", "chart_type": "line", "params": {"features": []}}
    
    chart_type = "bar" if any(kw in q for kw in ["bar", "cột"]) else ("line" if any(kw in q for kw in ["line", "đường", "xu hướng"]) else ("pie" if any(kw in q for kw in ["pie", "tròn", "tỉ lệ"]) else "none"))

    if any(kw in q for kw in python_keywords):
        return {"method": "python", "reason": "Keyword match: advanced analysis", "chart_type": chart_type, "params": {}}
    
    return {"method": "sql", "reason": "Default: simple query", "chart_type": chart_type, "params": {}}


# ============================================================
# 2. PYTHON ANALYSIS — Pandas sandbox execution
# ============================================================

def generate_python_code(
    question: str, columns: list, sample_data: list,
    tier: str, api_key: str,
    df: pd.DataFrame = None,
    model_name: str = None
) -> str:
    """Gemini sinh code Python/Pandas để phân tích, có context về role của từng cột."""

    tier_note = ""
    if tier == "FREE":
        tier_note = "Chỉ sử dụng thống kê cơ bản: describe(), value_counts(), sum(), mean()."
    elif tier == "PLUS":
        tier_note = "Có thể sử dụng phân tích nâng cao: correlation, pivot_table, groupby phức tạp."
    elif tier == "PREMIUM":
        tier_note = "Full power: mọi phân tích Pandas, NumPy."

    sample_str = json.dumps(sample_data[:3], ensure_ascii=False, default=str)

    # Build column role hints
    col_role_lines = []
    identifier_cols = []
    if df is not None:
        try:
            profiles = _build_column_profile(df)
            for p in profiles:
                role = p['role']
                hint = f"'{p['name']}' [ROLE:{role}]"
                if 'mean' in p:
                    hint += f" — số, mean={p['mean']:,.0f}"
                else:
                    hint += f" — text"
                if role == 'identifier':
                    hint += " ← KHÔNG tính SUM/AVG/GROUP"
                    identifier_cols.append(p['name'])
                col_role_lines.append(hint)
        except Exception:
            pass

    col_context = '\n'.join(col_role_lines) if col_role_lines else json.dumps(columns, ensure_ascii=False)
    id_warning = (
        f"\nCỘT CHỈ LÀ ĐỊNH DANH — TUYỆT ĐỐI KHÔNG tính SUM/AVG: {identifier_cols}"
        if identifier_cols else ""
    )

    prompt = f"""Bạn là Python Data Analyst. Viết code Python/Pandas để phân tích dữ liệu.

THÔNG TIN DỮ LIỆU (đã phân tích role từng cột):
{col_context}{id_warning}
- DataFrame tên là `df` (đã có sẵn)
- Dữ liệu mẫu: {sample_str}

CÂU HỎI: "{question}"

QUY TẮC TIER [{tier}]: {tier_note}

QUY TẮC CODE (BẮT BUỘC):
1. Code phải gán kết quả vào biến `result` (dict hoặc list). KHÔNG dùng lệnh `return` ở ngoài hàm (sẽ gây lỗi SyntaxError).
2. KHÔNG DÙNG THƯ VIỆN ĐỒ HOẠ (matplotlib, seaborn). Hệ thống tự động vẽ biểu đồ Chart.js dựa trên dữ liệu bạn trả về.
3. Nếu user KHÔNG CHỈ ĐỊNH vẽ biểu đồ, và kết quả là bảng → result = df_result.to_dict('records')
4. Nếu user CÓ YÊU CẦU vẽ biểu đồ: Hãy format biến `result` = df_result.to_dict('records') với cột đầu tiên là Nhãn (Labels), các cột tiếp theo là Số (Values) để Frontend tự động đưa lên chart.
5. Nếu kết quả là đáp án dạng text/số → result = {{"summary": "Giải thích...", "details": [...]}}
6. CHỈ dùng: pandas (as pd), numpy (as np), io, statistics.
7. KHÔNG import thêm module nào khác. KHÔNG dùng os, sys, subprocess.
8. KHÔNG print(). Code phải handle lỗi (try/except).
9. QUAN TRỌNG VỀ NGÀY THÁNG: Khi xử lý cột thời gian, BẮT BUỘC dùng `pd.to_datetime(df['col'], dayfirst=True, errors='coerce')` để không bị lỗi với định dạng ngày DD/MM/YYYY của Việt Nam. Cần dropna() sau khi chuyển đổi.

EXAMPLE CODE FORMAT (Vẽ biểu đồ / Bảng dữ liệu):
```python
import numpy as np

try:
    # Nếu user muốn so sánh Feature:
    # Lấy các cột số, tính giá trị trung bình để vẽ bar chart từng feature
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_means = df[numeric_cols].mean().reset_index()
    feature_means.columns = ['Feature', 'Average Value']
    result = feature_means.to_dict('records')
except Exception as e:
    result = {{"error": str(e)}}
```

CHỈ TRẢ VỀ CODE PYTHON. KHÔNG giải thích, KHÔNG markdown wrapper.
"""
    
    try:
        from .ai_utils import get_generative_model
        model = get_generative_model(model_name)
        response = model.generate_content(prompt)
        if not (response.candidates and response.candidates[0].content.parts):
            return 'result = {"error": "AI response blocked by safety filter"}'
        code = response.text.strip()
        
        # Clean markdown - Lấy chính xác phần code trong block ```python ... ```
        match = re.search(r'```(?:python)?\s*(.*?)\s*```', code, re.IGNORECASE | re.DOTALL)
        if match:
            code = match.group(1).strip()
        else:
            code = code.replace("```python", "").replace("```", "").strip()
        
        # Sửa lỗi SyntaxError: 'return' outside function nếu AI nhầm lẫn
        code = re.sub(r'^return\s+(.*)', r'result = \1', code, flags=re.MULTILINE)
        
        return code
    except Exception as e:
        return f'result = {{"error": "Lỗi sinh code: {str(e)}"}}'


def generate_dashboard_code(question: str, columns: list, sample_data: list, tier: str, api_key: str, model_name: str = None, tier_limit: int = 4, context_text: str = "") -> str:
    """Sinh code Python để tạo DataFrame cho hệ thống vẽ multi-chart dashboard."""
    sample_str = json.dumps(sample_data[:3], ensure_ascii=False, default=str) if sample_data else "[]"
    
    prompt = f"""Bạn là Chuyên gia Data Analyst. User yêu cầu "Tạo dashboard". Cần phân tích và thiết kế từ 2 đến {tier_limit} biểu đồ thiết thực nhất để tạo thành 1 bản báo cáo toàn diện.
    
THÔNG TIN DỮ LIỆU:
- DataFrame tên là `df` (đã có sẵn)
- Các cột: {json.dumps(columns, ensure_ascii=False)}
- Dữ liệu mẫu: {sample_str}
- GÓI DỊCH VỤ: {tier} (Giới hạn tối đa {tier_limit} biểu đồ)

{context_text}

CÂU HỎI: "{question}"

QUY TẮC CODE (BẮT BUỘC):
1. Tính toán ra dữ liệu cho TỐI ĐA {tier_limit} biểu đồ. Gán kết quả cuối cùng vào biến `result` (dict).
2. KHÔNG DÙNG THƯ VIỆN ĐỒ HOẠ (matplotlib). Hệ thống dùng Frontend vẽ biểu đồ (Chart.js).
3. Format biến `result` bắt buộc phải là:
result = {{
    "summary": "Tóm tắt ý nghĩa tổng thể của các biểu đồ này...",
    "dashboards": [
        {{"title": "Tên biểu đồ 1", "type": "bar", "data": df_1.to_dict('records')}},
        {{"title": "Tên biểu đồ 2", "type": "pie", "data": df_2.to_dict('records')}}
    ]
}}
4. Các `type` được phép: "line", "bar", "pie", "doughnut".
5. Với mỗi dataframe con (Ví dụ df_1), CHỈ CÓ TỐI ĐA 2 CỘT: Cột Số 1 dùng làm Nhãn (Labels), Cột Số 2 dùng làm Giá trị Số (Values).
6. CHỈ dùng: pandas (as pd), numpy (as np). Handle lỗi try/except. Nếu lỗi: result = {{"error": "..."}}

7. ƯU TIÊN TUYỆT ĐỐI: Nếu người dùng yêu cầu rõ loại biểu đồ (ví dụ: "vẽ bar chart", "dùng biểu đồ cột", "vẽ line chart", "biểu đồ tròn") → BẮT BUỘC chọn đúng `type` đó (bar/line/pie).
8. SỐ LƯỢNG BIỂU ĐỒ: Nếu user nói "3 chart" hoặc "4 chart", bạn PHẢI tạo ra ĐÚNG số lượng đó trong mảng `dashboards`.
9. TRUNCATE DATA: Với các biểu đồ dạng "bar" hoặc "pie", nếu có quá 15 hạng mục, hãy tự động lấy TOP 15 hạng mục lớn nhất để biểu đồ không bị rối mắt.
10. QUAN TRỌNG VỀ NGÀY THÁNG: Khi ép kiểu cột thời gian, BẮT BUỘC dùng `pd.to_datetime(df['col'], dayfirst=True, errors='coerce')` để hỗ trợ định dạng DD/MM/YYYY.
11. KHÔNG giải thích, KHÔNG markdown wrapper. CHỈ TRẢ VỀ CODE PYTHON.
"""
    try:
        from .ai_utils import get_generative_model
        model = get_generative_model(model_name)
        response = model.generate_content(prompt)
        if not (response.candidates and response.candidates[0].content.parts):
            return 'result = {"error": "AI response blocked by safety filter"}'
        code = response.text.strip()
        match = re.search(r'```(?:python)?\s*(.*?)\s*```', code, re.IGNORECASE | re.DOTALL)
        if match:
            code = match.group(1).strip()
        code = code.replace("```python", "").replace("```", "").strip()
        code = re.sub(r'^return\s+(.*)', r'result = \1', code, flags=re.MULTILINE)
        return code
    except Exception as e:
        return f'result = {{"error": "Lỗi sinh code dashboard: {str(e)}"}}'


def execute_python_safely(code: str, df: pd.DataFrame) -> Dict[str, Any]:
    """
    Chạy code Python trong sandbox giới hạn (Docker container).
    Returns: {"result": ..., "chart_base64": ... or None, "error": ... or None}
    """
    import os
    import tempfile
    import uuid
    import json
    import subprocess
    import shutil

    # Create a unique temporary directory inside the project to ensure Docker can mount it
    base_tmp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sandbox_tmp')
    os.makedirs(base_tmp_dir, exist_ok=True)
    session_id = str(uuid.uuid4())
    tmp_dir = os.path.join(base_tmp_dir, f"session_{session_id}")
    os.makedirs(tmp_dir, exist_ok=True)
    
    try:
        # 1. Save DataFrame to CSV
        data_path = os.path.join(tmp_dir, 'data.csv')
        df.to_csv(data_path, index=False)

        # 2. Prepare Sandbox Code
        # We indent the AI's code to run inside our try-except block
        indented_code = chr(10).join(['    ' + line for line in code.split(chr(10))])
        
        sandbox_code = f"""import pandas as pd
import numpy as np
import json
import io
import math
import datetime
import traceback

def custom_json_encoder(obj):
    if isinstance(obj, np.integer): return int(obj)
    if isinstance(obj, np.floating): return float(obj)
    if isinstance(obj, np.ndarray): return obj.tolist()
    if pd.isna(obj): return None
    raise TypeError(f"Object of type {{type(obj)}} is not JSON serializable")

try:
    df = pd.read_csv('/workspace/data.csv')
    result = None

{indented_code}

    if isinstance(result, pd.DataFrame):
        result = result.to_dict('records')
    elif isinstance(result, pd.Series):
        result = result.to_dict()

    with open('/workspace/result.json', 'w') as f:
        json.dump({{"result": result, "error": None}}, f, default=custom_json_encoder)
except Exception as e:
    with open('/workspace/result.json', 'w') as f:
        json.dump({{"result": None, "error": str(e)}}, f)
"""
        code_path = os.path.join(tmp_dir, 'script.py')
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(sandbox_code)

        # 3. Execute Docker Container
        cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "-m", "256m",
            "--cpus", "0.5",
            "--user", "sandboxuser",
            "-v", f"{tmp_dir}:/workspace",
            "mia_sandbox_image",
            "python", "/workspace/script.py"
        ]
        
        # Timeout 10 seconds for docker to start and run
        subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        # 4. Read Results
        result_path = os.path.join(tmp_dir, 'result.json')
        if os.path.exists(result_path):
            with open(result_path, 'r', encoding='utf-8') as f:
                res_data = json.load(f)
                return {"result": res_data.get("result"), "error": res_data.get("error")}
        else:
            return {"result": None, "error": "Sandbox failed to produce output. Possible timeout, Memory Limit (OOM), or syntax error."}

    except subprocess.TimeoutExpired:
        return {"result": None, "error": "Lỗi: Code phân tích chạy quá thời gian cho phép (Timeout > 10s)."}
    except Exception as e:
        return {"result": None, "error": f"Lỗi môi trường Sandbox: {str(e)}"}
    finally:
        # Cleanup
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except:
            pass


# ============================================================
# 3. MACHINE LEARNING — Clustering, Forecast, Anomaly
# ============================================================

def execute_ml_clustering(df: pd.DataFrame, features: list = None, max_k: int = 10) -> Dict[str, Any]:
    """
    K-Means clustering với Elbow method tự động tìm K tối ưu.
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import silhouette_score
    
    try:
        # Auto-detect hoặc lọc numeric features
        if not features:
            features = df.select_dtypes(include=[np.number]).columns.tolist()
        else:
            # Lọc lại features do AI có thể chọn nhầm cột chữ (Fix string to float error)
            all_numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            features = [f for f in features if f in all_numeric_cols]
        
        if len(features) < 2:
            return {"error": "Cần ít nhất 2 cột số để phân cụm. Hãy chọn các cột như Giá doanh thu, Số lượng... Dữ liệu hiện tại không đủ cột số."}
        
        # Prepare data
        data = df[features].dropna()
        if len(data) < 10:
            return {"error": "Cần ít nhất 10 dòng dữ liệu hợp lệ để phân cụm."}
        
        # Standardize
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data)
        
        # Elbow method — tìm K tối ưu
        max_k = min(max_k, len(data) - 1, 10)
        if max_k < 2:
            max_k = 2
        
        inertias = []
        silhouette_scores = []
        K_range = range(2, max_k + 1)
        
        for k in K_range:
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            km.fit(scaled_data)
            inertias.append(km.inertia_)
            score = silhouette_score(scaled_data, km.labels_)
            silhouette_scores.append(score)
        
        # Tìm K bằng Elbow: điểm có "khuỷu" lớn nhất
        optimal_k = _find_elbow(list(K_range), inertias)
        
        # Nếu silhouette score cho kết quả tốt hơn, ưu tiên
        best_silhouette_k = list(K_range)[np.argmax(silhouette_scores)]
        if silhouette_scores[best_silhouette_k - 2] > silhouette_scores[optimal_k - 2] + 0.05:
            optimal_k = best_silhouette_k
        
        # Chạy KMeans với K tối ưu
        final_km = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
        labels = final_km.fit_predict(scaled_data)
        
        df_result = data.copy()
        df_result['Cluster'] = labels
        
        # Thống kê từng cluster
        cluster_stats = []
        for c in range(optimal_k):
            cluster_data = df_result[df_result['Cluster'] == c]
            stat = {"cluster": c, "count": len(cluster_data)}
            for f in features:
                stat[f"{f}_mean"] = round(float(cluster_data[f].mean()), 2)
                stat[f"{f}_std"] = round(float(cluster_data[f].std()), 2) if len(cluster_data) > 1 else 0
            cluster_stats.append(stat)
        
        return {
            "method": "ml_cluster",
            "optimal_k": optimal_k,
            "features_used": features,
            "cluster_stats": cluster_stats,
            "silhouette_score": round(float(max(silhouette_scores)), 3),
            "data": df_result.to_dict('records'),
            "error": None
        }
        
    except Exception as e:
        return {"error": f"Lỗi clustering: {str(e)}\n{traceback.format_exc()}"}


def _find_elbow(k_values: list, inertias: list) -> int:
    """Tìm điểm khuỷu tay (elbow point) bằng phương pháp khoảng cách tối đa."""
    if len(k_values) <= 2:
        return k_values[0]
    
    # Đường thẳng từ điểm đầu đến điểm cuối
    p1 = np.array([k_values[0], inertias[0]])
    p2 = np.array([k_values[-1], inertias[-1]])
    
    # Normalize
    k_norm = (np.array(k_values) - k_values[0]) / (k_values[-1] - k_values[0]) if k_values[-1] != k_values[0] else np.zeros(len(k_values))
    inertia_range = inertias[0] - inertias[-1]
    i_norm = (np.array(inertias) - inertias[-1]) / inertia_range if inertia_range != 0 else np.zeros(len(inertias))
    
    # Khoảng cách từ mỗi điểm đến đường thẳng
    distances = []
    for i in range(len(k_values)):
        point = np.array([k_norm[i], i_norm[i]])
        line_start = np.array([0, 1])
        line_end = np.array([1, 0])
        
        line_vec = line_end - line_start
        point_vec = point - line_start
        line_len = np.linalg.norm(line_vec)
        
        if line_len == 0:
            distances.append(0)
        else:
            distance = abs(np.cross(line_vec, point_vec)) / line_len
            distances.append(distance)
    
    return k_values[np.argmax(distances)]


def execute_ml_forecast(df: pd.DataFrame, date_col: str = None, value_col: str = None, periods: int = 30) -> Dict[str, Any]:
    """
    Time series forecasting bằng Linear Regression + trend projection.
    """
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    
    try:
        # Auto-detect cột ngày và giá trị nếu không được chỉ định
        if not date_col:
            for col in df.columns:
                if df[col].dtype in ['datetime64[ns]', 'object']:
                    try:
                        pd.to_datetime(df[col])
                        date_col = col
                        break
                    except Exception:
                        continue
        
        if not date_col:
            return {"error": "Không tìm thấy cột ngày tháng trong dữ liệu. Cần cột ngày để dự báo."}
        
        if not value_col:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                # Ưu tiên cột có tên chứa 'amount', 'revenue', 'sales', 'doanh_thu'
                priority = ['amount', 'revenue', 'sales', 'doanh_thu', 'total', 'price', 'gia']
                for col in numeric_cols:
                    if any(p in col.lower() for p in priority):
                        value_col = col
                        break
                if not value_col:
                    value_col = numeric_cols[0]
            else:
                return {"error": "Không tìm thấy cột số để dự báo."}
        
        # Prepare data
        df_ts = df[[date_col, value_col]].copy()
        df_ts[date_col] = pd.to_datetime(df_ts[date_col], errors='coerce')
        df_ts = df_ts.dropna()
        
        if len(df_ts) < 5:
            return {"error": "Cần ít nhất 5 dòng dữ liệu thời gian để dự báo."}
        
        # Aggregate by date
        df_ts = df_ts.groupby(date_col)[value_col].sum().reset_index()
        df_ts = df_ts.sort_values(date_col)
        
        # Create numeric index for regression
        df_ts['day_index'] = (df_ts[date_col] - df_ts[date_col].min()).dt.days
        
        X = df_ts['day_index'].values.reshape(-1, 1)
        y = df_ts[value_col].values
        
        # Linear Regression
        lr = LinearRegression()
        lr.fit(X, y)
        
        # Polynomial Regression (degree 2) for better fit
        poly = PolynomialFeatures(degree=2)
        X_poly = poly.fit_transform(X)
        lr_poly = LinearRegression()
        lr_poly.fit(X_poly, y)
        
        # R² scores
        r2_linear = lr.score(X, y)
        r2_poly = lr_poly.score(X_poly, y)
        
        # Use better model
        use_poly = r2_poly > r2_linear + 0.05
        
        # Generate future dates
        last_date = df_ts[date_col].max()
        last_day = int(df_ts['day_index'].max())
        future_days = np.arange(last_day + 1, last_day + periods + 1).reshape(-1, 1)
        future_dates = [last_date + pd.Timedelta(days=int(d - last_day)) for d in future_days.flatten()]
        
        if use_poly:
            future_X_poly = poly.transform(future_days)
            predictions = lr_poly.predict(future_X_poly)
            historical_pred = lr_poly.predict(X_poly)
            model_name = "Polynomial Regression (degree 2)"
            r2_score = r2_poly
        else:
            predictions = lr.predict(future_days)
            historical_pred = lr.predict(X)
            model_name = "Linear Regression"
            r2_score = r2_linear
        
        # Ensure no negative predictions for inherently positive values
        predictions = np.maximum(predictions, 0)
        
        # Confidence interval (simple approach: ±1.96 * std of residuals)
        residuals = y - historical_pred
        std_residual = np.std(residuals)
        upper_bound = predictions + 1.96 * std_residual
        lower_bound = np.maximum(predictions - 1.96 * std_residual, 0)
        
        # Prepare forecast data
        forecast_data = []
        for i, (d, pred, ub, lb) in enumerate(zip(future_dates, predictions, upper_bound, lower_bound)):
            forecast_data.append({
                "date": d.strftime('%Y-%m-%d'),
                value_col: round(float(pred), 2),
                "upper_bound": round(float(ub), 2),
                "lower_bound": round(float(lb), 2)
            })
        
        # Summary stats
        total_forecast = float(np.sum(predictions))
        avg_forecast = float(np.mean(predictions))
        trend = "TĂNG" if predictions[-1] > predictions[0] else "GIẢM"
        growth_pct = ((predictions[-1] - predictions[0]) / (predictions[0] + 1e-10)) * 100
        
        return {
            "method": "ml_forecast",
            "model": model_name,
            "r2_score": round(r2_score, 4),
            "periods": periods,
            "date_col": date_col,
            "value_col": value_col,
            "trend": trend,
            "growth_percent": round(float(growth_pct), 2),
            "total_forecast": round(total_forecast, 2),
            "avg_forecast": round(avg_forecast, 2),
            "forecast_data": forecast_data,
            "error": None
        }
        
    except Exception as e:
        return {"error": f"Lỗi forecast: {str(e)}\n{traceback.format_exc()}"}


def execute_ml_anomaly(df: pd.DataFrame, features: list = None, contamination: float = 0.1) -> Dict[str, Any]:
    """
    Phát hiện anomaly bằng Isolation Forest.
    """
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    
    try:
        # Auto-detect hoặc lọc numeric features
        if not features:
            features = df.select_dtypes(include=[np.number]).columns.tolist()
        else:
            # Lọc lại features do AI có thể chọn nhầm cột chữ (Fix string to float error)
            all_numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            features = [f for f in features if f in all_numeric_cols]
        
        if len(features) < 1:
            return {"error": "Cần ít nhất 1 cột số để phát hiện bất thường. Hãy chọn các cột như Giá doanh thu, Số lượng... Dữ liệu hiện tại không đủ cột số."}
        
        data = df[features].dropna()
        if len(data) < 10:
            return {"error": "Cần ít nhất 10 dòng dữ liệu hợp lệ."}
        
        # Standardize
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data)
        
        # Isolation Forest
        iso_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        predictions = iso_forest.fit_predict(scaled_data)
        scores = iso_forest.decision_function(scaled_data)
        
        # -1 = anomaly, 1 = normal
        df_result = data.copy()
        df_result['Anomaly'] = ['Bất thường' if p == -1 else 'Bình thường' for p in predictions]
        df_result['Anomaly_Score'] = np.round(scores, 4)
        
        anomaly_count = int((predictions == -1).sum())
        normal_count = int((predictions == 1).sum())
        
        # Anomaly details
        anomaly_rows = df_result[df_result['Anomaly'] == 'Bất thường'].copy()
        anomaly_details = anomaly_rows.sort_values('Anomaly_Score').head(20).to_dict('records')
        
        return {
            "method": "ml_anomaly",
            "total_rows": len(data),
            "anomaly_count": anomaly_count,
            "normal_count": normal_count,
            "anomaly_rate": round(anomaly_count / len(data) * 100, 2),
            "features_used": features,
            "anomaly_details": anomaly_details,
            "data": df_result.to_dict('records'),
            "error": None
        }
        
    except Exception as e:
        return {"error": f"Lỗi anomaly detection: {str(e)}\n{traceback.format_exc()}"}


# ============================================================
# 4. RESULT FORMATTING — Format kết quả ML cho AI insight
# ============================================================

def format_ml_result_for_insight(ml_result: Dict[str, Any], question: str) -> str:
    """Tạo summary text từ kết quả ML để gửi cho Gemini phân tích insight."""
    method = ml_result.get("method", "")
    
    if method == "ml_cluster":
        stats = ml_result.get("cluster_stats", [])
        text = f"Kết quả phân cụm K-Means (K={ml_result.get('optimal_k')}, Silhouette={ml_result.get('silhouette_score')}):\n"
        for s in stats:
            text += f"- Cụm {s['cluster']}: {s['count']} phần tử\n"
            for k, v in s.items():
                if k not in ['cluster', 'count']:
                    text += f"  + {k}: {v}\n"
        return text
    
    elif method == "ml_forecast":
        text = f"Kết quả dự báo ({ml_result.get('model')}, R²={ml_result.get('r2_score')}):\n"
        text += f"- Xu hướng: {ml_result.get('trend')}\n"
        text += f"- Tăng/giảm: {ml_result.get('growth_percent')}%\n"
        text += f"- Tổng dự báo {ml_result.get('periods')} ngày: {ml_result.get('total_forecast')}\n"
        text += f"- Trung bình/ngày: {ml_result.get('avg_forecast')}\n"
        forecast_sample = ml_result.get("forecast_data", [])[:5]
        text += f"- 5 ngày đầu dự báo: {json.dumps(forecast_sample, ensure_ascii=False)}\n"
        return text
    
    elif method == "ml_anomaly":
        text = f"Kết quả phát hiện bất thường (Isolation Forest):\n"
        text += f"- Tổng dòng: {ml_result.get('total_rows')}\n"
        text += f"- Bất thường: {ml_result.get('anomaly_count')} ({ml_result.get('anomaly_rate')}%)\n"
        text += f"- Bình thường: {ml_result.get('normal_count')}\n"
        anomaly_sample = ml_result.get("anomaly_details", [])[:5]
        text += f"- Top 5 bất thường nhất: {json.dumps(anomaly_sample, ensure_ascii=False, default=str)}\n"
        return text
    
    return str(ml_result)

def analyze_gsheet_with_gemini(df: pd.DataFrame, user_prompt: str, api_key: str) -> str:
    """
    Decoupled function to run automated AI analysis on a dataframe (GSheet data).
    Used by background tasks without requiring HTTP request context.
    """
    try:
        # Tóm tắt dữ liệu cơ bản để giới hạn token
        stats = df.describe().to_dict()
        columns = df.columns.tolist()
        sample_data = df.head(5).to_dict(orient='records')
        row_count = len(df)
        
        system_prompt = f"""Bạn là chuyên gia phân tích dữ liệu AI tự động. 
Dữ liệu: Google Sheet. Yêu cầu: "{user_prompt}"

THÔNG TIN DỮ LIỆU:
- Số dòng: {row_count}
- Cột: {columns}
- Thống kê: {stats}
- Mẫu: {sample_data}

QUY TẮC PHẢN HỒI (RẤT QUAN TRỌNG):
- KHÔNG sử dụng định dạng Markdown (Không dùng **, *, #, __, [ ]...).
- Chỉ trả về TEXT THUẦN (Plain Text).
- Trình bày rõ ràng bằng cách xuống dòng (Enter).
- Nội dung: KHÔNG chỉ đơn thuần liệt kê dữ liệu. PHẢI phân tích và giải thích ý nghĩa của các con số này đối với doanh nghiệp (tốt/xấu, nguyên nhân, hệ quả). Đưa ra nhận xét chuyên nghiệp và súc tích.
"""
        from .ai_utils import get_generative_model
        model = get_generative_model()
        response = model.generate_content(system_prompt)
        return response.text.strip()
    except Exception as e:
        return f"Lỗi phân tích nền: {str(e)}"
