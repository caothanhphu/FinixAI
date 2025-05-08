# src/config.py

import os
from dotenv import load_dotenv

# Xác định đường dẫn đến thư mục gốc của dự án
# Giả sử config.py nằm trong src/, thì thư mục gốc là cha của src/
PROJECT_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Đường dẫn đến tệp .env
# Tệp .env nên nằm ở thư mục gốc của dự án
DOTENV_PATH = os.path.join(PROJECT_ROOT_DIR, '.env')

# Tải các biến môi trường từ tệp .env
# Nếu tệp .env không tồn tại, load_dotenv() sẽ không báo lỗi mà chỉ không làm gì cả.
# Các biến môi trường đã được set ở cấp hệ thống sẽ được ưu tiên hơn so với tệp .env.
if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
    print(f"Đã tải biến môi trường từ: {DOTENV_PATH}")
else:
    # Vẫn gọi load_dotenv() phòng trường hợp biến môi trường được cung cấp theo cách khác (vd: Docker, Heroku)
    # Hoặc nếu bạn không muốn dựa vào file .env cụ thể cho production.
    load_dotenv() 
    print(f"Không tìm thấy tệp .env tại {DOTENV_PATH}. Đang cố gắng tải biến môi trường hệ thống (nếu có).")


# --- Cấu hình kết nối PostgreSQL ---
# Lấy giá trị từ biến môi trường, với giá trị mặc định nếu không tìm thấy
DB_HOST = os.getenv("PG_HOST", "localhost")
DB_NAME = os.getenv("PG_DATABASE", "exchange_db_vcb")
DB_USER = os.getenv("PG_USER", "postgres") # Giá trị mặc định an toàn hơn
DB_PASSWORD = os.getenv("PG_PASSWORD") # Không nên có giá trị mặc định cho password
DB_PORT = os.getenv("PG_PORT", "5432")

# --- Các cấu hình khác (ví dụ) ---
# API_KEY = os.getenv("API_KEY")
# DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() in ('true', '1', 't')


# Kiểm tra xem password có được cung cấp không (quan trọng cho kết nối DB)
if DB_PASSWORD is None:
    print("CẢNH BÁO: Biến môi trường PG_PASSWORD chưa được thiết lập.")
    # Bạn có thể quyết định dừng chương trình ở đây nếu password là bắt buộc
    # raise ValueError("PG_PASSWORD is not set in the environment variables or .env file")

if __name__ == '__main__':
    # Phần này để kiểm tra nhanh xem config có được tải đúng không
    print("\n--- KIỂM TRA CẤU HÌNH ---")
    print(f"PROJECT_ROOT_DIR: {PROJECT_ROOT_DIR}")
    print(f"DOTENV_PATH: {DOTENV_PATH}")
    print(f"DB_HOST: {DB_HOST}")
    print(f"DB_NAME: {DB_NAME}")
    print(f"DB_USER: {DB_USER}")
    # Không in DB_PASSWORD ra màn hình vì lý do bảo mật
    print(f"DB_PASSWORD được đặt: {'Có' if DB_PASSWORD else 'Không'}")
    print(f"DB_PORT: {DB_PORT}")
    # print(f"API_KEY: {API_KEY}")
    # print(f"DEBUG_MODE: {DEBUG_MODE} (type: {type(DEBUG_MODE)})")