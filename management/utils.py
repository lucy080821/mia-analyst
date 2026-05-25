import pandas as pd
from django.http import HttpResponse
from io import BytesIO

def export_to_excel(data, filename, sheet_name="Sheet1"):
    """
    Exports a list of dictionaries to an Excel file response.
    """
    df = pd.DataFrame(data)
    
    # Create the Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}.xlsx'
    
    return response
