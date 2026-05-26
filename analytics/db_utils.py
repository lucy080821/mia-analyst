from sqlalchemy import create_engine
from django.conf import settings
import urllib.parse

def get_sqlalchemy_engine():
    """
    Tạo SQLAlchemy engine từ cấu hình DATABASES của Django.
    Hỗ trợ PostgreSQL và SQLite (fallback).
    """
    db_config = settings.DATABASES['default']
    engine_name = db_config['ENGINE']
    
    if 'postgresql' in engine_name or 'postgis' in engine_name:
        # Xây dựng connection string cho PostgreSQL
        user = db_config.get('USER', '')
        password = db_config.get('PASSWORD', '')
        host = db_config.get('HOST', 'localhost')
        port = db_config.get('PORT', '5432')
        name = db_config.get('NAME', '')
        
        # Encode password phòng trường hợp có ký tự đặc biệt
        safe_password = urllib.parse.quote_plus(password)
        
        connection_string = f"postgresql://{user}:{safe_password}@{host}:{port}/{name}?sslmode=require"
        return create_engine(connection_string)
    
    else:
        # Fallback cho SQLite
        db_path = db_config['NAME']
        return create_engine(f"sqlite:///{db_path}")

def get_postgres_schema_query(table_name=None):
    """
    Trả về câu lệnh SQL để lấy thông tin schema trong PostgreSQL.
    """
    if table_name:
        return f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position;
        """
    return """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE';
    """

def execute_query(sql, params=None):
    """
    Executes a raw SQL query using Django's database connection and returns results as a list of dicts.
    """
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        if cursor.description:
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        return None
