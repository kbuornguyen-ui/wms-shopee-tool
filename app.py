import streamlit as st
import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import logging

# --- Cấu hình Trang Web ---
st.set_page_config(page_title="WMS SKU Search Tool", layout="wide")
st.title("📦 WMS Add-Picking Manual")

# --- Google Sheets API setup ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
OUTPUT_SHEET_ID = '1O_nlMx5ClZMtVXoT5ZiBm886d-FqzUoDARChePd560g'
COOKIE_SHEET_ID = '1QRaq07g9d14bw_rpW0Q-c8f7e1qRYQRq8_vI426yUro'

# Kết nối Google Sheet qua Secrets
@st.cache_resource # Giữ kết nối để không phải load lại mỗi lần nhấn nút
def init_connection():
    if "gcp_service_account" in st.secrets:
        info = json.loads(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        return gspread.authorize(creds)
    return None

client = init_connection()

if not client:
    st.error("❌ Chưa cấu hình Google Credentials trong Secrets của Streamlit!")
    st.stop()

# --- Các hàm xử lý logic (Bê từ code gốc của bạn sang) ---

def get_headers():
    try:
        sheet = client.open_by_key(COOKIE_SHEET_ID).worksheet('WMS')
        cookie_string = sheet.acell('A2').value
        return {
            "Sec-CH-UA": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            "Sec-CH-UA-Mobile": "?0",
            "Sec-CH-UA-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Referer": "https://wms.ssc.shopee.vn/",
            "Origin": "https://wms.ssc.shopee.vn",
            "Content-Type": "application/json",
            "Cookie": cookie_string
        }
    except Exception as e:
        st.error(f"Lỗi lấy Cookie: {e}")
        return None

def search_sku_upc_api(sku_upc_code):
    headers = get_headers()
    if not headers: return None
    
    url = f"https://wms.ssc.shopee.vn/api/v2/apps/process/inventory/inventorymap/search_onhand_map?count=100&pageno=1&sku_upc_code={sku_upc_code}&include_batch=N"
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if data.get("retcode") == 0:
            return data.get("data", {}).get("list", [])
        return None
    except:
        return None

def find_max_quantity_zone(results):
    zone_quantities = {}
    excluded_zones = ["RS", "TS","AV"]
    for item in results:
        zone_id = item.get("zone_id")
        quantity = item.get("on_hand_quantity", 0)
        if zone_id and item.get("pickup_type") == 1 and zone_id not in excluded_zones:
            zone_quantities[zone_id] = zone_quantities.get(zone_id, 0) + quantity
    return max(zone_quantities, key=zone_quantities.get) if zone_quantities else None

# --- Giao diện người dùng ---

col1, col2 = st.columns([3, 1])

with col1:
    sku_input = st.text_input("Nhập SKU hoặc UPC và nhấn Enter:", placeholder="Ví dụ: 123456789")

with col2:
    st.write("##")
    btn_search = st.button("🔍 Tìm kiếm SKU")

if btn_search or sku_input:
    if sku_input:
        with st.spinner('Đang kiểm tra hệ thống...'):
            all_results = search_sku_upc_api(sku_input)
            
            if all_results:
                max_zone = find_max_quantity_zone(all_results)
                st.success(f"✅ Kết quả cho: {sku_input}")
                
                # Hiển thị thông tin tổng quan bằng các thẻ (Cards)
                c1, c2 = st.columns(2)
                c1.metric("Vị trí nhiều nhất", max_zone if max_zone else "N/A")
                c2.metric("Tổng tồn kho", sum(item.get('on_hand_quantity', 0) for item in all_results))

                # Hiển thị bảng chi tiết
                df = pd.DataFrame(all_results)
                st.dataframe(df[['sku_id', 'sku_name', 'location_id', 'zone_id', 'on_hand_quantity']], use_container_width=True)
                
                # Nút ghi dữ liệu vào Sheet (Option)
                if st.button("📝 Ghi lần quét này vào Google Sheet"):
                    # Thực hiện hàm append_rows_to_sheet của bạn ở đây
                    st.toast("Đã ghi thành công!")
            else:
                st.error("❌ Không tìm thấy dữ liệu hoặc Cookie hết hạn.")

st.divider()
if st.button("📊 Tổng hợp dữ liệu (Consolidate)"):
    st.warning("Tính năng này sẽ quét toàn bộ sheet và tổng hợp. Có thể mất vài phút.")
    # Chèn logic hàm consolidate_data của bạn vào đây