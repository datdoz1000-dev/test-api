import logging
import time
import pandas as pd
from db import MongoDBConnector
from vnstock.api.financial import Finance

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def transform_dataframe(
    df: pd.DataFrame,
    symbol: str,
    period_type: str,
    target_items: list = None,
) -> list:
  if df is None or df.empty:
    return []

  df = df.copy()

  # 1. Lọc dữ liệu chỉ giữ lại các chỉ số trong danh sách target_items
  if target_items and "item_id" in df.columns:
    df = df[df["item_id"].isin(target_items)]

  if df.empty:
    return []

  # 2. Bổ sung Metadata
  df["symbol"] = symbol
  df["period"] = period_type

  if "year" not in df.columns:
    df["year"] = 0
  if "quarter" not in df.columns:
    df["quarter"] = 0

  return df.to_dict(orient="records")


SELECTED_METRICS = [
    # Kết quả kinh doanh
    "net_revenue",  # Doanh thu thuần
    "gross_profit",  # Lợi nhuận gộp
    "profit_after_tax",  # Lợi nhuận sau thuế
    # Bảng cân đối kế toán
    "total_assets",  # Tổng tài sản
    "owner_equity",  # Vốn chủ sở hữu
    "total_liabilities",  # Tổng nợ phải trả
]

def crawl_bctc_for_symbol(
    db: MongoDBConnector, symbol: str, period: str = "quarter"
):
  """Cào 3 BCTC cho mã cổ phiếu bằng cấu trúc vnstock.api mới."""
  # SỬA LỖI: Định nghĩa biến freq và period_type dựa trên tham số period
  p_clean = period.lower()
  if p_clean in ["quarter", "q"]:
    freq = "Quarter"
    period_type = "quarter"
  elif p_clean in ["year", "y"]:
    freq = "Year"
    period_type = "year"
  else:
    logging.error(f"Kỳ BCTC không hợp lệ: {period}")
    return

  logging.info(
      f"--- Đang cào dữ liệu BCTC cho mã: {symbol} ({period_type}) ---"
  )

  # Khởi tạo đối tượng Finance
  fin = Finance(symbol=symbol, source="VCI")

  reports = [
      ("income_statement", fin.income_statement),
      ("balance_sheet", fin.balance_sheet),
      ("cash_flow", fin.cash_flow),
  ]

  for collection_name, fetch_func in reports:
    try:
      # SỬA LỖI: Chỉ cần truyền period=freq
      df = fetch_func(period=freq)

      records = transform_dataframe(
          df, symbol, period_type, target_items=SELECTED_METRICS
      )

      if records:
        count = db.bulk_upsert(collection_name, records)
        logging.info(f"[{symbol}] {collection_name}: Đã lưu {count} chỉ số.")
      else:
        logging.warning(
            f"[{symbol}] {collection_name}: Không có dữ liệu thỏa mãn bộ lọc."
        )

      time.sleep(1)
    except Exception as e:
      logging.error(f"Lỗi khi cào [{collection_name}] của {symbol}: {e}")


if __name__ == "__main__":
  db_client = MongoDBConnector()
  symbols = ["HPG", "SSI", "VCB"]

  try:
    for ticker in symbols:
      crawl_bctc_for_symbol(db_client, symbol=ticker, period="quarter")
  finally:
    db_client.close()
    logging.info("Đã đóng kết nối MongoDB.")