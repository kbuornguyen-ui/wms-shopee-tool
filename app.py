import streamlit as st
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# --- Cấu hình Trang Web ---
st.set_page_config(page_title="WMS SKU Search Tool", layout="wide", page_icon="📦")
st.title("📦 WMS Add-Picking Manual")

# --- Kết nối Google Sheets qua Secrets ---
@st.cache_resource
def init_connection():
    try:
        if "gcp_service_account" in st.secrets:
            info = json.loads(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
            return gspread.authorize(creds)
        else:
            st.error("Chưa cấu hình Google Credentials trong Secrets!")
            return None
    except Exception as e:
        st.error(f"Lỗi cấu hình Google Service Account: {e}")
        return None

client = init_connection()

OUTPUT_SHEET_ID = '1O_nlMx5ClZMtVXoT5ZiBm886d-FqzUoDARChePd560g'
COOKIE_SHEET_ID = '1QRaq07g9d14bw_rpW0Q-c8f7e1qRYQRq8_vI426yUro'

# --- Các hàm xử lý API (Giữ nguyên Headers của bạn) ---

def get_headers():
    try:
        sheet = client.open_by_key(COOKIE_SHEET_ID).worksheet('WMS')
        cookie = sheet.acell('A2').value
        # Giữ nguyên toàn bộ Headers bạn cung cấp, không thêm bớt
        return {
            "Content-Type": "application/json",
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
        }
    except Exception as e:
        st.error(f"Lỗi lấy Cookie từ Google Sheet: {e}")
        return None

def search_api(sku):
    headers = get_headers()
    if not headers:
        return None
        
    url = f"https://wms.ssc.shopee.vn/api/v2/apps/process/inventory/inventorymap/search_onhand_map?count=100&pageno=1&sku_upc_code={sku}&include_batch=N"
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return res.json().get("data", {}).get("list", [])
        elif res.status_code == 403:
            st.error("🚫 Lỗi 403: Cookie bị Shopee từ chối (Có thể do sai IP máy chủ Streamlit hoặc Cookie hết hạn).")
            return None
        else:
            st.error(f"Lỗi kết nối API: mã lỗi {res.status_code}")
            return None
    except Exception as e:
        st.error(f"Lỗi thực thi Request: {e}")
        return None

# --- Giao diện Web ---
col1, col2 = st.columns([3, 1])

with col1:
    # Cho phép tìm kiếm bằng cách nhấn Enter hoặc nhấn nút
    sku_input = st.text_input("Nhập SKU hoặc UPC:", key="sku_input_val")

with col2:
    st.write("##") # Căn lề nút bấm
    btn_search = st.button("Tìm kiếm")

if btn_search or (sku_input and st.session_state.sku_input_val):
    target_sku = sku_input if sku_input else st.session_state.sku_input_val
    if target_sku:
        with st.spinner(f"Đang quét dữ liệu cho {target_sku}..."):
            results = search_api(target_sku)
            
            if results:
                st.success(f"Tìm thấy dữ liệu cho SKU: {target_sku}")
                df = pd.DataFrame(results)
                
                # Hiển thị bảng dữ liệu với các cột quan trọng
                cols_to_show = ['sku_id', 'location_id', 'zone_id', 'on_hand_quantity']
                # Kiểm tra nếu các cột tồn tại trong kết quả trả về
                available_cols = [c for c in cols_to_show if c in df.columns]
                st.dataframe(df[available_cols], use_container_width=True)
                
                # Tại đây bạn có thể thêm logic append_rows_to_sheet của bạn
            else:
                st.warning("Không tìm thấy kết quả hoặc lỗi Cookie.")

st.divider()

if st.button("Tổng hợp dữ liệu (Consolidate)"):
    st.info("Đang thực hiện lệnh tổng hợp dữ liệu... Vui lòng đợi.")
    # Gọi hàm consolidate_data của bạn tại đây
