import pandas as pd
import re
import numpy as np

class FormulaEngine:
    @staticmethod
    def evaluate(df, formula, field_type):
        """
        Evaluates a DAX-like formula on a Pandas DataFrame.
        Supported: SUM(col), AVG(col), COUNT(col), MIN(col), MAX(col), [col] + [col]
        """
        # Clean formula
        formula = formula.strip()
        
        # 1. Handle Aggregations (Measures)
        if field_type == 'MEASURE':
            return FormulaEngine._evaluate_measure(df, formula)
        
        # 2. Handle Row-level (Calculated Columns)
        else:
            return FormulaEngine._evaluate_column(df, formula)

    @staticmethod
    def _evaluate_measure(df, formula):
        # Map SUM(col) -> df['col'].sum()
        # regex to find FUNC(COL)
        pattern = r'(SUM|AVG|COUNT|MIN|MAX)\((.*?)\)'
        
        def replace_func(match):
            func = match.group(1)
            col = match.group(2).strip('[]"\' ')
            if col not in df.columns:
                return "0"
            
            if func == 'SUM': return str(df[col].sum())
            if func == 'AVG': return str(df[col].mean())
            if func == 'COUNT': return str(df[col].count())
            if func == 'MIN': return str(df[col].min())
            if func == 'MAX': return str(df[col].max())
            return "0"

        processed_formula = re.sub(pattern, replace_func, formula, flags=re.IGNORECASE)
        
        # Now handle basic math on the resulting numbers
        try:
            # Use simple eval or just eval with restricted scope for safety
            # For now, using a simple eval but in production use a safer parser
            result = eval(processed_formula, {"__builtins__": None}, {})
            return result
        except Exception as e:
            print(f"Formula Evaluation Error: {e}")
            return 0

    @staticmethod
    def _evaluate_column(df, formula):
        # Map [Col Name] to df['Col Name']
        # We can use df.eval() for row-level operations which is quite safe and fast
        
        # Replace [Col Name] with Col_Name (internal pandas eval style)
        # Or just use the original names if they are valid identifiers
        
        processed_formula = formula
        for col in df.columns:
            if f'[{col}]' in formula:
                processed_formula = processed_formula.replace(f'[{col}]', f"`{col}`")
        
        try:
            return df.eval(processed_formula)
        except Exception as e:
            print(f"Column Evaluation Error: {e}")
            return pd.Series([np.nan] * len(df))
