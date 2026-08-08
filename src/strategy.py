import re
import logging
from datetime import datetime
from db import MongoDBConnector

import certifi
from pymongo import MongoClient
from config import DB_NAME, MONGO_URI

logging.basicConfig(level=logging.INFO, format="%(message)s")

class MongoDBConnector:

  def __init__(self, uri: str = MONGO_URI, db_name: str = DB_NAME):
    # Bổ sung tls=True và tlsAllowInvalidCertificates=True để bỏ qua lỗi SSL Handshake
    self.client = MongoClient(
        uri,
        tls=True,
        tlsAllowInvalidCertificates=True,  # Bỏ qua xác thực SSL trên Windows
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10000,
    )
    self.db = self.client[db_name]
    self._setup_indexes()

def run_strategy():
    db = MongoDBConnector()
    
    #Lấy toàn bộ bản ghi Lợi nhuận sau thuế từ collection income_statement
    docs = list(db.db["income_statement"].find({"item_id": "net_profit"}))
    results = []
    
    logging.info("--- ĐANG CHẠY LOGIC PHÂN TÍCH (LNST 3 Quý > 0) ---")
    
    for doc in docs:
        symbol = doc.get("symbol")
        
        # Tìm các cột dữ liệu theo quý 
        quarter_keys = [k for k in doc.keys() if re.match(r"^\d{4}-Q\d$", str(k))]
        quarter_keys.sort() # Sắp xếp tăng dần theo thời gian
        
        if len(quarter_keys) < 3:
            logging.warning(f"Mã {symbol} chưa đủ dữ liệu 3 quý. Bỏ qua.")
            continue
            
        # Trích xuất 3 quý gần nhất
        last_3_quarters = quarter_keys[-3:]
        
        try:
            p1 = float(doc.get(last_3_quarters[0]) or 0)
            p2 = float(doc.get(last_3_quarters[1]) or 0) 
            p3 = float(doc.get(last_3_quarters[2]) or 0) 
            
            # Cả 3 quý đều phải có LNST > 0
            is_buy = (p1 > 0) and (p2 > 0) and (p3 > 0)
            
            results.append({
                "symbol": symbol,
                "q_minus_2_name": last_3_quarters[0],
                "q_minus_2_profit": p1,
                "q_minus_1_name": last_3_quarters[1],
                "q_minus_1_profit": p2,
                "q_current_name": last_3_quarters[2],
                "q_current_profit": p3,
                "total_3q_profit": p1 + p2 + p3,
                "signal": "BUY" if is_buy else "IGNORE",
                "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception as e:
            logging.error(f"Lỗi tính toán cho {symbol}: {e}")
            continue

    #Lưu kết quả vào Collection 'signals'
    if results:
        db.db["signals"].delete_many({})
        db.db["signals"].insert_many(results)
        
        buy_count = sum(1 for r in results if r["signal"] == "BUY")
        logging.info(f"Hoàn tất! Phân tích {len(results)} mã. Có {buy_count} mã đạt tiêu chí BUY.")

if __name__ == "__main__":
    run_strategy()