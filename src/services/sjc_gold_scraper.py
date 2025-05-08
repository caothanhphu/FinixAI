# src/services/sjc_gold_scraper.py
import requests
import json # Để xử lý JSON response
from datetime import datetime
# import re # Không cần re nữa nếu có key thời gian rõ ràng

SJC_PRICE_SERVICE_URL = "https://sjc.com.vn/GoldPrice/Services/PriceService.ashx"

def _convert_sjc_numeric_value(value):
    """Chuyển đổi giá trị số từ SJC (thường là float với .0000) sang integer."""
    if value is None:
        return None
    try:
        # Giá trị như 118500000.0000 sẽ được chuyển thành 118500000
        return int(float(value))
    except (ValueError, TypeError):
        # print(f"Warning: Không thể chuyển đổi giá trị SJC value: '{value}'")
        return None

def _parse_sjc_service_update_time(response_dict):
    """
    Phân tích thời gian cập nhật từ JSON response của SJC service.
    response_dict là Python dictionary đã được parse từ JSON.
    """
    if not isinstance(response_dict, dict):
        print("Lỗi: Dữ liệu phản hồi để parse thời gian không phải là dictionary.")
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S') # Fallback

    raw_time_str = response_dict.get("latestDate") # Ví dụ: "13:48 08/05/2025"
    
    if raw_time_str and isinstance(raw_time_str, str):
        try:
            # Parse định dạng "HH:MM DD/MM/YYYY"
            dt_obj_naive = datetime.strptime(raw_time_str, '%H:%M %d/%m/%Y')
            return dt_obj_naive.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError as e:
            print(f"Không parse được thời gian SJC từ service: '{raw_time_str}'. Lỗi: {e}")
            # Nếu lỗi, thử trả về chuỗi gốc hoặc một giá trị mặc định có ý nghĩa hơn
            return raw_time_str # Trả về chuỗi gốc để có thể debug
    else:
        print("Không tìm thấy key 'latestDate' hoặc giá trị không hợp lệ trong phản hồi từ service SJC.")
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S') # Fallback


def _parse_sjc_service_gold_items(response_dict):
    """
    Phân tích danh sách các loại vàng và giá từ JSON response của SJC service.
    response_dict là Python dictionary đã được parse từ JSON.
    """
    gold_prices_list = []
    
    if not isinstance(response_dict, dict):
        print("Lỗi: Dữ liệu phản hồi để parse giá vàng không phải là dictionary.")
        return gold_prices_list

    gold_items_list = response_dict.get("data") # Key "data" chứa list các loại vàng
    
    if isinstance(gold_items_list, list):
        for item in gold_items_list:
            if not isinstance(item, dict):
                # print(f"Warning: Mục item trong list 'data' không phải là dict: {item}")
                continue

            type_name_original = item.get('TypeName')
            city = item.get('BranchName', "N/A") # BranchId=1 thường là Hồ Chí Minh
            
            # Sử dụng "BuyValue" và "SellValue" vì chúng đã là số (hoặc dễ chuyển đổi)
            buy_price = _convert_sjc_numeric_value(item.get('BuyValue'))
            sell_price = _convert_sjc_numeric_value(item.get('SellValue'))

            if type_name_original and buy_price is not None and sell_price is not None:
                # Tạo tên đầy đủ, bao gồm cả thành phố để phân biệt nếu cần
                # Hoặc có thể chỉ dùng TypeName nếu nó đã đủ chi tiết
                full_type_name = f"{type_name_original} - {city}" if city != "N/A" and city not in type_name_original else type_name_original
                
                gold_prices_list.append({
                    'type_name': full_type_name,
                    'original_type': type_name_original,
                    'city': city,
                    'buy': buy_price,
                    'sell': sell_price,
                    'unit': 'đồng/lượng' # Mặc định cho SJC
                })
            # else:
                # print(f"Warning: Bỏ qua mục vàng thiếu thông tin: Type={type_name_original}, BuyV={item.get('BuyValue')}, SellV={item.get('SellValue')}")
    else:
        print("Không tìm thấy key 'data' hoặc giá trị không phải list trong phản hồi JSON từ service SJC.")
        
    return gold_prices_list


def fetch_sjc_gold_from_service():
    """
    Lấy giá vàng SJC từ PriceService.ashx bằng POST request.
    """
    payload = {
        'method': 'GetCurrentGoldPricesByBranch',
        'BranchId': '1' # BranchId=1 thường là TP.HCM hoặc chi nhánh trung tâm
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest', # Quan trọng cho các AJAX request
        'Referer': 'https://sjc.com.vn/gia-vang-online' # Trang web gốc của request
    }

    print(f"Đang gửi POST request tới SJC Price Service: {SJC_PRICE_SERVICE_URL}")
    print(f"Payload: {payload}")
    
    source_update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # Fallback
    gold_data_list = []

    try:
        response = requests.post(SJC_PRICE_SERVICE_URL, headers=headers, data=payload, timeout=20)
        response.raise_for_status()
        
        raw_response_text = response.text # Lấy text để debug nếu JSON lỗi
        response_json = response.json() # Parse JSON

        print("Phản hồi từ SJC Price Service là JSON.")
        # print(f"Dữ liệu JSON thô: {json.dumps(response_json, indent=2, ensure_ascii=False)}") # Debug: In ra JSON đẹp

        if response_json.get("success") is True:
            source_update_time = _parse_sjc_service_update_time(response_json)
            gold_data_list = _parse_sjc_service_gold_items(response_json)
            if not gold_data_list:
                 print("Lấy dữ liệu thành công nhưng không phân tích được mục giá vàng nào.")
        else:
            error_message = response_json.get("message", "Lỗi không xác định từ SJC service (success=false).")
            print(f"SJC Service báo lỗi: {error_message}")
            # source_update_time vẫn có thể có trong 'latestDate' ngay cả khi success=false
            source_update_time = _parse_sjc_service_update_time(response_json) # Thử parse thời gian
            return None, source_update_time # Trả về None cho data, nhưng có thể có thời gian

    except requests.exceptions.Timeout:
        print(f"Lỗi: Yêu cầu tới SJC Price Service ({SJC_PRICE_SERVICE_URL}) bị timeout.")
        return None, source_update_time
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi POST request tới SJC Price Service: {e}")
        return None, source_update_time
    except json.JSONDecodeError as e:
        print(f"Lỗi giải mã JSON từ SJC Price Service: {e}.")
        print(f"Phản hồi thô nhận được (đầu): {raw_response_text[:500] if raw_response_text else 'Không có'}")
        return None, source_update_time
    except Exception as e_general: # Bắt các lỗi không lường trước khác
        print(f"Lỗi không xác định khi xử lý phản hồi từ SJC Price Service: {e_general}")
        return None, source_update_time
        
    return gold_data_list, source_update_time


# Hàm chính để lấy dữ liệu giá vàng SJC
def get_sjc_gold_data():
    """
    Hàm chính để lấy dữ liệu giá vàng SJC.
    Hiện tại sử dụng POST request đến PriceService.ashx.
    """
    print("Đang lấy giá vàng SJC từ PriceService (POST)...")
    gold_data, update_time = fetch_sjc_gold_from_service()
    
    if gold_data:
        print(f"Lấy giá vàng SJC từ PriceService thành công. Thời gian SJC cập nhật: {update_time}")
    elif update_time: # Có thể có update_time ngay cả khi gold_data là None (ví dụ service báo lỗi)
        print(f"Không lấy được danh sách giá vàng chi tiết từ PriceService. Thời gian SJC (nếu có): {update_time}")
    else:
        print("Hoàn toàn không lấy được dữ liệu/thời gian từ PriceService SJC.")
        
    return gold_data, update_time


# Phần XML có thể giữ lại làm fallback nếu muốn, hoặc xóa đi nếu service mới đủ ổn định.
# SJC_XML_URL = "https://sjc.com.vn/xml/tygiavang.xml"
# def _parse_sjc_xml_update_time(time_str_raw): ...
# def fetch_sjc_gold_from_xml(): ...


if __name__ == '__main__':
    # Chạy thử để kiểm tra scraper SJC với PriceService
    print("--- Chạy thử scraper giá vàng SJC (sử dụng PriceService) ---")
    all_gold_data, sjc_update_time_from_service = get_sjc_gold_data()
    if all_gold_data:
        print(f"\nThời gian SJC cập nhật (từ Service): {sjc_update_time_from_service}")
        print(f"Số loại giá vàng lấy được: {len(all_gold_data)}")
        for i, data_item in enumerate(all_gold_data[:10]): # In 10 mục đầu tiên
            buy_display = f"{data_item['buy']:,}" if data_item['buy'] is not None else "-"
            sell_display = f"{data_item['sell']:,}" if data_item['sell'] is not None else "-"
            print(f"{i+1}. Loại: {data_item['type_name']}, Mua: {buy_display}, Bán: {sell_display} ({data_item['unit']})")
    elif sjc_update_time_from_service: # Có thể có thời gian dù không có data list
         print(f"\nKhông lấy được danh sách giá vàng. Thời gian SJC cập nhật (từ Service): {sjc_update_time_from_service}")
    else:
        print("\nKhông lấy được dữ liệu giá vàng SJC từ PriceService.")
    print("--- Kết thúc chạy thử scraper giá vàng SJC ---")