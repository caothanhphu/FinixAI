from datetime import datetime
import services.scraper_vcb as scraper # Đã cập nhật cho PostgreSQL
import services.sjc_gold_scraper as scraper_sjc # Đã cập nhật cho PostgreSQL
import database # database.py đã được cập nhật cho PostgreSQL
import sys # Để thoát nếu kết nối DB thất bại

def run_update_exchange_rates():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --- Bắt đầu quá trình cập nhật tỷ giá Vietcombank (PostgreSQL) ---")


    # 1. Lấy dữ liệu tỷ giá mới nhất từ Vietcombank API
    print("\nĐang lấy dữ liệu tỷ giá từ Vietcombank...")
    fetched_rates, source_update_time_str = scraper.fetch_exchange_rates_from_api()

    if fetched_rates:
        print(f"Lấy dữ liệu thành công. Thời gian cập nhật từ Vietcombank (chuỗi gốc): {source_update_time_str}.")
        print(f"Số lượng ngoại tệ thu được: {len(fetched_rates)}")
        
        # 2. Lưu dữ liệu vào cơ sở dữ liệu PostgreSQL
        print("\nĐang lưu dữ liệu vào cơ sở dữ liệu PostgreSQL...")
        successful_inserts = 0
        for rate_data in fetched_rates:
            currency_id = database.get_or_create_currency(rate_data['code'], rate_data['name'])
            if currency_id:
                database.insert_exchange_rate(
                    currency_id=currency_id,
                    buy_cash=rate_data['buy_cash'],
                    buy_transfer=rate_data['buy_transfer'],
                    sell=rate_data['sell'],
                    source_update_time_str=source_update_time_str # Truyền chuỗi, database.py sẽ parse
                )
                successful_inserts += 1
            else:
                print(f"Không thể lấy hoặc tạo currency_id cho {rate_data['code']} trong PostgreSQL.")
        print(f"Đã thực hiện ghi {successful_inserts} bản ghi tỷ giá vào PostgreSQL.")
    else:
        print("Không lấy được dữ liệu tỷ giá từ Vietcombank. Bỏ qua việc lưu vào CSDL.")

    # --- Lấy và lưu giá vàng SJC ---
    print("\n--- Cập nhật Giá vàng SJC ---")
    sjc_gold_data, sjc_source_time = scraper_sjc.get_sjc_gold_data()

    if sjc_gold_data:
        print(f"Lấy giá vàng SJC thành công. Thời gian SJC cập nhật: {sjc_source_time}.")
        print(f"Số loại giá vàng SJC: {len(sjc_gold_data)}")
        for gold_item in sjc_gold_data:
            gold_type_id = database.get_or_create_gold_type(
                full_name=gold_item['type_name'],
                original_type_name=gold_item['original_type'],
                city_name=gold_item['city'],
                provider='SJC'
            )
            if gold_type_id:
                database.insert_gold_price(
                    gold_type_id=gold_type_id,
                    buy_price=gold_item['buy'],
                    sell_price=gold_item['sell'],
                    unit=gold_item['unit'],
                    source_update_time_str=sjc_source_time
                )
        print(f"Đã lưu {len(sjc_gold_data)} bản ghi giá vàng SJC.")
    else:
        print("Không lấy được dữ liệu giá vàng từ SJC.")

    # 3. Hiển thị tỷ giá mới nhất vừa được lưu (hoặc đã có) trong CSDL PostgreSQL
    print("\n--- Tỷ giá mới nhất hiện có trong Cơ sở dữ liệu PostgreSQL ---")
    latest_rates_from_db = database.get_latest_rates()
    if latest_rates_from_db:
        for rate in latest_rates_from_db: # rate giờ là RealDictRow, truy cập như dict
            buy_cash_display = f"{rate['buy_cash']:.2f}" if rate['buy_cash'] is not None else '-'
            buy_transfer_display = f"{rate['buy_transfer']:.2f}" if rate['buy_transfer'] is not None else '-'
            sell_display = f"{rate['sell']:.2f}" if rate['sell'] is not None else '-'
            
            # Định dạng lại thời gian từ TIMESTAMPTZ để hiển thị đẹp hơn
            # Đối tượng datetime từ psycopg2 đã là "aware" (có tzinfo)
            date_recorded_display = rate['date_recorded'].strftime('%Y-%m-%d %H:%M:%S %Z') if rate['date_recorded'] else 'N/A'
            source_update_display = rate['source_update_time'].strftime('%Y-%m-%d %H:%M:%S %Z') if rate['source_update_time'] else 'N/A'

            print(f"- {rate['currency_name']} ({rate['currency_code']}): "
                  f"Mua TM: {buy_cash_display}, "
                  f"Mua CK: {buy_transfer_display}, "
                  f"Bán: {sell_display} VND. "
                  f"(VCB cập nhật: {source_update_display}, App ghi lúc: {date_recorded_display})")
    else:
        print("Không có dữ liệu tỷ giá nào trong cơ sở dữ liệu PostgreSQL.")

    print("\n--- Giá Vàng SJC Mới nhất từ CSDL ---")
    latest_sjc_gold_db = database.get_latest_gold_prices()
    if latest_sjc_gold_db:
        for gold in latest_sjc_gold_db:
            buy_price_display = f"{gold['buy_price']:,}" if gold['buy_price'] is not None else '-'
            sell_price_display = f"{gold['sell_price']:,}" if gold['sell_price'] is not None else '-'
            date_recorded_display = gold['date_recorded'].strftime('%Y-%m-%d %H:%M:%S %Z') if gold['date_recorded'] else 'N/A'
            source_update_display = gold['source_update_time'].strftime('%Y-%m-%d %H:%M:%S %Z') if gold['source_update_time'] else 'N/A'
            print(f"- {gold['gold_type_name']} (Provider: {gold['provider']}): Mua: {buy_price_display}, Bán: {sell_price_display} ({gold['unit']}). (SJC: {source_update_display}, App: {date_recorded_display})")
    else:
        print("Không có dữ liệu giá vàng SJC trong CSDL.")
    
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --- Hoàn tất quá trình cập nhật (PostgreSQL) ---")

if __name__ == "__main__":
    # Rất quan trọng: Đảm bảo bạn đã cấu hình đúng các biến môi trường
    # PG_HOST, PG_DATABASE, PG_USER, PG_PASSWORD, PG_PORT
    # hoặc sửa trực tiếp trong file database.py (không khuyến khích cho production)
    # Ví dụ set biến môi trường (chỉ cho mục đích demo, nên set bên ngoài script):
    # os.environ["PG_USER"] = "your_user"
    # os.environ["PG_PASSWORD"] = "your_secret_password"
    # os.environ["PG_DATABASE"] = "vcb_rates_db"
    
    run_update_exchange_rates()