import pandas as pd
from vnstock.api.financial import Finance

# 1. Lấy dữ liệu từ Vnstock
symbol = "FPT"
fin = Finance(symbol=symbol, source="KBS")
df = fin.income_statement(period="Quarter")

# 2. Xóa các cột mô tả không cần thiết, chỉ giữ lại 'item_id' làm key
df_clean = df.drop(columns=['item', 'item_en'], errors='ignore')

df = fin.income_statement(period="Quarter")

# Xoá các hàng có item_id trùng nhau, bảo vệ quá trình pivot sau đó
if 'item_id' in df.columns:
    df = df.drop_duplicates(subset=['item_id'], keep='first')

# # 3. Đặt item_id làm Index và xoay chiều (Transpose) DataFrame
# # Kết quả: Các chỉ số (profit_after_tax_...) thành CỘT, Thời gian ('2026-Q2'...) thành DÒNG
# df_transposed = df_clean.set_index('item_id').T

# # 4. Đưa Index hiện tại (chuỗi thời gian) thành một cột thực sự
# df_transposed = df_transposed.reset_index().rename(columns={'index': 'period_str'})

# 5. Viết hàm tách year, quarter, period từ chuỗi (vd: '2026-Q2', '2025-Q4_1')
def parse_period(period_str):
    # Loại bỏ phần hậu tố _1, _2 (nếu Vnstock trả về cột bị trùng tên)
    clean_str = str(period_str).split('_')[0]
    
    if '-Q' in clean_str:
        year, q = clean_str.split('-Q')
        return int(year), int(q), 'Quarter'
    elif len(clean_str) == 4 and clean_str.isdigit():
        return int(clean_str), None, 'Year'
    return None, None, None

# Áp dụng hàm để tạo ra 3 cột chuẩn bị cho MongoDB
df_transposed[['year', 'quarter', 'period']] = df_transposed['period_str'].apply(parse_period).apply(pd.Series)

# 6. Gán thêm mã cổ phiếu
df_transposed['symbol'] = symbol

# In ra xem thử kết quả
print(df_transposed.head())

# ==========================================
# CÁCH GỌI HÀM LƯU VÀO MONGODB
# ==========================================
# Dữ liệu lúc này đã khớp hoàn toàn với index idx_symbol_period_year_quarter.
# Bạn cần sửa lại hàm bulk_upsert để query theo bộ 4 key này:

records = df_transposed.to_dict(orient='records')
# Ví dụ: 
# db_connector.bulk_upsert(
#     data=records, 
#     match_keys=['symbol', 'period', 'year', 'quarter'] # Bắt buộc khớp với index
# )