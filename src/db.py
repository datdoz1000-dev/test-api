import os
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "vietnam_stocks")

class MongoDB:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        
    def bulk_upsert(self, collection_name, records, match_keys):
        """Lưu dữ liệu mới, nếu đã có (dựa trên match_keys) thì cập nhật"""
        if not records:
            return 0
        
        operations = []
        for record in records:
            # Tạo bộ lọc để tìm xem record đã tồn tại chưa
            filter_doc = {k: record.get(k) for k in match_keys}
            operations.append(UpdateOne(filter_doc, {"$set": record}, upsert=True))
            
        result = self.db[collection_name].bulk_write(operations, ordered=False)
        return result.upserted_count + result.modified_count