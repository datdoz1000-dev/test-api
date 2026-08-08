import os
import logging
from pymongo import MongoClient
import pandas as pd
from vnstock.api.financial import Finance
from dotenv import load_dotenv
import certifi

# Cấu hình log để dễ nhìn
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "vietnam_stocks")

def test_mongodb_connection():
    logging.info("--- 1. KIỂM TRA KẾT NỐI MONGODB ---")
    try:
        if not MONGO_URI:
            logging.error("Chưa có MONGO_URI trong file .env")
            return False
            
        # Thêm tlsCAFile=certifi.where() để fix lỗi SSL
        # Thêm serverSelectionTimeoutMS=5000 để không phải chờ quá lâu nếu lỗi mạng
        client = MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
        
        # Test ping để kiểm tra kết nối
        client.admin.command('ping')
        logging.info("✅ KẾT NỐI MONGODB THÀNH CÔNG!")
        
        # In ra các collections
        db = client[DB_NAME]
        collections = db.list_collection_names()
        logging.info(f"Các collections hiện có trong Database '{DB_NAME}': {collections}")
        return True
    except Exception as e:
        logging.error(f"❌ LỖI KẾT NỐI MONGODB: {e}")
        logging.info("""
        GỢI Ý SỬA LỖI DNS MONGODB TRÊN WINDOWS:
        1. Đổi DNS của máy tính sang Google DNS (8.8.8.8 và 8.8.4.4) hoặc Cloudflare (1.1.1.1).
        2. Tắt các phần mềm VPN hoặc Proxy nếu đang bật.
        3. Thử dùng mạng Wifi khác hoặc phát 4G từ điện thoại.
        4. (Tùy chọn) Trong URL MongoDB Atlas, thay vì dùng mongodb+srv://, hãy lấy Standard connection string (mongodb://).
        """)
        return False

def test_vnstock_api(symbol="HPG"):
    logging.info(f"\n--- 2. KIỂM TRA DỮ LIỆU VNSTOCK MÃ {symbol} ---")
    try:
        # Cào thử dữ liệu
        fin = Finance(symbol=symbol, source="KBS")
        df = fin.income_statement(period="Quarter")
        
        if df is None or df.empty:
            logging.warning("❌ Không lấy được dữ liệu BCTC.")
            return
            
        logging.info(f"✅ Lấy được dữ liệu với {len(df)} dòng.")
        logging.info(f"Danh sách các cột: {df.columns.tolist()}")
        
        if 'item_id' in df.columns:
            unique_items = df['item_id'].unique().tolist()
            logging.info(f"Danh sách các loại item_id hiện có: \n{unique_items}")
            
            # Thử lọc Lợi nhuận sau thuế
            profit_df = df[df["item_id"] == "profit_after_tax"]
            if not profit_df.empty:
                logging.info(f"✅ TÌM THẤY Lợi nhuận sau thuế (profit_after_tax): {len(profit_df)} bản ghi")
                print(profit_df.head())
            else:
                logging.warning("❌ KHÔNG TÌM THẤY item_id 'profit_after_tax'. Hãy đối chiếu danh sách item_id phía trên xem nó bị đổi tên thành gì nhé!")
        else:
            logging.warning("❌ Cột 'item_id' KHÔNG TỒN TẠI trong dữ liệu trả về từ vnstock.")
            print(df.head())
            
    except Exception as e:
        logging.error(f"❌ Lỗi khi cào dữ liệu vnstock: {e}")

if __name__ == "__main__":
    test_mongodb_connection()
    test_vnstock_api("HPG")