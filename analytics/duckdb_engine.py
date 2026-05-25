import duckdb
import pandas as pd
from django.db import connection

class DuckDBEngine:
    """
    In-memory data processing engine using DuckDB.
    This allows us to run complex SQL transformations on DataFrames or DB tables
    at extremely high speeds without stressing the primary operational database.
    """
    
    def __init__(self):
        # Create an in-memory DuckDB connection
        self.conn = duckdb.connect(database=':memory:')

    def register_dataframe(self, name: str, df: pd.DataFrame):
        """Registers a Pandas DataFrame as a virtual table in DuckDB."""
        self.conn.register(name, df)

    def execute_transform(self, sql_query: str) -> pd.DataFrame:
        """
        Executes a SQL query in DuckDB (which can query registered DataFrames)
        and returns the result as a new Pandas DataFrame.
        """
        try:
            result_df = self.conn.execute(sql_query).df()
            return result_df
        except Exception as e:
            raise Exception(f"DuckDB Transformation Error: {str(e)}")

    def save_to_django_db(self, df: pd.DataFrame, target_table_name: str, if_exists: str = 'replace'):
        """
        Saves the transformed DataFrame back to the main Django database (Postgres/SQLite).
        This represents the "Load" phase back into the Staging or Analytics schemas.
        """
        db_path = str(connection.settings_dict['NAME'])
        engine_type = connection.settings_dict['ENGINE']
        
        try:
            if 'sqlite' in engine_type:
                import sqlite3
                from analytics.utils import prepare_df_for_sqlite
                df = prepare_df_for_sqlite(df)
                with sqlite3.connect(db_path) as sqlite_conn:
                    df.to_sql(name=target_table_name, con=sqlite_conn, if_exists=if_exists, index=False)
            elif 'postgresql' in engine_type:
                from sqlalchemy import create_engine
                db_url = f"postgresql://{connection.settings_dict['USER']}:{connection.settings_dict['PASSWORD']}@{connection.settings_dict['HOST']}:{connection.settings_dict['PORT']}/{connection.settings_dict['NAME']}"
                sql_engine = create_engine(db_url)
                with sql_engine.connect() as pg_conn:
                    df.to_sql(name=target_table_name, con=pg_conn, if_exists=if_exists, index=False)
            else:
                raise Exception(f"Unsupported database engine for automatic saving: {engine_type}")
        except Exception as e:
            raise Exception(f"Error saving data to target table '{target_table_name}': {str(e)}")
