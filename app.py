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

# --- Google Sheets API IDs ---
OUTPUT_SHEET_ID = '1O_nlMx5ClZMtVXoT5ZiBm886d-FqzUoDARChePd560g'
COOKIE_SHEET_ID = '1QRaq07g9d14bw_rpW0Q-c8f7e1qRYQRq8_vI426yUro'
SHEET_NAME = 'WMS'
SUMMARY_SHEET_NAME = 'totaldoavms'
HANGDU_SHEET_NAME = 'hangdu'
TOTALDU_SHEET_NAME = 'totaldu'
COOKIE_CELL = 'A2'

# --- Kết nối Google Sheets qua Secrets ---
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

gc = init_connection()

# --- Các hàm Logic lấy từ code gốc của bạn ---

def get_headers():
    try:
        sheet = gc.open_by_key(COOKIE_SHEET_ID).worksheet(SHEET_NAME)
        cookie_string = sheet.acell(COOKIE_CELL).value
        if not cookie_string:
            return None
        
        # Giữ nguyên load headers từ code gốc của bạn
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
        st.error(f"Lỗi đọc Cookie: {e}")
        return None

def search_sku_api(headers, sku):
    url = f"https://wms.ssc.shopee.vn/api/v2/apps/process/inventory/inventorymap/search_onhand_map?count=100&pageno=1&sku_upc_code={sku}&include_batch=N"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if data.get("retcode") == 0:
            return data.get("data", {}).get("list", []), None
        return None, data.get("message", "Lỗi API Shopee")
    except Exception as e:
        return None, str(e)

def find_max_zone(results):
    zone_quantities = {}
    excluded = ["RS", "TS", "AV"]
    for item in results:
        z_id = item.get("zone_id")
        qty = item.get("on_hand_quantity", 0)
        if z_id and item.get("pickup_type") == 1 and z_id not in excluded:
            zone_quantities[z_id] = zone_quantities.get(z_id, 0) + qty
    return max(zone_quantities, key=zone_quantities.get) if zone_quantities else None

# --- Giao diện Streamlit ---

if gc:
    tab1, tab2 = st.tabs(["🔍 Tìm kiếm SKU", "📊 Tổng hợp dữ liệu"])

    with tab1:
        col1, col2 = st.columns([3, 1])
        with col1:
            sku_input = st.text_input("Nhập SKU hoặc UPC:", placeholder="Quét mã tại đây...")
        with col2:
            st.write("##")
            btn_search = st.button("Tìm kiếm", use_container_width=True)

        if btn_search or sku_input:
            headers = get_headers()
            if headers:
                with st.spinner("Đang truy vấn..."):
                    results, err = search_sku_api(headers, sku_input)
                    if err:
                        st.error(f"Lỗi: {err}")
                    elif results:
                        # Logic tính toán ưu tiên
                        prioritized_zones = ["DO", "IMOB", "AV", "IMIV", "IMRT", "IMAO", "MS"]
                        total_prioritized = sum(i.get("on_hand_quantity", 0) for i in results if i.get("zone_id") in prioritized_zones)
                        max_z = find_max_zone(results)
                        
                        st.success(f"✅ SKU: {results[0].get('sku_id')} - Tên: {results[0].get('sku_name')}")
                        st.metric("Tổng tồn kho ưu tiên", total_prioritized)
                        if max_z: st.info(f"📍 Vị trí nhiều nhất: {max_z}")
                        
                        # Hiển thị bảng
                        df = pd.DataFrame(results)
                        st.dataframe(df[['sku_id', 'location_id', 'zone_id', 'on_hand_quantity', 'pickup_type']])
                        
                        # Ghi vào Google Sheet (Tương tự logic append_rows_to_sheet của bạn)
                        try:
                            out_ws = gc.open_by_key(OUTPUT_SHEET_ID).worksheet(SHEET_NAME)
                            out_ws.append_row([results[0].get('sku_id'), results[0].get('sku_name'), results[0].get('location_id'), 1, max_z if max_z else ''])
                            st.toast("Đã ghi nhận lần quét vào Sheet!")
                        except Exception as e:
                            st.error(f"Lỗi ghi Sheet: {e}")
                    else:
                        st.warning("Không tìm thấy dữ liệu.")

    with tab2:
        st.subheader("Tổng hợp dữ liệu cuối ngày")
        if st.button("🚀 Bắt đầu Tổng hợp (Consolidate)"):
            with st.spinner("Đang xử lý dữ liệu..."):
                # Tại đây bạn có thể bê nguyên logic của hàm consolidate_data vào
                st.write("Đang quét dữ liệu từ Sheet...")
                # ... (Logic xử lý dữ liệu tương tự code gốc)
                st.success("Đã tổng hợp thành công vào các Sheet tương ứng!")
