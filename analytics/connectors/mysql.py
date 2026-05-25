import pandas as pd
from sqlalchemy import create_engine, text
from .base import BaseDatabaseConnector

class MysqlConnector(BaseDatabaseConnector):
    """
    Connector for MySQL databases.
    """
    
    def get_connection_string(self) -> str:
        # Format: mysql+pymysql://<username>:<password>@<host>:<port>/<database_name>
        import urllib.parse
        encoded_password = urllib.parse.quote_plus(self.password)
        return f"mysql+pymysql://{self.credential.username}:{encoded_password}@{self.credential.host}:{self.credential.port}/{self.credential.database_name}"

    def get_engine(self):
        return create_engine(self.get_connection_string())

    def test_connection(self) -> tuple[bool, str]:
        try:
            engine = self.get_engine()
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True, "Kết nối MySQL thành công!"
        except Exception as e:
            return False, f"Lỗi kết nối MySQL: {str(e)}"

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
                # Basic extraction of the whole table. 
                # For Incremental Load, the 'query' parameter should be used with WHERE conditions.
                df = pd.read_sql_table(table_name, engine)
            return df
        except Exception as e:
            raise Exception(f"Lỗi khi trích xuất dữ liệu từ MySQL: {str(e)}")

    def get_tables(self) -> list[str]:
        """
        Duyệt danh sách các bảng trong Database.
        """
        engine = self.get_engine()
        query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_SCHEMA = DATABASE()"
        try:
            with engine.connect() as connection:
                df = pd.read_sql(text(query), connection)
                return df['TABLE_NAME'].tolist()
        except Exception as e:
            raise Exception(f"Error fetching MySQL tables: {str(e)}")
