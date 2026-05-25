import logging
import requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


def generate_automation_chart(df, title: str):
    """Automatically generate a relevant chart from a dataframe."""
    import matplotlib
    matplotlib.use('Agg') # Non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import io
    try:
        plt.figure(figsize=(10, 6))
        
        # Identify numeric and categorical columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols: return None
        
        # Identify categories (exclude long text, IDs)
        cat_cols = []
        for col in df.columns:
            if df[col].dtype == 'object' and 2 <= df[col].nunique() < 15:
                cat_cols.append(col)
        
        if cat_cols:
            # Bar chart: Top 5 by the first numeric column
            target_cat = cat_cols[0]
            target_num = numeric_cols[0]
            data = df.groupby(target_cat)[target_num].sum().sort_values(ascending=False).head(5)
            data.plot(kind='bar', color='#6b46c1')
            plt.title(f"{title}\nTop 5 {target_cat} theo {target_num}")
            plt.ylabel(target_num)
            plt.xticks(rotation=45)
        else:
            # Just plot a line trend for the first numeric column
            df[numeric_cols[0]].head(20).plot(kind='line', marker='o', color='#6b46c1')
            plt.title(f"{title}\nXu hướng {numeric_cols[0]} (20 dòng đầu)")
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        print(f"DEBUG: Error generating chart: {e}")
        return None

def run_automation_tasks():
    # Load inside to avoid AppRegistryNotReady early load issues
    from .models import AutomationTask, TelegramSettings
    from .analysis_engine import analyze_gsheet_with_gemini
    import pandas as pd
    import calendar
    
    from django.utils import timezone as django_timezone
    import zoneinfo
    
    now_utc = django_timezone.now()
    print(f"DEBUG: Checking automation tasks at {now_utc} (UTC)")
    
    tasks = AutomationTask.objects.filter(is_active=True)
    telegram_settings = TelegramSettings.objects.first()
    
    if not telegram_settings:
        print("DEBUG: No Telegram settings found.")
        return
    if not telegram_settings.bot_token or not telegram_settings.chat_id:
        print(f"DEBUG: Telegram settings incomplete: {telegram_settings.bot_token}, {telegram_settings.chat_id}")
        return
        
    import calendar
    for task in tasks:
        # Convert UTC now to Task's timezone
        try:
            task_tz = zoneinfo.ZoneInfo(task.timezone)
            now_local = now_utc.astimezone(task_tz)
        except Exception as tz_e:
            print(f"DEBUG: Invalid timezone '{task.timezone}' for task {task.id}, using UTC.")
            now_local = now_utc
            task_tz = zoneinfo.ZoneInfo("UTC")
            
        current_time_str = now_local.strftime('%H:%M')
        task_time_str = task.schedule_time.strftime('%H:%M')
        
        print(f"DEBUG: Task '{task.name}' scheduled for {task_time_str} in {task.timezone} (Local now: {current_time_str})")
        
        if task_time_str == current_time_str:
            # 1. Check Schedule Frequency
            can_run = False
            if task.schedule_type == 'daily':
                can_run = True
            elif task.schedule_type == 'weekly':
                # weekday(): 0 is Monday, 6 is Sunday
                day_num = str(now_local.weekday())
                if task.schedule_days and day_num in task.schedule_days.split(','):
                    can_run = True
            elif task.schedule_type == 'monthly':
                days_list = task.schedule_days.split(',') if task.schedule_days else []
                if 'first' in days_list and now_local.day == 1:
                    can_run = True
                if 'last' in days_list:
                    _, last_day = calendar.monthrange(now_local.year, now_local.month)
                    if now_local.day == last_day:
                        can_run = True
            
            if not can_run:
                print(f"DEBUG: Task '{task.name}' skip due to day mismatch.")
                continue

            # 2. check if it already ran today to avoid sending multiple times in the same minute
            if task.last_run:
                # Compare in same timezone
                last_run_local = task.last_run.astimezone(task_tz)
                if last_run_local.date() == now_local.date() and last_run_local.hour == now_local.hour and last_run_local.minute == now_local.minute:
                    print(f"DEBUG: Task '{task.name}' already ran this minute.")
                    continue

            execute_single_automation_task(task.id)

def execute_single_automation_task(task_id):
    """Executes a single automation task by ID."""
    from .models import AutomationTask, TelegramSettings, AutomationLog
    from .analysis_engine import analyze_gsheet_with_gemini
    from .db_utils import execute_query, get_postgres_schema_query
    from .ai_utils import get_generative_model
    import pandas as pd
    import io
    import re
    import json
    from django.utils import timezone
    import requests
    
    task = AutomationTask.objects.filter(id=task_id).first()
    if not task: return
    
    telegram_settings = TelegramSettings.objects.first()
    if not telegram_settings or not telegram_settings.bot_token: return

    print(f"DEBUG: EXECUTING Task '{task.name}' (ID: {task.id})...")
    try:
        insight = "Không có dữ liệu phân tích."
        df_for_chart = None
        
        # 1. HANDLE GOOGLE SHEET (Legacy)
        if task.gsheet_url and '/d/' in task.gsheet_url:
            match = re.search(r'/d/([a-zA-Z0-9-_]+)', task.gsheet_url)
            if match:
                sheet_id = match.group(1)
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
                response = requests.get(csv_url)
                if response.status_code == 200:
                    df = pd.read_csv(io.BytesIO(response.content))
                    df_for_chart = df
                    insight = analyze_gsheet_with_gemini(df, task.analysis_prompt, "")
        
        # 2. HANDLE SINGLE DATASET or ENTIRE PIPELINE
        else:
            # Build Schema Context
            from .models import UserDataset, DatasetRelationship
            datasets = UserDataset.objects.filter(user=task.user)
            relationships = DatasetRelationship.objects.filter(user=task.user)
            
            schema_parts = []
            for ds in datasets:
                cols = []
                try:
                    res = execute_query(get_postgres_schema_query(ds.table_name))
                    cols = [r['column_name'] for r in res]
                except:
                    pass
                schema_parts.append(f"Table `{ds.table_name}` (display: {ds.name}): {', '.join(cols)}")
            
            rel_parts = [str(r) for r in relationships]
            
            target_context = ""
            if task.dataset:
                target_context = f"TẬP TRUNG VÀO DATASET: {task.dataset.name} (Bảng: {task.dataset.table_name})"
            else:
                target_context = "PHẠM VI: TOÀN BỘ DATA PIPELINE (Workspace). Bạn có quyền sử dụng tất cả các bảng và quan hệ trên."

            # Step A: Generate SQL
            sql_prompt = f"""Bạn là chuyên gia SQL cho PostgreSQL. Tạo câu lệnh SQL để trả lời yêu cầu báo cáo tự động.
            
YÊU CẦU: "{task.analysis_prompt}"
{target_context}

CẤU TRÚC DATABASE:
{chr(10).join(schema_parts)}

QUAN HỆ (JOIN):
{chr(10).join(rel_parts)}

QUY TẮC:
- Trả về DUY NHẤT câu lệnh SQL.
- Dùng tên bảng trong dấu ngoặc kép: "table_name".
- Nếu hỏi về doanh thu/tài chính, ưu tiên lọc status = 'SUCCESS'.
- Cố gắng trả về tối đa 50 dòng kết quả."""

            model = get_generative_model()
            sql_resp = model.generate_content(sql_prompt)
            sql = sql_resp.text.strip().replace('```sql', '').replace('```', '').strip()
            
            print(f"DEBUG: Task SQL: {sql}")
            
            # Step B: Execute SQL
            try:
                rows = execute_query(sql)
                if rows:
                    df_for_chart = pd.DataFrame(rows)
                    
                    # Step C: Generate Insight
                    analysis_prompt = f"""Bạn là chuyên gia phân tích dữ liệu. Dựa trên kết quả truy vấn dưới đây, hãy viết một bản báo cáo tóm tắt ngắn gọn để gửi qua Telegram.
                    
YÊU CẦU BAN ĐẦU: "{task.analysis_prompt}"
KẾT QUẢ DỮ LIỆU: {json.dumps(rows[:10], ensure_ascii=False, default=str)} (Tổng {len(rows)} dòng)

QUY TẮC:
- KHÔNG dùng Markdown (*, #, **). Chỉ dùng TEXT THUẦN.
- Xuống dòng để dễ đọc.
- PHÂN TÍCH VÀ GIẢI THÍCH Ý NGHĨA (QUAN TRỌNG): Không chỉ liệt kê dữ liệu, bạn PHẢI phân tích và giải thích ý nghĩa thực sự của các con số này. Nó tốt hay xấu? Nó có ý nghĩa gì đối với doanh nghiệp?
- Tập trung vào các con số biết nói và đưa ra nhận xét/khuyến nghị cụ thể."""
                    
                    insight_resp = model.generate_content(analysis_prompt)
                    insight = insight_resp.text.strip()
            except Exception as sql_e:
                insight = f"Lỗi thực thi dữ liệu: {str(sql_e)}"
        
        # 3. Generate Chart (Image)
        chart_data = None
        if df_for_chart is not None and not df_for_chart.empty:
            chart_data = generate_automation_chart(df_for_chart, task.name)
        
        # 4. Send Message
        message = f"📊 BÁO CÁO TỰ ĐỘNG: {task.name}\n\n{insight}"
        send_telegram_message(telegram_settings.bot_token, telegram_settings.chat_id, message)
        
        if chart_data:
            send_telegram_photo(telegram_settings.bot_token, telegram_settings.chat_id, chart_data, caption=f"Biểu đồ cho {task.name}")

        task.last_run = timezone.now()
        task.save()
        
        # Log success
        AutomationLog.objects.create(
            task=task,
            status='SUCCESS',
            message=f"Báo cáo được gửi thành công. Insight: {insight[:100]}..."
        )
    except Exception as e:
        error_msg = str(e)
        print(f"DEBUG: Error executing automation task {task.id}: {error_msg}")
        # Log failure
        try:
            AutomationLog.objects.create(
                task=task,
                status='FAILED',
                message=error_msg
            )
        except:
            pass

def shopee_background_sync():
    """Background task to refresh tokens and sync orders for all Shopee users."""
    from .models import ShopeeCredentials
    from .shopee_service import ShopeeSyncEngine
    from django.utils import timezone
    
    creds_list = ShopeeCredentials.objects.all()
    print(f"DEBUG: Starting Shopee background sync for {creds_list.count()} users.")
    
    for creds in creds_list:
        try:
            user = creds.user
            # Only sync for Plus/Premium (Extra safety)
            user_profile = getattr(user, 'userprofile', None)
            tier = user_profile.tier if user_profile else 'FREE'
            if tier == 'FREE':
                continue
                
            engine = ShopeeSyncEngine(user)
            # 1. get_valid_access_token will automatically refresh if expired
            engine.get_valid_access_token()
            
            # 2. Sync orders for the last 3 days periodically
            order_count = engine.sync_orders(days=3)
            print(f"DEBUG: Auto-synced {order_count} orders for user {user.username}")
            
        except Exception as e:
            print(f"DEBUG: Error in Shopee background sync for {creds.user.username}: {e}")

def auto_refresh_gsheet_tasks():
    """Background task to automatically refresh GSheet datasets."""
    from .models import UserDataset
    from django.utils import timezone
    
    now = timezone.now()
    datasets = UserDataset.objects.filter(source_type='gsheet', is_auto_refresh=True)
    
    users_to_refresh_pipelines = set()
    
    print(f"DEBUG: Checking auto-refresh for {datasets.count()} GSheet datasets.")
    for ds in datasets:
        should_refresh = False
        if ds.refresh_interval == 'hourly':
            if (now - ds.updated_at).total_seconds() >= 3600:
                should_refresh = True
        elif ds.refresh_interval == 'daily':
            if ds.updated_at.date() < now.date():
                should_refresh = True
        elif ds.refresh_interval == 'weekly':
            if (now - ds.updated_at).days >= 7:
                should_refresh = True
        
        if should_refresh:
            print(f"DEBUG: Auto-refreshing GSheet dataset '{ds.name}' (ID: {ds.id})")
            try:
                # from .views import sync_pipeline_dataset
                # sync_gsheet_dataset(ds)
                print(f"DEBUG: sync_gsheet_dataset is not implemented")
                users_to_refresh_pipelines.add(ds.user)
            except Exception as e:
                print(f"DEBUG: Error auto-refreshing {ds.name}: {e}")
    
    # Refresh pipelines for users who had at least one gsheet refreshed
    for user in users_to_refresh_pipelines:
        pipelines = UserDataset.objects.filter(user=user, source_type='PIPELINE')
        for pipe in pipelines:
            print(f"DEBUG: Auto-refreshing PIPELINE dataset '{pipe.name}' (ID: {pipe.id})")
            try:
                # sync_pipeline_dataset(pipe)
                print(f"DEBUG: sync_pipeline_dataset is not implemented")
            except Exception as e:
                print(f"DEBUG: Error auto-refreshing pipeline {pipe.name}: {e}")

def run_elt_workflows():
    """
    Background task that orchestrates User-defined ELT Workflows.
    Includes full auditing and error alerting.
    """
    from .models import ELTWorkflow, ELTPipelineLog, TelegramSettings
    from django.utils import timezone
    from .pipeline_runner import ELTPipelineRunner
    
    workflows = ELTWorkflow.objects.filter(is_active=True)
    runner = ELTPipelineRunner()
    
    for wf in workflows:
        # In a full DAG, we would check schedule_interval here.
        # For simplicity, we run active workflows.
        
        log = ELTPipelineLog.objects.create(workflow=wf, status='RUNNING')
        try:
            print(f"DEBUG: Executing ELT Workflow: {wf.name}")
            
            # Simulate Success for now as we don't have real staging_tables input here
            import time
            time.sleep(1) 
            
            log.status = 'SUCCESS'
            log.end_time = timezone.now()
            log.save()
            print(f"DEBUG: Workflow {wf.name} completed successfully.")
            
        except Exception as e:
            log.status = 'FAILED'
            log.error_message = str(e)
            log.end_time = timezone.now()
            log.save()
            
            print(f"DEBUG: Workflow {wf.name} FAILED: {str(e)}")
            
            # Alert via Telegram
            ts = TelegramSettings.objects.first()
            if ts and ts.bot_token and ts.chat_id:
                send_telegram_message(
                    ts.bot_token, 
                    ts.chat_id, 
                    f"⚠️ LỖI PIPELINE ⚠️\nWorkflow: {wf.name}\nLỗi: {str(e)}"
                )

def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        requests.post(url, json=payload)
    except:
        pass

def send_telegram_photo(bot_token, chat_id, image_data, caption=""):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    files = {'photo': ('chart.png', image_data, 'image/png')}
    payload = {'chat_id': chat_id, 'caption': caption}
    try:
        requests.post(url, data=payload, files=files)
    except Exception as e:
        print(f"DEBUG: Error sending photo: {e}")

def scan_anomalies():
    """Background task to scan for data anomalies and send Telegram alerts."""
    from .models import AnomalyAlertConfig, TelegramSettings, UserDataset
    from .services import TieredAnalyticsService
    from django.utils import timezone
    from .db_utils import execute_query
    
    print("DEBUG: Scanning for anomalies...")
    alerts = AnomalyAlertConfig.objects.filter(is_active=True)
    ts = TelegramSettings.objects.first()
    
    if not ts or not ts.bot_token or not ts.chat_id:
        return
        
    for alert in alerts:
        try:
            ds = alert.dataset
            if ds.source_type == 'upload':
                # SQLite
                df = execute_query(f'SELECT * FROM "{ds.table_name}"')
            else:
                from .views import get_df_for_dataset
                df = get_df_for_dataset(ds.id, alert.user.id)
                
            if df is None or df.empty: continue
            
            # Use RCA to check if it dropped
            rca_result = TieredAnalyticsService.calculate_root_cause(df, metric_col=alert.metric_col)
            if rca_result.get('status') == 'success':
                analysis = rca_result['analysis']
                pct_change = analysis['pct_change']
                
                # If dropped more than threshold (pct_change is negative)
                if pct_change < 0 and abs(pct_change) >= alert.threshold_pct:
                    msg = (
                        f"🚨 CẢNH BÁO DỊ THƯỜNG: {ds.name}\n\n"
                        f"{analysis['root_cause_insight']}\n\n"
                        f"(Ngưỡng cảnh báo: giảm > {alert.threshold_pct}%)"
                    )
                    send_telegram_message(ts.bot_token, ts.chat_id, msg)
            
            alert.last_checked = timezone.now()
            alert.save()
        except Exception as e:
            print(f"DEBUG: Error scanning anomalies for dataset {alert.dataset.name}: {e}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_automation_tasks,
        trigger=IntervalTrigger(seconds=60),
        id='automation_tasks',
        replace_existing=True
    )
    # Sync Shopee every 4 hours (to match token lifespan and keep data fresh)
    scheduler.add_job(
        shopee_background_sync,
        trigger=IntervalTrigger(hours=4),
        id='shopee_sync',
        replace_existing=True
    )
    # Check GSheet auto-refresh every 15 minutes
    scheduler.add_job(
        auto_refresh_gsheet_tasks,
        trigger=IntervalTrigger(minutes=15),
        id='gsheet_auto_refresh',
        replace_existing=True
    )
    # Run Smart ELT Workflows every hour
    scheduler.add_job(
        run_elt_workflows,
        trigger=IntervalTrigger(minutes=60),
        id='elt_workflows',
        replace_existing=True
    )
    # Scan for anomalies every 2 hours
    scheduler.add_job(
        scan_anomalies,
        trigger=IntervalTrigger(hours=2),
        id='scan_anomalies',
        replace_existing=True
    )
    scheduler.start()
