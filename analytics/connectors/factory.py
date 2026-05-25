from .mysql import MysqlConnector
from .postgres import PostgresConnector
from .sqlserver import SqlServerConnector
from analytics.models import DatabaseCredential

class ConnectorFactory:
    """
    Factory to create the appropriate connector instance based on the credential type.
    """
    
    @staticmethod
    def get_connector(credential):
        if isinstance(credential, DatabaseCredential):
            if credential.db_type == 'mysql':
                return MysqlConnector(credential)
            elif credential.db_type == 'postgres':
                return PostgresConnector(credential)
            elif credential.db_type == 'sqlserver':
                return SqlServerConnector(credential)
            else:
                raise ValueError(f"Loại cơ sở dữ liệu '{credential.db_type}' chưa được hỗ trợ.")
        # Add API connectors here later if needed
        raise ValueError("Loại Credential không hợp lệ.")
