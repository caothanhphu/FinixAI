import requests
import re
from datetime import datetime # Chỉ dùng datetime để parse timestamp từ API

VCB_API_URL = "https://www.vietcombank.com.vn/api/exchangerates"

def format_number_from_string(value_str):
    if not value_str or value_str.strip() == '-':
        return None
    try:
        cleaned_str = value_str.replace(',', '')
        return float(cleaned_str)
    except ValueError:
        print(f"Không thể chuyển đổi '{value_str}' thành số.")
        return None

def fetch_exchange_rates_from_vcb_api():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }
    print(f"Đang gửi yêu cầu tới API Vietcombank: {VCB_API_URL}")
    try:
        response = requests.get(VCB_API_URL, headers=headers, timeout=20)
        response.raise_for_status()
        api_data = response.json()
    except requests.exceptions.Timeout:
        print("Lỗi: Yêu cầu tới API Vietcombank bị timeout.")
        return None, None
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi gọi API Vietcombank: {e}")
        return None, None
    except ValueError as e: # Cho json.loads()
        print(f"Lỗi khi phân tích JSON từ API Vietcombank: {e}")
        return None, None

    if not api_data or 'Data' not in api_data or not api_data['Data']:
        print("Không tìm thấy mục 'Data' hoặc 'Data' rỗng trong phản hồi API.")
        return None, None

    source_update_time_str_for_db = "Không xác định" # Chuỗi sẽ được parse bởi database.py
    api_time_raw = api_data.get('Time') # Ví dụ: "/Date(1715128500000+0700)/"
    if api_time_raw:
        match = re.search(r"\((\d+)([+-]\d{4})?\)", api_time_raw)
        if match:
            timestamp_ms = int(match.group(1))
            timestamp_s = timestamp_ms / 1000
            try:
                # datetime.fromtimestamp() sẽ tạo datetime object theo múi giờ của máy chạy code.
                # Giả sử máy chạy code là GMT+7 (giờ VCB), thì đây là thời gian VCB công bố.
                dt_object_local = datetime.fromtimestamp(timestamp_s)
                source_update_time_str_for_db = dt_object_local.strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                print(f"Lỗi khi chuyển đổi timestamp từ API: {e}")
        else:
            print(f"Định dạng thời gian từ API không khớp: {api_time_raw}")
    else:
        print("Không tìm thấy thông tin 'Time' trong phản hồi API.")

    extracted_rates = []
    for item in api_data['Data']:
        currency_code = item.get('code')
        currency_name = item.get('name')
        buy_cash_str = item.get('buyCash', '')
        buy_transfer_str = item.get('buyTransfer', '')
        sell_str = item.get('sell', '')

        buy_cash_val = format_number_from_string(buy_cash_str)
        buy_transfer_val = format_number_from_string(buy_transfer_str)
        sell_val = format_number_from_string(sell_str)

        if currency_code and currency_name and sell_val is not None:
            extracted_rates.append({
                'code': currency_code,
                'name': currency_name,
                'buy_cash': buy_cash_val,
                'buy_transfer': buy_transfer_val,
                'sell': sell_val
            })
        else:
            print(f"Bỏ qua ngoại tệ không đủ thông tin: Code={currency_code}, Name={currency_name}, Sell={sell_str}")
            
    return extracted_rates, source_update_time_str_for_db