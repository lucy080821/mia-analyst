"""
Replace ml_forecast and ml_anomaly handlers with updated version using _build_insight_prompt.
"""
import re

with open('analytics/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ── Replace _handle_ml_forecast ─────────────────────────────
old_forecast_sig = 'def _handle_ml_forecast(request, question, table_name, params,\n                       context_text, tier, tier_instructions, model, api_key):'
new_forecast = '''def _handle_ml_forecast(request, question, table_name, params,
                       context_text, tier, tier_instructions, model, api_key,
                       extra_ctx=None):
    """Xử lý dự báo time series."""
    extra_ctx = extra_ctx or {}
    col_labels = extra_ctx.get('col_labels', {})
    quality_alerts = extra_ctx.get('quality_alerts', [])
    df_ctx = extra_ctx.get('df')

    try:
        from django.db import connection
        df = df_ctx if df_ctx is not None else pd.read_sql(f"SELECT * FROM {table_name}", connection)
    except Exception as e:
        return JsonResponse({"error": f"Lỗi đọc dữ liệu: {str(e)}"}, status=500)

    date_col = params.get("date_col") if params else None
    value_col = params.get("value_col") if params else None
    periods = params.get("periods", 30) if params else 30

    ml_result = execute_ml_forecast(df, date_col=date_col, value_col=value_col, periods=periods)
    if ml_result.get("error"):
        return JsonResponse({"error": ml_result["error"]}, status=500)

    result_text = format_ml_result_for_insight(ml_result, question)
    insight_prompt = _build_insight_prompt(
        method='ml_forecast', question=question, result_text=result_text,
        tier=tier, tier_instructions=tier_instructions, context_text=context_text,
        col_labels=col_labels, quality_alerts=quality_alerts
    )
    try:
        resp = model.generate_content(insight_prompt)
        explanation = resp.text.strip() if resp.text else "Dự báo hoàn tất."
    except Exception:
        explanation = f"Dự báo hoàn tất ({ml_result.get('model')})\\n{result_text}"

    data = ml_result.get("forecast_data", [])
    columns = list(data[0].keys()) if data else []
    save_chat_history(request.user, question, explanation, 'table', {"data": data, "columns": columns})

    return JsonResponse({
        "reply": explanation, "type": "table", "method": "ml_forecast",
        "data": data, "columns": columns,
        "ml_info": {
            "model": ml_result.get("model"),
            "r2_score": ml_result.get("r2_score"),
            "trend": ml_result.get("trend"),
            "growth_percent": ml_result.get("growth_percent"),
            "periods": ml_result.get("periods")
        },
        "summary": {"question": question, "row_count": len(data)}
    })'''

if old_forecast_sig in content:
    # Find full old function
    idx_start = content.find(old_forecast_sig)
    idx_end = content.find('\ndef _handle_ml_anomaly', idx_start)
    if idx_end > 0:
        content = content[:idx_start] + new_forecast + '\n\n\n' + content[idx_end+1:]
        print("Replaced _handle_ml_forecast OK")
    else:
        print("Could not find end of forecast handler")
else:
    print("old_forecast_sig not found - may already be updated")
    # Try to find by partial match
    idx = content.find('def _handle_ml_forecast')
    if idx >= 0:
        print("Found at:", idx)
        print(repr(content[idx:idx+200]))

# ── Replace _handle_ml_anomaly ───────────────────────────────
old_anomaly_sig = 'def _handle_ml_anomaly(request, question, table_name, params,\n                      context_text, tier, tier_instructions, model, api_key):'
new_anomaly = '''def _handle_ml_anomaly(request, question, table_name, params,
                      context_text, tier, tier_instructions, model, api_key,
                      extra_ctx=None):
    """Xử lý phát hiện bất thường."""
    extra_ctx = extra_ctx or {}
    col_labels = extra_ctx.get('col_labels', {})
    quality_alerts = extra_ctx.get('quality_alerts', [])
    df_ctx = extra_ctx.get('df')

    try:
        from django.db import connection
        df = df_ctx if df_ctx is not None else pd.read_sql(f"SELECT * FROM {table_name}", connection)
    except Exception as e:
        return JsonResponse({"error": f"Lỗi đọc dữ liệu: {str(e)}"}, status=500)

    features = params.get("features", []) if params else []
    features = [f for f in features if f in df.columns]
    ml_result = execute_ml_anomaly(df, features=features if features else None)

    if ml_result.get("error"):
        return JsonResponse({"error": ml_result["error"]}, status=500)

    result_text = format_ml_result_for_insight(ml_result, question)
    insight_prompt = _build_insight_prompt(
        method='ml_anomaly', question=question, result_text=result_text,
        tier=tier, tier_instructions=tier_instructions, context_text=context_text,
        col_labels=col_labels, quality_alerts=quality_alerts
    )
    try:
        resp = model.generate_content(insight_prompt)
        explanation = resp.text.strip() if resp.text else "Phát hiện bất thường hoàn tất."
    except Exception:
        explanation = f"Phát hiện bất thường: {ml_result.get('anomaly_count')} dòng bất thường\\n{result_text}"

    data = ml_result.get("anomaly_details", [])
    columns = list(data[0].keys()) if data else []
    save_chat_history(request.user, question, explanation, 'table', {"data": data, "columns": columns})

    return JsonResponse({
        "reply": explanation, "type": "table", "method": "ml_anomaly",
        "data": data, "columns": columns,
        "ml_info": {
            "total_rows": ml_result.get("total_rows"),
            "anomaly_count": ml_result.get("anomaly_count"),
            "anomaly_rate": ml_result.get("anomaly_rate"),
            "features_used": ml_result.get("features_used")
        },
        "summary": {"question": question, "row_count": len(data)}
    })'''

if old_anomaly_sig in content:
    idx_start = content.find(old_anomaly_sig)
    idx_end = content.find('\ndef _generate_ai_insight', idx_start)
    if idx_end > 0:
        content = content[:idx_start] + new_anomaly + '\n\n\n' + content[idx_end+1:]
        print("Replaced _handle_ml_anomaly OK")
    else:
        print("Could not find end of anomaly handler")
else:
    print("old_anomaly_sig not found")
    idx = content.find('def _handle_ml_anomaly')
    if idx >= 0:
        print("Found at:", idx, "sig:", repr(content[idx:idx+200]))

with open('analytics/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done writing views.py")
