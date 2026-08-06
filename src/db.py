from pymongo import MongoClient, UpdateOne, ASCENDING
import logging
from config import MONGO_URI, DB_NAME

logger = logging.getLogger(__name__)

class MongoDBConnector:
    def __init__(self, uri: str = MONGO_URI, db_name: str = DB_NAME):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self._setup_indexes()

    def _setup_indexes(self):
        """Khởi tạo Unique Index để chống trùng lặp dữ liệu BCTC."""
        collections = ["income_statement", "balance_sheet", "cash_flow"]
        index_keys = [
            ("symbol", ASCENDING),
            ("period", ASCENDING),
            ("year", ASCENDING),
            ("quarter", ASCENDING)
        ]
        
        for coll_name in collections:
            self.db[coll_name].create_index(
                index_keys, 
                unique=True, 
                name="idx_symbol_period_year_quarter"
            )

    def bulk_upsert(self, collection_name: str, records: list) -> int:
        """Thực hiện bulk write upsert để ghi nhận nhiều bản ghi cùng lúc."""
        if not records:
            return 0

        operations = []
        for record in records:
            filter_doc = {
                "symbol": record["symbol"],
                "period": record["period"],
                "year": record["year"],
                "quarter": record["quarter"]
            }
            operations.append(
                UpdateOne(filter_doc, {"$set": record}, upsert=True)
            )

        result = self.db[collection_name].bulk_write(operations, ordered=False)
        return result.upserted_count + result.modified_count

    def close(self):
        self.client.close()