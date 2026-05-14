

import pyodbc
SERVER = 'D403-005'
DATABASE = 'SmartStock'
DRIVER='ODBC Driver 17 for SQL Server'
def get_connection():
 conn_str = (
 f'DRIVER={{{DRIVER}}};'
 f'SERVER={SERVER};'
 f'DATABASE={DATABASE};'
 f'Trusted_Connection=yes;'
 )
 return pyodbc.connect(conn_str)
conn=get_connection()
cursor =conn.cursor()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# יצירת ה-engine
engine = create_engine(
    f'mssql+pyodbc://@{SERVER}/{DATABASE}?driver={DRIVER}',
    echo=True
)

# יצירת סשן
SessionLocal = sessionmaker(bind=engine)
