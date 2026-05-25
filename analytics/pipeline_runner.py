import pandas as pd
from .duckdb_engine import DuckDBEngine
from .ai_transformer import AITransformer

class ELTPipelineRunner:
    """
    Orchestrates the entire ELT process:
    1. Extract data using Connectors.
    2. Register in DuckDB.
    3. Generate/Execute Staging Transformation.
    4. Generate/Execute Analytics Transformation.
    5. Save results to the central Data Warehouse (Postgres/SQLite).
    """
    
    def __init__(self):
        self.engine = DuckDBEngine()
        self.ai = AITransformer()

    def run_connector_to_staging(self, connector, extract_kwargs: dict, raw_table_name: str, staging_table_name: str) -> pd.DataFrame:
        """
        Extracts data using the provided connector, automatically generates a staging SQL
        using AI, applies the transformation, and saves it.
        """
        print(f"Starting Extraction for {raw_table_name}...")
        raw_df = connector.extract_to_dataframe(**extract_kwargs)
        
        if raw_df.empty:
            print(f"No data extracted for {raw_table_name}.")
            return raw_df
            
        print(f"Registering {raw_table_name} in DuckDB...")
        self.engine.register_dataframe(raw_table_name, raw_df)
        
        print(f"Asking AI to generate Staging SQL for {raw_table_name}...")
        staging_sql = self.ai.generate_staging_sql(raw_table_name, raw_df)
        print(f"Generated SQL:\n{staging_sql}")
        
        print(f"Executing Transformation...")
        staging_df = self.engine.execute_transform(staging_sql)
        
        print(f"Saving to DWH Staging Layer ({staging_table_name})...")
        self.engine.save_to_django_db(staging_df, staging_table_name)
        
        return staging_df

    def run_analytics_layer(self, user, staging_tables: dict, user_request: str, gold_table_name: str) -> pd.DataFrame:
        """
        Takes multiple staging dataframes, asks AI to fulfill a business request,
        and saves the resulting table to the Analytics (Gold) layer.
        """
        for t_name, df in staging_tables.items():
            self.engine.register_dataframe(t_name, df)
            
        print(f"Asking AI to generate Analytics SQL based on request: '{user_request}'...")
        analytics_sql = self.ai.generate_analytics_sql(staging_tables, user_request)
        print(f"Generated SQL:\n{analytics_sql}")
        
        print("Executing Analytics Transformation...")
        analytics_df = self.engine.execute_transform(analytics_sql)
        
        print(f"Saving to DWH Analytics Layer ({gold_table_name})...")
        self.engine.save_to_django_db(analytics_df, gold_table_name)
        
        # Register as a UserDataset so it appears in the dashboard/chat
        self.register_dataset(
            user=user,
            table_name=gold_table_name,
            display_name=f"Smart Report: {gold_table_name}",
            row_count=len(analytics_df)
        )
        
        return analytics_df

    def register_dataset(self, user, table_name, display_name, source_type='PIPELINE', row_count=0):
        """Helper to register the processed table in Mia's dataset registry."""
        from analytics.models import UserDataset
        UserDataset.objects.update_or_create(
            user=user,
            table_name=table_name,
            defaults={
                'name': display_name,
                'source_type': source_type,
                'row_count': row_count
            }
        )
