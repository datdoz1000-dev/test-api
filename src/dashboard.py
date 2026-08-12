import streamlit as st
import pandas as pd
import certifi
from pymongo import MongoClient

# Import cấu hình và 2 hàm chạy logic của bạn từ các file khác
from config import MONGO_URI, DB_NAME
from crawl import crawl_profit_data
from strategy import run_strategy

# Thiết lập cơ bản cho trang web
st.set_page_config(page_title="Công cụ Lọc Cổ phiếu", page_icon="📈", layout="wide")

st.title("📈 Phân Tích Cổ Phiếu Theo Lợi Nhuận")
st.markdown("Chiến lược: **Lợi nhuận sau thuế 3 quý liên tiếp gần nhất > 0**")

# ==========================================
# PHẦN 1: TƯƠNG TÁC NHẬP MÃ (TỪ GIAO DIỆN)
# ==========================================
st.subheader("1. Nhập Mã Doanh Nghiệp")
symbols_input = st.text_input(
    "Nhập danh sách mã chứng khoán (cách nhau bằng dấu phẩy):", 
    placeholder="Ví dụ: HPG, VCB, FPT"
)

# Nút bấm để thực hiện cả Cào Dữ Liệu & Chạy Thuật Toán
if st.button("🚀 Thực hiện Cào dữ liệu & Phân tích", type="primary"):
    if not symbols_input.strip():
        st.warning("Vui lòng nhập ít nhất 1 mã cổ phiếu!")
    else:
        # Tự động cắt khoảng trắng và viết hoa các mã (vd: "  hpg, fpt " -> ["HPG", "FPT"])
        symbols = [s.strip().upper() for s in symbols_input.split(',')]
        
        # Bật màn hình loading báo tiến độ
        with st.status("Hệ thống đang xử lý...", expanded=True) as status:
            st.write(f"Đang cào dữ liệu BCTC cho: {', '.join(symbols)}")
            crawl_profit_data(symbols) # Gọi file crawl
            
            st.write("Đang chạy chiến lược phân tích...")
            run_strategy()             # Gọi file strategy
            
            status.update(label="Hoàn tất xử lý!", state="complete", expanded=False)
            
        st.success("Thành công! Bảng kết quả dưới đây đã được làm mới tự động.")

st.divider()

# ==========================================
# PHẦN 2: HIỂN THỊ KẾT QUẢ TỪ DATABASE
# ==========================================
st.subheader("2. Kết quả Phân tích")

try:
    # Kết nối MongoDB để lấy tín hiệu (Signals) hiển thị
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client[DB_NAME]
    cursor = db["signals"].find({}, {"_id": 0, "evaluated_at": 0})
    df = pd.DataFrame(list(cursor))
    client.close()
    
    if df.empty:
        st.info("Chưa có dữ liệu. Vui lòng nhập mã và bấm nút thực hiện ở trên để bắt đầu.")
    else:
        # Tách làm 2 nhóm: Đạt (BUY) và Trượt (IGNORE)
        buy_df = df[df["signal"] == "BUY"].reset_index(drop=True)
        ignore_df = df[df["signal"] == "IGNORE"].reset_index(drop=True)
        
        # Các con số thống kê nổi bật
        col1, col2 = st.columns(2)
        col1.metric("Tổng số mã đã quét", len(df))
        col2.metric("Số mã đạt chuẩn MUA", len(buy_df))
        
        st.write("### 🟢 Các mã đạt tiêu chí MUA (BUY)")
        if not buy_df.empty:
            # Format các cột tiền tệ cho dễ nhìn (thêm dấu phẩy phân cách)
            st.dataframe(
                buy_df.style.format(subset=["q_minus_2_profit", "q_minus_1_profit", "q_current_profit", "total_3q_profit"], formatter="{:,.0f}"),
                use_container_width=True
            )
        else:
            st.warning("Không có mã nào trong cơ sở dữ liệu đạt tiêu chí.")
            
        # Ẩn các mã không đạt vào một thanh menu cuộn (Expander) cho gọn
        with st.expander("🔴 Xem các mã KHÔNG đạt tiêu chí (IGNORE)"):
            if not ignore_df.empty:
                st.dataframe(
                    ignore_df.style.format(subset=["q_minus_2_profit", "q_minus_1_profit", "q_current_profit", "total_3q_profit"], formatter="{:,.0f}"),
                    use_container_width=True
                )
            else:
                st.write("Trống.")

except Exception as e:
    st.error(f"Lỗi kết nối cơ sở dữ liệu: {e}")