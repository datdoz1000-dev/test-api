import re
import logging
import pandas as pd
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

MONGO_URI = "mongodb+srv://datdoz1000_db_user:KHz1rR1oMBNPixPY@testapi.rq4cv6g.mongodb.net/?"
DB_NAME = "vietnam_stocks"

def run_strategy():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    logging.info("1. Đang truy vấn dữ liệu 'Lợi nhuận sau thuế' từ MongoDB...")
    
    # Tìm các document chứa Lợi nhuận sau thuế (Sử dụng Regex để bắt cả trường hợp ghi hoa/thường)
    query = {
        "$or": [
            {"item_id": "profit_after_tax"},
            {"item": {"$regex": "lợi nhuận sau thuế", "$options": "i"}}
        ]
    }
    docs = list(db["income_statement"].find(query))
    
    if not docs:
        logging.warning("Không tìm thấy dữ liệu 'Lợi nhuận sau thuế'. Hãy chắc chắn bạn đã cào dữ liệu.")
        return

    results = []
    
    logging.info("2. Đang áp dụng logic: 3 Quý gần nhất LNST > 0...")
    for doc in docs:
        symbol = doc.get("symbol", "UNKNOWN")
        
        # Trích xuất các cột chứa chu kỳ thời gian (VD: 2024-Q1, 2024-Q2,...)
        quarter_keys = [key for key in doc.keys() if re.match(r"^\d{4}-Q\d$", key)]
        
        # Sắp xếp theo bảng chữ cái cũng chính là sắp xếp theo thời gian tăng dần
        quarter_keys.sort()
        
        # Bỏ qua nếu mã này chưa đủ dữ liệu của 3 quý
        if len(quarter_keys) < 3:
            continue
            
        # Lấy 3 quý gần nhất
        last_3_quarters = quarter_keys[-3:]
        profits = [doc.get(q, 0) for q in last_3_quarters]
        
        # Logic: Tất cả 3 quý đều phải có LNST > 0
        try:
            is_good = all(float(p) > 0 for p in profits if p is not None)
        except (ValueError, TypeError):
            is_good = False
            
        # Đóng gói kết quả
        results.append({
            "symbol": symbol,
            "q_minus_2_name": last_3_quarters[0],
            "q_minus_2_profit": profits[0],
            "q_minus_1_name": last_3_quarters[1],
            "q_minus_1_profit": profits[1],
            "q_current_name": last_3_quarters[2],
            "q_current_profit": profits[2],
            "signal": "BUY" if is_good else "IGNORE",
            "evaluated_at": pd.Timestamp.now()
        })
        
    logging.info("3. Lưu danh sách tín hiệu vào collection 'signals'...")
    if results:
        # Xóa dữ liệu chiến lược cũ trước khi ghi mới để không bị rác
        db["signals"].delete_many({}) 
        db["signals"].insert_many(results)
        
        buy_count = sum(1 for r in results if r["signal"] == "BUY")
        logging.info(f"Hoàn tất! Phân tích {len(results)} mã. Có {buy_count} mã đạt tiêu chí BUY.")
    
    client.close()

if __name__ == "__main__":
    run_strategy()