import logging
import certifi
import dns.resolver
from pymongo import MongoClient, UpdateOne, ASCENDING
from config import MONGO_URI, DB_NAME

logger = logging.getLogger(__name__)

# dnspython dùng Google DNS (8.8.8.8) & Cloudflare DNS (1.1.1.1)
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1']

class MongoDBConnector:
    def __init__(self, uri: str = MONGO_URI, db_name: str = DB_NAME):
        # Thêm tlsCAFile=certifi.where() chống lỗi SSL Handshake trên Windows
        self.client = MongoClient(uri, tlsCAFile=certifi.where())
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

    def bulk_upsert(self, collection_name, records, match_keys=None):
        """Lưu dữ liệu mới, nếu đã có (dựa trên match_keys) thì cập nhật"""
        if not records:
            return 0
            
        if match_keys is None:
            match_keys = ["symbol", "item_id"]
            
        operations = []
        for record in records:
            # Tạo bộ lọc để tìm xem bản ghi đã tồn tại chưa dựa trên các key được chỉ định
            filter_doc = {k: record.get(k) for k in match_keys if k in record}
            
            # Upsert=True có nghĩa là: Có thì Update, chưa có thì Insert
            operations.append(UpdateOne(filter_doc, {"$set": record}, upsert=True))
            
        if operations:
            result = self.db[collection_name].bulk_write(operations, ordered=False)
            return result.upserted_count + result.modified_count
        return 0

    def close(self):
        self.client.close()