import logging
import pandas as pd
from vnstock.api.financial import Finance
from db import MongoDBConnector

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

def crawl_profit_data(symbols):
    db = MongoDBConnector()
    
    for symbol in symbols:
        logging.info(f"Đang cào dữ liệu BCTC Quý cho mã: {symbol}")
        try:
            fin = Finance(symbol=symbol, source="KBS")
            df = fin.income_statement(period="Quarter")
            
            if df is None or df.empty:
                logging.warning(f"Không có dữ liệu BCTC cho {symbol}")
                continue
                
            # Xoá các hàng có item_id trùng nhau 
            if 'item_id' in df.columns:
                df = df.drop_duplicates(subset=['item_id'], keep='first')
                
            # Loại bỏ các cột trùng lặp thời gian do KBS sinh ra 
            cols_to_keep = [c for c in df.columns if not str(c).endswith('_1') and not str(c).endswith('_2')]
            df = df[cols_to_keep]
                
            # 3. Lọc lấy chỉ số LNST
            df = df[df["item_id"] == "net_profit"].copy()
            if df.empty:
                continue
                
            # Chuyển dữ liệu từ ngang (cột là quý) sang dọc (Melt)
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
            
            # match_keys
            db.bulk_upsert("income_statement", records, match_keys=["symbol", "period", "year", "quarter"])
            
            logging.info(f"Đã lưu thành công LNST của {symbol}")
            
        except Exception as e:
            logging.error(f"Lỗi khi cào mã {symbol}: {e}")

if __name__ == "__main__":
    print("--- CHƯƠNG TRÌNH CÀO DỮ LIỆU TÀI CHÍNH ---")
    
    # Cho phép người dùng tự nhập mã từ màn hình terminal/console
    user_input = input("Nhập danh sách mã doanh nghiệp cần cào: ")
    
    if user_input.strip():
        # Xử lý chuỗi nhập vào: Tách bằng dấu phẩy, xoá khoảng trắng và in hoa toàn bộ
        symbols = [s.strip().upper() for s in user_input.split(',')]
        
        print("\n--- BẮT ĐẦU CÀO DỮ LIỆU ---")
        crawl_profit_data(symbols)
        print("--- HOÀN TẤT CÀO DỮ LIỆU ---")
    else:
        print("Bạn chưa nhập mã nào. Chương trình kết thúc.")