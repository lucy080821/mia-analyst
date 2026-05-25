"""Fix the missing closing }) on ml_cluster return and ensure clean newlines."""
with open('analytics/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The broken section: JsonResponse that's not closed
old = (
    '        \"summary\": {\"question\": question, \"row_count\": len(data)}\n'
    '\n'
    '\n'
    '\n'
    'def _handle_ml_forecast'
)
new = (
    '        \"summary\": {\"question\": question, \"row_count\": len(data)}\n'
    '    })\n'
    '\n'
    '\n'
    'def _handle_ml_forecast'
)

if old in content:
    content = content.replace(old, new, 1)
    print("Fixed ml_cluster closing brace")
else:
    # Try another variant
    old2 = (
        '        \"summary\": {\"question\": question, \"row_count\": len(data)}\n'
        ' \n'
        '\n'
        ' \n'
        'def _handle_ml_forecast'
    )
    if old2 in content:
        content = content.replace(old2, new, 1)
        print("Fixed ml_cluster closing brace (variant 2)")
    else:
        # Find and show context
        idx = content.find('def _handle_ml_forecast')
        print("Could not find exact pattern. Context before forecast handler:")
        print(repr(content[idx-200:idx]))

with open('analytics/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
