import logging
from datetime import datetime
from db import MongoDBConnector

logging.basicConfig(level=logging.INFO, format="%(message)s")

def run_strategy():
    db = MongoDBConnector()
    
    # Lấy danh sách các mã cổ phiếu (symbol) có trong bảng income_statement
    symbols = db.db["income_statement"].distinct("symbol")
    
    results = []
    
    logging.info("--- ĐANG CHẠY LOGIC PHÂN TÍCH (LNST 3 Quý Liên Tiếp > 0) ---")
    
    for symbol in symbols:
        # Lấy dữ liệu lợi nhuận của mã hiện tại, sắp xếp theo thời gian (năm và quý tăng dần)
        docs = list(db.db["income_statement"].find({"symbol": symbol}).sort([("year", 1), ("quarter", 1)]))
        
        if len(docs) < 3:
            logging.warning(f"Mã {symbol} chưa đủ dữ liệu 3 quý. Bỏ qua.")
            continue
            
        # Trích xuất 3 quý gần nhất
        last_3_docs = docs[-3:]
        
        try:
            # Thu thập tên quý và lợi nhuận của 3 quý gần nhất
            q_names = [doc.get("period_str") for doc in last_3_docs]
            q_profits = [float(doc.get("net_profit", 0)) for doc in last_3_docs]
            
            p1, p2, p3 = q_profits
            
            # Tiêu chí: Cả 3 quý gần nhất đều phải có LNST > 0
            is_buy = (p1 > 0) and (p2 > 0) and (p3 > 0)
            
            results.append({
                "symbol": symbol,
                "q_minus_2_name": q_names[0],
                "q_minus_2_profit": p1,
                "q_minus_1_name": q_names[1],
                "q_minus_1_profit": p2,
                "q_current_name": q_names[2],
                "q_current_profit": p3,
                "total_3q_profit": sum(q_profits),
                "signal": "BUY" if is_buy else "IGNORE",
                "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except Exception as e:
            logging.error(f"Lỗi tính toán cho {symbol}: {e}")
            continue

    # Lưu kết quả vào Collection 'signals' trong MongoDB
    if results:
        db.db["signals"].delete_many({}) # Xoá tín hiệu cũ
        db.db["signals"].insert_many(results) # Ghi tín hiệu mới
        
        buy_count = sum(1 for r in results if r["signal"] == "BUY")
        logging.info(f"Hoàn tất! Đã phân tích {len(results)} mã. Có {buy_count} mã đạt tiêu chí BUY.")
    else:
        logging.warning("Không có dữ liệu hợp lệ nào để phân tích.")

if __name__ == "__main__":
    run_strategy()