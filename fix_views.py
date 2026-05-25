"""Script dọn dẹp views.py sau khi multi_replace để lại residual code."""
import re

with open('analytics/views.py', 'rb') as f:
    raw = f.read()

content = raw.decode('utf-8', errors='replace')

# ── Fix 1: residual after python handler ──────────────────────
# Pattern: '})  # Format result tex# ============...'
content = re.sub(
    r'\}\)  # Format result tex(# ============================================================\n# HANDLER: Multi-Chart Dashboard)',
    r'})\n\n\n\1',
    content
)

# ── Fix 2: residual inside ml_cluster handler ─────────────────
# Pattern: '    })        return JsonResponse...'
# Find the block: ends with the duplicate old code
bad_pattern = (
    r'(\}\)  # ml_cluster old residual|'
    r'    \}\)        return JsonResponse\(\{\"error\": f\"Lỗi đọc dữ liệu.*?\}\), status=500\)\n'
    r'    \n'
    r'    features = params\.get.*?    # Validate features exist in df\n'
    r'    features = \[f for f in features if f in df\.columns\]\n'
    r'    \n'
    r'    ml_result = execute_ml_clustering.*?\}\)\n\n\n)'
)

# More targeted: remove the duplicate code after the new _handle_ml_clustering returns
# We know the new code returns properly with JsonResponse, then old code leaked
# Find and remove the duplicate block
marker_start = '    })        return JsonResponse({"error": f"Lỗi đọc dữ liệu: {str(e)}'
marker_end_old = '    ml_result = execute_ml_clustering(df, features=features if features else None)'

idx_start = content.find(marker_start)
if idx_start > 0:
    # Find what comes after — look for the second occurrence of ml_clustering call
    idx_end = content.find(marker_end_old, idx_start)
    if idx_end > 0:
        # Find the end of this stale block (next function def)
        idx_next_fn = content.find('\ndef _handle_ml_forecast', idx_end)
        if idx_next_fn > 0:
            # Remove everything from marker_start to idx_next_fn (exclusive)
            content = content[:idx_start] + '\n\n' + content[idx_next_fn:]
            print(f"Removed stale ml_cluster block at {idx_start}–{idx_next_fn}")
        else:
            print("Could not find end of stale block")
    else:
        print("marker_end_old not found after marker_start")
else:
    print("marker_start not found — file may already be clean")

# ── Fix 3: residual after dashboard handler ───────────────────
# Pattern: '    })ïch# ============================================================\n# HANDLER: ML Clustering'
# The garbled character is there
bad_dashboard = r'    \}\)[\uFFFD\u00ef\uad\u00bc]ch# ============================================================'
content = re.sub(
    r'    \}\)[^\n]*ch# ============================================================\n# HANDLER: ML Clustering',
    '    })\n\n\n# ============================================================\n# HANDLER: ML Clustering',
    content
)

with open('analytics/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done. views.py written.")
