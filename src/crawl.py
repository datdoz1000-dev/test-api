import logging
import pandas as pd
from vnstock.api.financial import Finance
from db import MongoDBConnector

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Danh sách mã 
<<<<<<< HEAD
SYMBOLS = ["HPG", "VCB", "FPT"]
=======
SYMBOLS = ["HPG","VCB", "FPT"]
>>>>>>> bf81072c40a17ce43a939220ed85be8cf887dc26

def crawl_profit_data():
    db = MongoDBConnector()
    
    for symbol in SYMBOLS:
        logging.info(f"Đang cào dữ liệu BCTC Quý cho mã: {symbol}")
        try:
            fin = Finance(symbol=symbol, source="KBS")
            df = fin.income_statement(period="Quarter")
            
            if df is None or df.empty:
                logging.warning(f"Không có dữ liệu BCTC cho {symbol}")
                continue
            
            #: Xoá các hàng có item_id trùng nhau 
            if 'item_id' in df.columns:
                df = df.drop_duplicates(subset=['item_id'], keep='first')
                
            # Loại bỏ các cột trùng lặp thời gian do KBS sinh ra (vd: 2025-Q4_1)
            cols_to_keep = [c for c in df.columns if not str(c).endswith('_1') and not str(c).endswith('_2')]
            df = df[cols_to_keep]
                
            # 3. Lọc lấy chỉ số LNST
            df = df[df["item_id"] == "net_profit"].copy()
            if df.empty:
                continue
                
            # Chuyển dữ liệu từ ngang (cột là quý) sang dọc (Melt)
            # Khúc này sẽ biến các cột như '2026-Q1' thành dữ liệu trong cột 'period_str'
            time_cols = [c for c in df.columns if c not in ['item', 'item_id']]
            df_melted = df.melt(id_vars=['item_id'], value_vars=time_cols, var_name='period_str', value_name='value')
            
            # Đẩy item_id thành tên cột (Pivot) để lưu vào DB sạch sẽ
            df_pivoted = df_melted.pivot_table(index='period_str', columns='item_id', values='value', aggfunc='first').reset_index()
            
            # Bổ sung các trường bắt buộc để thoả mãn Unique Index của MongoDB
            df_pivoted["symbol"] = symbol
            df_pivoted["period"] = "Quarter"
            # Tách năm (2026) và quý (1) từ chuỗi '2026-Q1'
            df_pivoted["year"] = df_pivoted["period_str"].str.split('-').str[0].astype(int)
            df_pivoted["quarter"] = df_pivoted["period_str"].str.extract(r'Q(\d+)').astype(int)
            
            # Đóng gói dữ liệu để lưu
            records = df_pivoted.to_dict(orient="records")
            
            # Lưu vào bảng income_statement
<<<<<<< HEAD
            # match_keys bây giờ phải sử dụng bộ khoá chuẩn của index
            db.bulk_upsert("income_statement", records, match_keys=["symbol", "period", "year", "quarter"])
=======
            db.bulk_upsert("income_statement", records, match_keys=["symbol", "item_id"])
>>>>>>> bf81072c40a17ce43a939220ed85be8cf887dc26
            logging.info(f"Đã lưu thành công LNST của {symbol}")
            
        except Exception as e:
            logging.error(f"Lỗi khi cào mã {symbol}: {e}")

if __name__ == "__main__":
    print("--- BẮT ĐẦU CÀO DỮ LIỆU ---")
    crawl_profit_data()
    print("--- HOÀN TẤT CÀO DỮ LIỆU ---")
