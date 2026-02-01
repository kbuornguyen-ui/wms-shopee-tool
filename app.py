import streamlit as st
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# --- Cấu hình Trang Web ---
st.set_page_config(page_title="WMS SKU Search Tool", layout="wide")
st.title("📦 WMS Add-Picking Manual")

# --- Google Sheets API setup ---
@st.cache_resource
def init_connection():
    if "gcp_service_account" in st.secrets:
        info = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        return gspread.authorize(creds)
    return None

client = init_connection()

OUTPUT_SHEET_ID = '1O_nlMx5ClZMtVXoT5ZiBm886d-FqzUoDARChePd560g'
COOKIE_SHEET_ID = '1QRaq07g9d14bw_rpW0Q-c8f7e1qRYQRq8_vI426yUro'

# --- Các hàm xử lý API (Giữ nguyên Headers bạn yêu cầu) ---
def get_headers():
    try:
        sheet = client.open_by_key(COOKIE_SHEET_ID).worksheet('WMS')
        cookie = sheet.acell('A2').value
        # Giữ nguyên load headers không thêm bớt
        return {
            "Content-Type": "application/json",
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        }
    except Exception as e:
        st.error(f"Lỗi đọc Cookie từ Sheet: {e}")
        return None

def search_api(sku):
    headers = get_headers()
    if not headers: return []
    
    url = f"https://wms.ssc.shopee.vn/api/v2/apps/process/inventory/inventorymap/search_onhand_map?count=100&pageno=1&sku_upc_code={sku}&include_batch=N"
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json().get("data", {}).get("list", [])
        elif res.status_code == 403:
            # Hiển thị thông báo chi tiết khi bị chặn IP hoặc Cookie
            st.error("🚫 Lỗi 403: Shopee từ chối truy cập. Kiểm tra lại Cookie tại ô A2 hoặc IP máy chủ bị chặn.")
            return []
    except Exception as e:
        st.error(f"Lỗi kết nối: {e}")
    return []

# --- Giao diện Web ---
col1, col2 = st.columns([3, 1])

with col1:
    sku_input = st.text_input("Nhập SKU hoặc UPC:")

with col2:
    st.write("##") 
    btn_search = st.button("Tìm kiếm")

if btn_search or sku_input:
    if sku_input:
        results = search_api(sku_input)
        if results:
            st.success(f"Tìm thấy dữ liệu cho SKU: {sku_input}")
            df = pd.DataFrame(results)
            # Hiển thị các cột như code gốc
            st.dataframe(df[['sku_id', 'location_id', 'zone_id', 'on_hand_quantity']])
        else:
            st.warning("Không tìm thấy kết quả hoặc lỗi xác thực.")

if st.button("Tổng hợp dữ liệu"):
    st.info("Đang tổng hợp... Vui lòng đợi.")
