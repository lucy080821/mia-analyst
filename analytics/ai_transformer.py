import google.generativeai as genai
from django.conf import settings
import pandas as pd

class AITransformer:
    """
    AI Agent responsible for writing Data Engineering pipelines.
    It inspects raw table schemas and user intents to generate DuckDB SQL for Staging and Analytics layers.
    """
    
    def __init__(self):
        from .ai_utils import get_generative_model
        self.model = get_generative_model()

    def _get_schema_str(self, table_name: str, df: pd.DataFrame) -> str:
        """Helper to convert DataFrame schema to a readable string for the prompt."""
        dtypes = df.dtypes.astype(str).to_dict()
        schema_lines = [f"- {col} ({dtype})" for col, dtype in dtypes.items()]
        return f"Table: {table_name}\nColumns:\n" + "\n".join(schema_lines)

    def generate_staging_sql(self, table_name: str, df: pd.DataFrame) -> str:
        """
        Analyzes a raw dataframe and generates a SQL query to clean and cast it (Silver Layer).
        """
        schema_str = self._get_schema_str(table_name, df)
        
        prompt = f"""
        You are an expert Data Engineer writing DuckDB SQL.
        I have a raw table loaded into DuckDB. 
        
        {schema_str}
        
        Task: Write a single SELECT statement to clean this table for a Staging layer.
        Rules:
        1. Cast strings that look like numbers to DOUBLE or INT.
        2. Cast strings that look like dates to DATE or TIMESTAMP.
        3. Standardize column names (lowercase, replace spaces with underscores) using AS aliases if needed.
        4. Return ONLY the SQL query, without any markdown formatting like ```sql.
        5. The FROM clause must be exactly FROM "{table_name}".
        """
        
        response = self.model.generate_content(prompt)
        sql = response.text.strip()
        # Clean up if the model ignored the markdown rule
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
            
        return sql.strip()

    def generate_analytics_sql(self, tables_info: dict, user_request: str) -> str:
        """
        Generates a Gold layer query (Analytics) combining multiple staging tables based on a user request.
        tables_info: dict mapping table_name to its schema string or dataframe.
        """
        schemas = []
        for t_name, df in tables_info.items():
            schemas.append(self._get_schema_str(t_name, df))
            
        context = "\n\n".join(schemas)
        
        prompt = f"""
        You are an expert Data Engineer and Data Analyst writing DuckDB SQL.
        I have the following cleaned staging tables loaded in DuckDB:
        
        {context}
        
        The Business User asks: "{user_request}"
        
        Task: Write a DuckDB SQL query to aggregate, join, and calculate the metrics needed to answer this request.
        This query will be used to create the final Analytics (Gold) table for the dashboard.
        
        Rules:
        1. Use proper JOINs if multiple tables are needed.
        2. Handle potential NULLs using COALESCE.
        3. Return ONLY the SQL query, without any markdown formatting like ```sql.
        4. Use LEFT JOIN when joining a primary table (like users, customers, products) with a secondary table (logs, transactions, actions) unless specifically requested otherwise, to ensure all primary records are preserved.
        """
        
        response = self.model.generate_content(prompt)
        sql = response.text.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
            
        return sql.strip()
