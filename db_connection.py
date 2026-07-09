import pymssql
from config import (
    DB_SERVER, DB_PORT, DB_NAME, DB_USERNAME, DB_PASSWORD,
    get_sqlalchemy_connection_string,
)

def get_connection():
    return pymssql.connect(
        server=DB_SERVER,
        port=DB_PORT,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        database=DB_NAME,
        as_dict=False,
    )

conn = get_connection()
cursor = conn.cursor()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(get_sqlalchemy_connection_string(), echo=True)

SessionLocal = sessionmaker(bind=engine)

from flask import Flask
from Controler.receipt_processing import ReceiptController

app = Flask(__name__)

receipt_controller = ReceiptController()

@app.route("/receipt/upload", methods=["POST"])
def upload_receipt():
    return receipt_controller.upload_receipt()
