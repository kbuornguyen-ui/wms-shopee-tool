import streamlit as st
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# --- Cấu hình Trang Web ---
st.set_page_config(page_title="WMS SKU Search Tool", layout="wide", page_icon="📦")
st.title("📦 WMS Add-Picking Manual")

# --- Google Sheets API setup ---
OUTPUT_SHEET_ID = '1O_nlMx5ClZMtVXoT5ZiBm886d-FqzUoDARChePd560g'
COOKIE_SHEET_ID = '1QRaq07g9d14bw_rpW0Q-c8f7e1qRYQRq8_vI426yUro'

@st.cache_resource
def init_connection():
    try:
        if "gcp_service_account" in st.secrets:
            info = json.loads(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
            return gspread.authorize(creds)
        else:
            st.error("❌ Thiếu cấu hình Secrets 'gcp_service_account'!")
            return None
    except Exception as e:
        st.error(f"❌ Lỗi kết nối Google API: {e}")
        return None

client = init_connection()

# --- Hàm lấy Headers chuẩn Shopee ---
def get_headers():
    try:
        sheet = client.open_by_key(COOKIE_SHEET_ID).worksheet('WMS')
        cookie = sheet.acell('A2').value
        if not cookie:
            st.warning("⚠️ Không tìm thấy Cookie tại ô A2 của Sheet!")
            return None
        
        return {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Cookie": cookie.strip(),
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Referer": "https://wms.ssc.shopee.vn/",
            "X-Requested-With": "XMLHttpRequest"
        }
    except Exception as e:
        st.error(f"❌ Không thể đọc Sheet Cookie: {e}")
        return None

# --- Hàm gọi API Shopee ---
def search_api(sku):
    headers = get_headers()
    if not headers: return None
    
    url = f"https://wms.ssc.shopee.vn/api/v2/apps/process/inventory/inventorymap/search_onhand_map?count=100&pageno=1&sku_upc_code={sku.strip()}&include_batch=N"
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("retcode") == 0:
                return data.get("data", {}).get("list", [])
            else:
                st.error(f"🛑 Shopee báo lỗi: {data.get('msg')}")
        elif res.status_code == 403:
            st.error("🚫 Lỗi 403: Cookie đã bị Shopee từ chối (Hết hạn hoặc sai IP).")
        else:
            st.error(f"🌐 Lỗi kết nối: HTTP {res.status_code}")
    except Exception as e:
        st.error(f"💥 Lỗi hệ thống: {e}")
    return []

# --- Giao diện Web ---
col1, col2 = st.columns([4, 1])

with col1:
    sku_input = st.text_input("Nhập SKU hoặc UPC:", placeholder="Dán mã vào đây và nhấn Enter...")

with col2:
    st.write("##")
    btn_search = st.button("🔍 Tìm kiếm SKU", use_container_width=True)

if btn_search or sku_input:
    if sku_input:
        with st.spinner("🚀 Đang truy vấn dữ liệu Shopee..."):
            results = search_api(sku_input)
            if results:
                st.success(f"✅ Tìm thấy {len(results)} vị trí cho SKU: {sku_input}")
                df = pd.DataFrame(results)
                # Lọc các cột quan trọng
                display_cols = ['sku_id', 'location_id', 'zone_id', 'on_hand_quantity', 'pickup_type']
                st.dataframe(df[display_cols], use_container_width=True)
            else:
                st.info("ℹ️ Không có dữ liệu tồn kho cho mã này.")
    else:
        st.warning("⚠️ Vui lòng nhập mã SKU trước.")

st.divider()
if st.button("📊 Tổng hợp dữ liệu (Consolidate)"):
    st.info("Tính năng này đang được thiết lập...")
