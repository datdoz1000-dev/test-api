import streamlit as st
import pandas as pd
from pymongo import MongoClient

# Tùy chỉnh URI và Tên DB của bạn
MONGO_URI = "mongodb+srv://datdoz1000_db_user:KHz1rR1oMBNPixPY@testapi.rq4cv6g.mongodb.net/?"
DB_NAME = "vietnam_stocks"

# Cấu hình giao diện Streamlit
st.set_page_config(page_title="Stock Screener", page_icon="📈", layout="wide")

st.title("📈 Bảng điều khiển Lọc Cổ phiếu (Stock Screener)")
st.markdown("Chiến lược: **Lợi nhuận sau thuế 3 quý liên tiếp gần nhất > 0**")

# Hàm load dữ liệu từ DB (có cache để web load nhanh, không query liên tục)
@st.cache_data(ttl=60) 
def load_data():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Lấy toàn bộ dữ liệu từ collection signals, bỏ trường _id mặc định của Mongo
    cursor = db["signals"].find({}, {"_id": 0, "evaluated_at": 0})
    df = pd.DataFrame(list(cursor))
    client.close()
    return df

# Tiến hành render UI
try:
    df = load_data()
    
    if df.empty:
        st.warning("Chưa có dữ liệu tín hiệu. Hãy chạy `python src/strategy.py` trước.")
    else:
        # Tách dữ liệu thành 2 bảng
        buy_df = df[df["signal"] == "BUY"].reset_index(drop=True)
        ignore_df = df[df["signal"] == "IGNORE"].reset_index(drop=True)
        
        # 1. Hiển thị thông số tổng quan (Metrics)
        st.subheader("1. Tổng quan")
        col1, col2 = st.columns(2)
        col1.metric("Tổng số mã đã phân tích", len(df))
        col2.metric("Số mã đạt chuẩn (BUY)", len(buy_df), delta="Tiềm năng", delta_color="normal")
        
        st.divider()
        
        # 2. Bảng các mã đạt tiêu chí
        st.subheader("2. Danh sách Cổ phiếu Đạt Tiêu Chí Đầu Tư 🏆")
        if not buy_df.empty:
            # Định dạng lại hiển thị số tiền cho dễ nhìn (thêm dấu phẩy)
            st.dataframe(
                buy_df.style.format(subset=["q_minus_2_profit", "q_minus_1_profit", "q_current_profit"], formatter="{:,.0f}"),
                use_container_width=True
            )
        else:
            st.info("Hiện tại chưa có mã nào thỏa mãn điều kiện.")
            
        # 3. Bảng các mã bị loại
        with st.expander("Xem các mã không đạt tiêu chí (IGNORE)"):
            st.dataframe(ignore_df, use_container_width=True)

except Exception as e:
    st.error(f"Không thể kết nối Database: {e}")