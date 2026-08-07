import logging
from vnstock.api.financial import Finance
from db import MongoDB

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Danh sách mã bạn muốn theo dõi (có thể thêm bớt tùy ý)
SYMBOLS = ["HPG","VCB", "FPT"]

def crawl_profit_data():
    db = MongoDB()
    
    for symbol in SYMBOLS:
        logging.info(f"Đang cào dữ liệu BCTC Quý cho mã: {symbol}")
        try:
            fin = Finance(symbol=symbol, source="VCI")
            df = fin.income_statement(period="Quarter")
            
            if df is None or df.empty:
                logging.warning(f"Không có dữ liệu BCTC cho {symbol}")
                continue
                
            # Lọc chỉ lấy đúng dòng "Lợi nhuận sau thuế"
            df = df[df["item_id"] == "profit_after_tax"].copy()
            if df.empty:
                continue
                
            # Đóng gói dữ liệu để lưu
            df["symbol"] = symbol
            records = df.to_dict(orient="records")
            
            # Lưu vào bảng income_statement
            db.bulk_upsert("income_statement", records, match_keys=["symbol", "item_id"])
            logging.info(f"✅ Đã lưu thành công LNST của {symbol}")
            
        except Exception as e:
            logging.error(f"Lỗi khi cào mã {symbol}: {e}")

if __name__ == "__main__":
    print("--- BẮT ĐẦU CÀO DỮ LIỆU ---")
    crawl_profit_data()
    print("--- HOÀN TẤT CÀO DỮ LIỆU ---")