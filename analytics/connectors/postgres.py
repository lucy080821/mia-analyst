import pandas as pd
from sqlalchemy import create_engine, text
from .base import BaseDatabaseConnector

class PostgresConnector(BaseDatabaseConnector):
    """
    Connector for PostgreSQL databases.
    """
    
    def get_connection_string(self) -> str:
        # Format: postgresql+psycopg2://<username>:<password>@<host>:<port>/<database_name>
        import urllib.parse
        encoded_password = urllib.parse.quote_plus(self.password)
        return f"postgresql+psycopg2://{self.credential.username}:{encoded_password}@{self.credential.host}:{self.credential.port}/{self.credential.database_name}"

    def get_engine(self):
        return create_engine(self.get_connection_string())

    def test_connection(self) -> tuple[bool, str]:
        try:
            engine = self.get_engine()
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True, "Kết nối PostgreSQL thành công!"
        except Exception as e:
            return False, f"Lỗi kết nối PostgreSQL: {str(e)}"

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
                df = pd.read_sql_table(table_name, engine)
            return df
        except Exception as e:
            raise Exception(f"Lỗi khi trích xuất dữ liệu từ PostgreSQL: {str(e)}")

    def get_tables(self) -> list[str]:
        """
        Duyệt danh sách các bảng trong Database (schema public).
        """
        engine = self.get_engine()
        query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        try:
            with engine.connect() as connection:
                df = pd.read_sql(text(query), connection)
                return df['table_name'].tolist()
        except Exception as e:
            raise Exception(f"Error fetching Postgres tables: {str(e)}")
