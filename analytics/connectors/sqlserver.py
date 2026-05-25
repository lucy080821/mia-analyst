import pandas as pd
from sqlalchemy import create_engine, text
from .base import BaseDatabaseConnector

class SqlServerConnector(BaseDatabaseConnector):
    """
    Connector for SQL Server databases.
    Requires pymssql (recommended) or pyodbc.
    """
    
    def get_connection_string(self) -> str:
        # Format: mssql+pymssql://<username>:<password>@<host>:<port>/<database_name>
        import urllib.parse
        encoded_password = urllib.parse.quote_plus(self.password)
        # Note: We use pymssql because it's often easier to install on various platforms
        # compared to pyodbc which requires system-level ODBC drivers.
        return f"mssql+pymssql://{self.credential.username}:{encoded_password}@{self.credential.host}:{self.credential.port}/{self.credential.database_name}"

    def get_engine(self):
        return create_engine(self.get_connection_string())

    def test_connection(self) -> tuple[bool, str]:
        try:
            # Check if pymssql is installed
            try:
                import pymssql
            except ImportError:
                return False, "Thiếu thư viện 'pymssql'. Vui lòng chạy: pip install pymssql"

            engine = self.get_engine()
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True, "Kết nối SQL Server thành công!"
        except Exception as e:
            return False, f"Lỗi kết nối SQL Server: {str(e)}"

    def extract_to_dataframe(self, table_name: str = None, query: str = None, **kwargs) -> pd.DataFrame:
        """
        Extract data from a specific table or using a custom SQL query.
        """
        if not table_name and not query:
            raise ValueError("Phải cung cấp tên bảng (table_name) hoặc câu lệnh SQL (query).")
            
        engine = self.get_engine()
        try:
            if query:
                df = pd.read_sql(query, engine)
            else:
                # SQL Server requires specific schema often (dbo), 
                # read_sql_table handles this better if provided in table_name
                df = pd.read_sql_table(table_name, engine)
            return df
        except Exception as e:
            raise Exception(f"Lỗi khi trích xuất dữ liệu từ SQL Server: {str(e)}")

    def get_tables(self) -> list[str]:
        """
        Duyệt danh sách các bảng trong Database (thường là schema dbo).
        """
        engine = self.get_engine()
        query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
        try:
            with engine.connect() as connection:
                df = pd.read_sql(text(query), connection)
                return df['TABLE_NAME'].tolist()
        except Exception as e:
            raise Exception(f"Error fetching SQL Server tables: {str(e)}")
