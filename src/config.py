import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://datdoz1000_db_user:KHz1rR1oMBNPixPY@testapi.rq4cv6g.mongodb.net/?")
DB_NAME = os.getenv("DB_NAME", "vietnam_stocks")