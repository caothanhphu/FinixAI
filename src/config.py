# src/config.py

import os
from dotenv import load_dotenv

load_dotenv()
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
    print(f"DB_HOST: {DB_HOST}")
    print(f"DB_NAME: {DB_NAME}")
    print(f"DB_USER: {DB_USER}")
    # Không in DB_PASSWORD ra màn hình vì lý do bảo mật
    print(f"DB_PASSWORD được đặt: {'Có' if DB_PASSWORD else 'Không'}")
    print(f"DB_PORT: {DB_PORT}")
    # print(f"API_KEY: {API_KEY}")
    # print(f"DEBUG_MODE: {DEBUG_MODE} (type: {type(DEBUG_MODE)})")