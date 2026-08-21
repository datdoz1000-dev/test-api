# import logging
# from datetime import datetime
# from db import MongoDBConnector

# logging.basicConfig(level=logging.INFO, format="%(message)s")

# def run_strategy():
#     db = MongoDBConnector()
    
#     # Lấy danh sách các mã cổ phiếu (symbol) có trong bảng income_statement
#     symbols = db.db["income_statement"].distinct("symbol")
    
#     results = []
    
#     logging.info("--- ĐANG CHẠY LOGIC PHÂN TÍCH ---")
    
#     for symbol in symbols:
#         # Lấy dữ liệu lợi nhuận của mã hiện tại, sắp xếp theo thời gian (năm và quý tăng dần)
#         docs = list(db.db["income_statement"].find({"symbol": symbol}).sort([("year", 1), ("quarter", 1)]))
        
#         if len(docs) < 3:
#             logging.warning(f"Mã {symbol} chưa đủ dữ liệu 3 quý. Bỏ qua.")
#             continue
            
#         # Trích xuất 3 quý gần nhất
#         last_3_docs = docs[-3:]
        
#         try:
#             # Thu thập tên quý và lợi nhuận của 3 quý gần nhất
#             q_names = [doc.get("period_str") for doc in last_3_docs]
#             q_profits = [float(doc.get("net_profit", 0)) for doc in last_3_docs]
            
#             p1, p2, p3 = q_profits
            
#             # Tiêu chí: Cả 3 quý gần nhất đều phải có LNST > 0
#             is_buy = (p1 > 0) and (p2 > 0) and (p3 > 0)
            
#             results.append({
#                 "symbol": symbol,
#                 "q_minus_2_name": q_names[0],
#                 "q_minus_2_profit": p1,
#                 "q_minus_1_name": q_names[1],
#                 "q_minus_1_profit": p2,
#                 "q_current_name": q_names[2],
#                 "q_current_profit": p3,
#                 "total_3q_profit": sum(q_profits),
#                 "signal": "BUY" if is_buy else "IGNORE",
#                 "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             })
#         except Exception as e:
#             logging.error(f"Lỗi tính toán cho {symbol}: {e}")
#             continue

#     # Lưu kết quả vào Collection 'signals' trong MongoDB
#     if results:
#         db.db["signals"].delete_many({}) # Xoá tín hiệu cũ
#         db.db["signals"].insert_many(results) # Ghi tín hiệu mới
        
#         buy_count = sum(1 for r in results if r["signal"] == "BUY")
#         logging.info(f"Hoàn tất! Đã phân tích {len(results)} mã. Có {buy_count} mã đạt tiêu chí BUY.")
#     else:
#         logging.warning("Không có dữ liệu hợp lệ nào để phân tích.")

# if __name__ == "__main__":
#     run_strategy()

import logging
from datetime import datetime
from pymongo import UpdateOne
from db import MongoDBConnector

logging.basicConfig(level=logging.INFO, format="%(message)s")

def run_strategy(symbols_to_analyze=None):
    db = MongoDBConnector()
    
    # 1. Xác định danh sách mã cần phân tích
    if symbols_to_analyze:
        symbols = symbols_to_analyze
        logging.info(f"--- ĐANG CHẠY PHÂN TÍCH CHO CÁC MÃ: {', '.join(symbols)} ---")
    else:
        # Nếu không truyền gì vào, mặc định phân tích toàn bộ trong DB
        symbols = db.db["income_statement"].distinct("symbol")
        logging.info("--- ĐANG CHẠY PHÂN TÍCH TẤT CẢ CÁC MÃ TRONG DATABASE ---")
    
    results = []
    invest_recommendations = []
    
    for symbol in symbols:
        # Lấy dữ liệu lợi nhuận, sắp xếp theo thời gian (năm và quý tăng dần)
        docs = list(db.db["income_statement"].find({"symbol": symbol}).sort([("year", 1), ("quarter", 1)]))
        
        if len(docs) < 3:
            logging.warning(f"[{symbol}] Chưa đủ dữ liệu 3 quý. Bỏ qua.")
            continue
            
        # Trích xuất 3 quý gần nhất
        last_3_docs = docs[-3:]
        
        try:
            q_names = [doc.get("period_str") for doc in last_3_docs]
            q_profits = [float(doc.get("net_profit", 0)) for doc in last_3_docs]
            
            p1, p2, p3 = q_profits
            
            # Tiêu chí: Cả 3 quý gần nhất đều phải có LNST > 0
            is_buy = (p1 > 0) and (p2 > 0) and (p3 > 0)
            
            # In ra màn hình chi tiết LNST 3 quý
            logging.info(f"[{symbol}] LNST 3 quý ({q_names[0]}, {q_names[1]}, {q_names[2]}): {p1:,.0f} | {p2:,.0f} | {p3:,.0f}")
            
            if is_buy:
                invest_recommendations.append(symbol)
            
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

    # 2. Lưu kết quả vào MongoDB (Cập nhật riêng lẻ, không xoá mã cũ)
    if results:
        operations = []
        for r in results:
            # Upsert: Nếu mã đã có tín hiệu thì ghi đè tín hiệu mới, chưa có thì thêm mới.
            operations.append(UpdateOne({"symbol": r["symbol"]}, {"$set": r}, upsert=True))
        
        db.db["signals"].bulk_write(operations, ordered=False)
        
        # 3. Kết luận đưa ra lời khuyên đầu tư
        logging.info("=" * 60)
        logging.info("KẾT LUẬN ĐẦU TƯ:")
        if invest_recommendations:
            logging.info(f"🟢 NÊN ĐẦU TƯ vào các mã: {', '.join(invest_recommendations)}")
            logging.info("   Lý do: Lợi nhuận sau thuế trong 3 quý liên tiếp gần nhất đều lớn hơn 0.")
        else:
            logging.info("🔴 KHÔNG CÓ mã nào đạt tiêu chuẩn (LNST 3 quý > 0) trong danh sách vừa kiểm tra.")
        logging.info("=" * 60)
    else:
        logging.warning("Không có dữ liệu hợp lệ nào để phân tích.")

# Chạy trực tiếp từ terminal
if __name__ == "__main__":
    print("--- CHƯƠNG TRÌNH PHÂN TÍCH CHIẾN LƯỢC ---")
    user_input = input("Nhập danh sách mã cần phân tích (để trống nếu muốn phân tích TOÀN BỘ trong DB): ")
    
    if user_input.strip():
        symbols_list = [s.strip().upper() for s in user_input.split(',')]
        run_strategy(symbols_list)
    else:
        run_strategy()