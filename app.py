import streamlit as st
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# --- Cấu hình Trang Web ---
st.set_page_config(page_title="WMS Tool - Proxy Mode", layout="wide")

# --- THÔNG TIN PROXY (Thay đổi thông tin bạn mua vào đây) ---
# Định dạng: http://username:password@ip_address:port
PROXY_URL = "http://user_cua_ban:pass_cua_ban@ip_proxy:port" 

proxies = {
    "http": PROXY_URL,
    "https": PROXY_URL,
}

# --- Kết nối Google Sheets ---
@st.cache_resource
def init_connection():
    try:
        if "gcp_service_account" in st.secrets:
            info = json.loads(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
            return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi kết nối Google: {e}")
    return None

gc = init_connection()
COOKIE_SHEET_ID = '1QRaq07g9d14bw_rpW0Q-c8f7e1qRYQRq8_vI426yUro'
OUTPUT_SHEET_ID = '1O_nlMx5ClZMtVXoT5ZiBm886d-FqzUoDARChePd560g'

def get_headers():
    try:
        sheet = gc.open_by_key(COOKIE_SHEET_ID).worksheet('WMS')
        cookie = sheet.acell('A2').value
        return {
            "Content-Type": "application/json",
            "Cookie": cookie,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Referer": "https://wms.ssc.shopee.vn/",
            "Origin": "https://wms.ssc.shopee.vn"
        }
    except: return None

def search_sku_api(sku):
    headers = get_headers()
    url = f"https://wms.ssc.shopee.vn/api/v2/apps/process/inventory/inventorymap/search_onhand_map?count=100&pageno=1&sku_upc_code={sku}&include_batch=N"
    
    try:
        # Gửi yêu cầu thông qua Proxy để lấy IP Việt Nam
        res = requests.get(url, headers=headers, proxies=proxies, timeout=15)
        if res.status_code == 200:
            return res.json().get("data", {}).get("list", []), None
        return None, f"Lỗi HTTP {res.status_code}"
    except Exception as e:
        return None, str(e)

# --- Giao diện ---
st.title("📦 WMS Tool (Chạy qua Proxy VN)")

sku_input = st.text_input("Nhập SKU/UPC:")
if st.button("Tìm kiếm") or sku_input:
    if sku_input:
        results, err = search_sku_api(sku_input)
        if err:
            st.error(f"❌ Vẫn bị lỗi: {err}. Kiểm tra lại Proxy hoặc Cookie.")
        elif results:
            st.success(f"✅ Thành công! Tìm thấy {len(results)} vị trí.")
            st.dataframe(pd.DataFrame(results)[['sku_id', 'location_id', 'zone_id', 'on_hand_quantity']])
