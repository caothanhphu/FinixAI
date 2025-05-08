# src/scraper.py
import requests
from datetime import datetime
import json

# URL API tỷ giá của Vietcombank
VCB_EXCHANGE_RATE_API_URL = "https://www.vietcombank.com.vn/api/exchangerates"

def fetch_exchange_rates_from_api():
    """
    Lấy dữ liệu tỷ giá từ API của Vietcombank.
    Trả về một danh sách các dictionaries chứa tỷ giá và thời gian cập nhật từ nguồn.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    # Lấy ngày hiện tại để gửi request
    current_date = datetime.now().strftime('%Y-%m-%d')
    api_url = f"{VCB_EXCHANGE_RATE_API_URL}?date={current_date}"
    
    print(f"Đang gửi yêu cầu tới API Vietcombank: {api_url}")
    try:
        response = requests.get(api_url, headers=headers, timeout=25)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        print("Lỗi: Yêu cầu tới API Vietcombank bị timeout.")
        return None, None
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi truy cập API Vietcombank: {e}")
        return None, None
    except json.JSONDecodeError as e:
        print(f"Lỗi khi phân tích JSON từ API: {e}")
        return None, None

    # Kiểm tra cấu trúc dữ liệu
    if not isinstance(data, dict) or 'Data' not in data:
        print("Dữ liệu API không đúng định dạng mong đợi.")
        return None, None

    # Lấy thời gian cập nhật từ API
    source_update_time_str = None
    if 'UpdatedDate' in data:
        try:
            # Chuyển đổi từ ISO format sang định dạng yêu-m-d H:M:S
            dt = datetime.fromisoformat(data['UpdatedDate'].replace('Z', '+00:00'))
            source_update_time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, AttributeError) as e:
            print(f"Lỗi khi xử lý thời gian cập nhật: {e}")
            source_update_time_str = "Không xác định"

    extracted_rates = []
    for item in data.get('Data', []):
        try:
            # Chuyển đổi các giá trị số
            buy_cash = float(item['cash']) if item['cash'] != "0.00" else None
            buy_transfer = float(item['transfer']) if item['transfer'] != "0.00" else None
            sell = float(item['sell']) if item['sell'] != "0.00" else None

            if item['currencyCode'] and item['currencyName'] and sell is not None:
                extracted_rates.append({
                    'code': item['currencyCode'].upper(),
                    'name': item['currencyName'],
                    'buy_cash': buy_cash,
                    'buy_transfer': buy_transfer,
                    'sell': sell
                })
        except (ValueError, KeyError) as e:
            print(f"Lỗi khi xử lý dữ liệu cho {item.get('currencyCode', 'Unknown')}: {e}")
            continue

    if not extracted_rates:
        print("Không trích xuất được bản ghi tỷ giá nào từ API.")
        return None, source_update_time_str

    return extracted_rates, source_update_time_str

def fetch_exchange_rates():
    """
    Hàm chính để lấy dữ liệu tỷ giá.
    """
    print("Sử dụng API Vietcombank để lấy tỷ giá.")
    return fetch_exchange_rates_from_api()

if __name__ == '__main__':
    # Chạy thử để kiểm tra scraper
    print("--- Chạy thử scraper ---")
    rates, update_time = fetch_exchange_rates()
    if rates:
        print(f"\nThời gian cập nhật từ VCB: {update_time}")
        print(f"Số lượng ngoại tệ lấy được: {len(rates)}")
        for i, rate in enumerate(rates[:5]):  # In 5 ngoại tệ đầu tiên
            print(f"{i+1}. {rate['name']} ({rate['code']}): "
                  f"Mua TM: {rate['buy_cash']}, "
                  f"Mua CK: {rate['buy_transfer']}, "
                  f"Bán: {rate['sell']}")
    else:
        print("\nKhông lấy được dữ liệu tỷ giá.")
    print("--- Kết thúc chạy thử scraper ---")