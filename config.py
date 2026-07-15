import os
from pathlib import Path


def _load_env_file():
    env_path = Path(__file__).resolve().parent / '.env'
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue

        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file()

# Database
DB_SERVER = os.environ.get('DB_SERVER', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '1433')
DB_NAME = os.environ.get('DB_NAME', 'SmartStock')
DB_USERNAME = os.environ.get('DB_USERNAME', 'sa')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'SmartStock123!')
DB_TRUSTED_CONNECTION = os.environ.get('DB_TRUSTED_CONNECTION', 'no')
DB_DRIVER = os.environ.get('DB_DRIVER', 'ODBC Driver 18 for SQL Server')

# Flask
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
FLASK_PORT = int(os.environ.get('FLASK_PORT', '5000'))


def get_sqlalchemy_connection_string():
    return (
        f'mssql+pymssql://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_NAME}'
    )
