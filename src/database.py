import psycopg2
import psycopg2.extras # Để sử dụng RealDictCursor
from datetime import datetime, timezone # Thêm timezone
import config
import os

# --- Cấu hình kết nối PostgreSQL ---
# Sử dụng biến môi trường để bảo mật thông tin nhạy cảm
DB_HOST = os.getenv("PG_HOST", "localhost")
DB_NAME = os.getenv("PG_DATABASE", "exchange_db_vcb") # Đặt tên DB của bạn
DB_USER = os.getenv("PG_USER", "postgres")      # Thay bằng user của bạn
DB_PASSWORD = os.getenv("PG_PASSWORD", "your_password") # Thay bằng password của bạn
DB_PORT = os.getenv("PG_PORT", "5432")


def get_db_connection():
    """Tạo và trả về một kết nối đến cơ sở dữ liệu PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Lỗi nghiêm trọng: Không thể kết nối đến PostgreSQL server.")
        print(f"Thông tin kết nối: Host={DB_HOST}, DB={DB_NAME}, User={DB_USER}, Port={DB_PORT}, Password={DB_PASSWORD}")
        print(f"Chi tiết lỗi: {e}")
        print("Vui lòng kiểm tra:")
        print("1. PostgreSQL server có đang chạy không.")
        print("2. Thông tin kết nối (host, database, user, password, port) có chính xác không.")
        print("3. Quyền truy cập của user vào database.")
        print("4. Cấu hình pg_hba.conf của PostgreSQL (nếu kết nối từ máy khác).")
        raise  # Ném lại lỗi để chương trình chính có thể dừng lại

def create_tables_postgres():
    """
    Tạo các bảng trong cơ sở dữ liệu PostgreSQL nếu chúng chưa tồn tại.
    """
    # Tạo bảng cho tỷ giá
    sql_script = """
    CREATE TABLE IF NOT EXISTS Currencies (
        id SERIAL PRIMARY KEY,
        code VARCHAR(10) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS ExchangeRates (
        id SERIAL PRIMARY KEY,
        currency_id INTEGER NOT NULL,
        date_recorded TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
        buy_cash NUMERIC(18, 4),
        buy_transfer NUMERIC(18, 4),
        sell NUMERIC(18, 4) NOT NULL,
        source_update_time TIMESTAMP WITH TIME ZONE,
        CONSTRAINT fk_currency
            FOREIGN KEY (currency_id)
            REFERENCES Currencies (id)
            ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_currencies_code ON Currencies (code);
    CREATE INDEX IF NOT EXISTS idx_exchangerates_currency_id ON ExchangeRates (currency_id);
    CREATE INDEX IF NOT EXISTS idx_exchangerates_date_recorded ON ExchangeRates (date_recorded DESC);
    CREATE INDEX IF NOT EXISTS idx_exchangerates_source_update_time ON ExchangeRates (source_update_time DESC);
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql_script)
        conn.commit()
        print(f"Đã kiểm tra/khởi tạo bảng tỷ giá trong PostgreSQL database '{DB_NAME}'.")
    except psycopg2.Error as e:
        print(f"Lỗi khi tạo bảng tỷ giá trong PostgreSQL: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    
    # Tạo bảng cho giá vàng
    create_gold_tables()

def get_or_create_currency(code, name):
    """
    Lấy ID của một loại tiền tệ dựa trên mã của nó trong PostgreSQL.
    Nếu không tồn tại, tạo mới và trả về ID.
    Sử dụng 'ON CONFLICT DO NOTHING' hoặc 'RETURNING id' để xử lý hiệu quả.
    """
    conn = None
    currency_id = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Thử SELECT trước để tránh ghi log không cần thiết nếu đã tồn tại
            cursor.execute("SELECT id FROM Currencies WHERE code = %s", (code,))
            row = cursor.fetchone()
            if row:
                currency_id = row[0]
            else:
                # Nếu không có, INSERT và lấy ID trả về.
                # Xử lý trường hợp đồng thời (race condition) bằng cách bắt UniqueViolation.
                try:
                    cursor.execute(
                        "INSERT INTO Currencies (code, name) VALUES (%s, %s) RETURNING id",
                        (code, name)
                    )
                    currency_id = cursor.fetchone()[0]
                    conn.commit()
                    print(f"Đã thêm ngoại tệ mới vào PostgreSQL: {name} ({code}) với ID {currency_id}")
                except psycopg2.errors.UniqueViolation: # Bắt lỗi cụ thể
                    conn.rollback() # Quan trọng: rollback transaction bị lỗi
                    # Ngoại tệ đã được thêm bởi một tiến trình khác, thử lấy lại ID
                    cursor.execute("SELECT id FROM Currencies WHERE code = %s", (code,))
                    row_after_conflict = cursor.fetchone()
                    if row_after_conflict:
                        currency_id = row_after_conflict[0]
                        print(f"Ngoại tệ {code} đã tồn tại (xử lý race condition), ID: {currency_id}")
                    else:
                        # Trường hợp này không nên xảy ra nếu UniqueViolation là do code
                        print(f"LỖI NGHIÊM TRỌNG: Không tìm thấy currency {code} sau khi xử lý UniqueViolation.")
                except psycopg2.Error as e_insert: # Bắt các lỗi khác khi insert
                    conn.rollback()
                    print(f"Lỗi khi INSERT currency '{code}': {e_insert}")

    except psycopg2.Error as e:
        print(f"Lỗi CSDL khi get/create currency '{code}': {e}")
        if conn: # Đảm bảo conn tồn tại trước khi rollback
            conn.rollback()
    finally:
        if conn:
            conn.close()
    return currency_id

def _parse_datetime_for_postgres(time_str_from_api):
    """
    Chuyển đổi chuỗi thời gian (từ scraper) thành đối tượng datetime aware (có múi giờ).
    Vietcombank API trả về thời gian dạng Unix timestamp cho múi giờ +07:00.
    Scraper đã chuyển nó thành chuỗi dạng "YYYY-MM-DD HH:MM:SS" theo giờ địa phương của máy chạy scraper.
    Giả định máy chạy scraper có múi giờ là GMT+7 (Asia/Ho_Chi_Minh).
    """
    if not time_str_from_api or time_str_from_api == "Không xác định":
        return None
    try:
        # Chuỗi thời gian từ scraper là giờ địa phương (đã được xử lý từ timestamp GMT+7)
        dt_naive = datetime.strptime(time_str_from_api, '%Y-%m-%d %H:%M:%S')
        # Gán múi giờ GMT+7 cho nó để thành "aware" datetime
        # (Vì source_update_time của VCB là giờ Việt Nam)
        dt_aware = dt_naive.replace(tzinfo=timezone(datetime.now().astimezone().utcoffset()))
        # Hoặc cụ thể hơn nếu biết chắc là GMT+7
        # dt_aware = dt_naive.replace(tzinfo=timezone(timedelta(hours=7)))
        return dt_aware
    except ValueError:
        print(f"Không thể phân tích chuỗi thời gian '{time_str_from_api}' cho source_update_time.")
        return None


def insert_exchange_rate(currency_id, buy_cash, buy_transfer, sell, source_update_time_str):
    """Chèn một bản ghi tỷ giá mới vào bảng ExchangeRates trong PostgreSQL."""
    conn = None
    try:
        conn = get_db_connection()
        # date_recorded sẽ được PostgreSQL tự động gán với DEFAULT CURRENT_TIMESTAMP (bao gồm múi giờ)
        
        source_update_time_aware = _parse_datetime_for_postgres(source_update_time_str)

        with conn.cursor() as cursor:
            sql = """
            INSERT INTO ExchangeRates 
                (currency_id, buy_cash, buy_transfer, sell, source_update_time)
            VALUES (%s, %s, %s, %s, %s) 
            """
            # psycopg2 sẽ tự động chuyển None thành NULL trong SQL.
            # Kiểu NUMERIC trong PG sẽ chấp nhận float từ Python.
            # Kiểu TIMESTAMP WITH TIME ZONE sẽ chấp nhận datetime object "aware".
            cursor.execute(sql, (
                currency_id,
                buy_cash,
                buy_transfer,
                sell,
                source_update_time_aware
            ))
        conn.commit()
    except psycopg2.Error as e:
        print(f"Lỗi khi chèn tỷ giá vào PostgreSQL cho currency_id {currency_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def get_latest_rates():
    """Lấy các bản ghi tỷ giá mới nhất cho mỗi loại tiền tệ từ PostgreSQL."""
    conn = None
    rates = []
    try:
        conn = get_db_connection()
        # Sử dụng RealDictCursor để lấy kết quả dưới dạng dictionary (giống đối tượng hơn)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            # DISTINCT ON (column) chỉ giữ lại hàng đầu tiên cho mỗi nhóm giá trị duy nhất của column
            # sau khi đã ORDER BY.
            query = """
            SELECT DISTINCT ON (c.code)
                c.name AS currency_name, 
                c.code AS currency_code, 
                er.buy_cash, 
                er.buy_transfer, 
                er.sell, 
                er.date_recorded,  -- Thời gian ứng dụng ghi vào DB (đã có múi giờ)
                er.source_update_time -- Thời gian VCB cập nhật (đã có múi giờ)
            FROM ExchangeRates er
            JOIN Currencies c ON er.currency_id = c.id
            ORDER BY c.code, er.date_recorded DESC, er.id DESC; 
            -- Sắp xếp theo code, sau đó theo date_recorded mới nhất, rồi id mới nhất (để đảm bảo tính duy nhất nếu date_recorded trùng)
            """
            cursor.execute(query)
            rates = cursor.fetchall() # Trả về list của các RealDictRow
    except psycopg2.Error as e:
        print(f"Lỗi khi lấy tỷ giá mới nhất từ PostgreSQL: {e}")
    finally:
        if conn:
            conn.close()
    return rates

def create_gold_tables():
    """
    Tạo các bảng liên quan đến giá vàng trong PostgreSQL nếu chúng chưa tồn tại.
    """
    sql_script = """
    CREATE TABLE IF NOT EXISTS GoldTypes (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,  -- Đổi full_name thành name
        original_type VARCHAR(255) NOT NULL,  -- Đổi original_type_name thành original_type
        city VARCHAR(100),  -- Đổi city_name thành city
        provider VARCHAR(50) NOT NULL,
        UNIQUE(name, provider)
    );

    CREATE TABLE IF NOT EXISTS GoldPrices (
        id SERIAL PRIMARY KEY,
        gold_type_id INTEGER NOT NULL,
        date_recorded TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
        buy_price NUMERIC(18, 4),
        sell_price NUMERIC(18, 4),
        unit VARCHAR(20) NOT NULL,
        source_update_time TIMESTAMP WITH TIME ZONE,
        CONSTRAINT fk_gold_type
            FOREIGN KEY (gold_type_id)
            REFERENCES GoldTypes (id)
            ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_goldtypes_provider ON GoldTypes (provider);
    CREATE INDEX IF NOT EXISTS idx_goldprices_gold_type_id ON GoldPrices (gold_type_id);
    CREATE INDEX IF NOT EXISTS idx_goldprices_date_recorded ON GoldPrices (date_recorded DESC);
    CREATE INDEX IF NOT EXISTS idx_goldprices_source_update_time ON GoldPrices (source_update_time DESC);
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql_script)
        conn.commit()
        print(f"Đã kiểm tra/khởi tạo bảng giá vàng trong PostgreSQL database '{DB_NAME}'.")
    except psycopg2.Error as e:
        print(f"Lỗi khi tạo bảng giá vàng trong PostgreSQL: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def get_or_create_gold_type(full_name, original_type_name, city_name, provider='SJC'):
    """
    Lấy ID của một loại vàng dựa trên tên đầy đủ (tham số full_name của Python, ứng với cột 'name' trong DB).
    Nếu không tồn tại, tạo mới và trả về ID.
    """
    conn = None
    gold_type_id = None
    try:
        conn = get_db_connection()
        if conn is None: # Thêm kiểm tra nếu get_db_connection có thể trả về None
            raise ConnectionError("Không thể kết nối đến cơ sở dữ liệu.")

        with conn.cursor() as cursor:
            # Sử dụng cột 'name' trong câu lệnh SQL, giá trị lấy từ biến Python 'full_name'
            sql_select = "SELECT id FROM GoldTypes WHERE name = %s AND provider = %s"
            cursor.execute(sql_select, (full_name, provider))
            row = cursor.fetchone()
            
            if row:
                gold_type_id = row[0]
            else:
                try:
                    # Sử dụng cột 'name' trong câu lệnh SQL INSERT
                    sql_insert = """INSERT INTO GoldTypes (name, original_type_name, city_name, provider) 
                                    VALUES (%s, %s, %s, %s) RETURNING id"""
                    cursor.execute(sql_insert, (full_name, original_type_name, city_name, provider))
                    result = cursor.fetchone()
                    if result:
                        gold_type_id = result[0]
                        conn.commit()
                        # print(f"Đã thêm loại vàng mới: {full_name} (Provider: {provider}) với ID {gold_type_id}")
                    else:
                        # Trường hợp hiếm khi RETURNING id không trả về gì dù không có lỗi
                        conn.rollback() # Rollback nếu không lấy được ID
                        print(f"Lỗi: Không nhận được ID sau khi INSERT GoldType '{full_name}'.")

                except psycopg2.errors.UniqueViolation:
                    conn.rollback() # Quan trọng: rollback transaction bị lỗi
                    # print(f"Thông tin: Loại vàng '{full_name}' (Provider: {provider}) đã tồn tại do race condition hoặc đã được thêm trước đó.")
                    # Thử lấy lại ID một lần nữa sau khi rollback
                    cursor.execute(sql_select, (full_name, provider)) # Dùng lại sql_select
                    row_after_conflict = cursor.fetchone()
                    if row_after_conflict:
                        gold_type_id = row_after_conflict[0]
                    else:
                        # Điều này không nên xảy ra nếu UniqueViolation là do 'name' và 'provider'
                        print(f"LỖI NGHIÊM TRỌNG: Không tìm thấy GoldType '{full_name}' sau khi xử lý UniqueViolation.")
                except psycopg2.Error as e_insert:
                    conn.rollback()
                    print(f"Lỗi khi INSERT GoldType '{full_name}': {e_insert}")
                    
    except psycopg2.Error as e:
        # Bổ sung thêm thông tin vào lỗi để dễ debug hơn
        print(f"Lỗi CSDL khi get/create GoldType '{full_name}' (Provider: {provider}). SQL SELECT: '{sql_select if 'sql_select' in locals() else 'N/A'}'. Lỗi: {e}")
        if conn: 
            conn.rollback()
    except ConnectionError as e_conn: # Bắt lỗi ConnectionError đã thêm
        print(e_conn)
    finally:
        if conn: 
            conn.close()
    return gold_type_id

def insert_gold_price(gold_type_id, buy_price, sell_price, unit, source_update_time_str):
    """Chèn một bản ghi giá vàng mới vào bảng GoldPrices trong PostgreSQL."""
    conn = None
    try:
        conn = get_db_connection()
        source_update_time_aware = _parse_datetime_for_postgres(source_update_time_str)
        
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO GoldPrices 
                (gold_type_id, buy_price, sell_price, unit, source_update_time)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                gold_type_id,
                buy_price,
                sell_price,
                unit,
                source_update_time_aware
            ))
        conn.commit()
    except psycopg2.Error as e:
        print(f"Lỗi khi chèn giá vàng vào PostgreSQL cho gold_type_id {gold_type_id}: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def get_latest_gold_prices():
    """Lấy các bản ghi giá vàng mới nhất cho mỗi loại vàng từ PostgreSQL."""
    conn = None
    prices = []
    sql_query = "" # Khởi tạo để có thể in ra nếu lỗi
    try:
        conn = get_db_connection()
        if conn is None: # Thêm kiểm tra nếu get_db_connection có thể trả về None
            raise ConnectionError("Không thể kết nối đến cơ sở dữ liệu để lấy giá vàng.")
            
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            # Sử dụng lại CTE của bạn, đây là một cách tốt.
            # Sửa gt.city thành gt.city_name
            # Và gt.name đã đúng (trước đó có thể là gt.full_name)
            sql_query = """
            WITH latest_prices AS (
                SELECT 
                    gp.gold_type_id,
                    MAX(gp.date_recorded) as latest_date
                FROM GoldPrices gp
                GROUP BY gp.gold_type_id
            )
            SELECT 
                gp.id AS gold_price_id, -- Thêm bí danh để tránh trùng tên cột 'id' với GoldTypes.id
                gp.gold_type_id,
                gp.date_recorded,
                gp.buy_price,
                gp.sell_price,
                gp.unit,
                gp.source_update_time,
                gt.id AS gold_type_table_id, -- Thêm bí danh để phân biệt
                gt.name as gold_type_name,
                gt.original_type_name, -- Thêm cột này nếu bạn muốn hiển thị tên gốc
                gt.provider,
                gt.city_name  -- << SỬA Ở ĐÂY: gt.city THÀNH gt.city_name
            FROM GoldPrices gp
            JOIN GoldTypes gt ON gp.gold_type_id = gt.id
            JOIN latest_prices lp ON gp.gold_type_id = lp.gold_type_id 
                AND gp.date_recorded = lp.latest_date
            ORDER BY gt.provider, gt.name; 
            """
            cursor.execute(sql_query)
            prices = cursor.fetchall()
    except psycopg2.Error as e:
        print(f"Lỗi khi lấy giá vàng mới nhất từ PostgreSQL: {e}")
        print(f"SQL Query đã chạy (hoặc cố gắng chạy): \n{sql_query}") # In ra câu query để debug
    except ConnectionError as e_conn:
        print(e_conn)
    finally:
        if conn:
            conn.close()
    return prices