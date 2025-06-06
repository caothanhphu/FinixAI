-- Xóa bảng nếu tồn tại để tạo lại (cẩn thận nếu có dữ liệu quan trọng)
-- DROP TABLE IF EXISTS ExchangeRates CASCADE;
-- DROP TABLE IF EXISTS Currencies CASCADE;

-- Bảng lưu thông tin các loại tiền tệ
CREATE TABLE IF NOT EXISTS Currencies (
    id SERIAL PRIMARY KEY,  -- Tự động tăng, tương đương AUTOINCREMENT của SQLite
    code VARCHAR(10) UNIQUE NOT NULL, -- Mã ngoại tệ, ví dụ: USD, EUR
    name VARCHAR(255) NOT NULL       -- Tên đầy đủ của ngoại tệ
);

-- Bảng lưu lịch sử tỷ giá
CREATE TABLE IF NOT EXISTS ExchangeRates (
    id SERIAL PRIMARY KEY,
    currency_id INTEGER NOT NULL,
    -- Lưu thời gian ứng dụng ghi nhận, mặc định là thời gian hiện tại với múi giờ
    date_recorded TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    buy_cash NUMERIC(18, 4),         -- Tỷ giá mua tiền mặt (ví dụ: 18 chữ số tổng, 4 chữ số thập phân)
    buy_transfer NUMERIC(18, 4),     -- Tỷ giá mua chuyển khoản
    sell NUMERIC(18, 4) NOT NULL,    -- Tỷ giá bán ra
    -- Thời gian Vietcombank cập nhật, có thể NULL nếu không lấy được
    source_update_time TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_currency
        FOREIGN KEY (currency_id)
        REFERENCES Currencies (id)
        ON DELETE CASCADE -- Nếu một currency bị xóa, các tỷ giá liên quan cũng bị xóa
);

-- Tạo index để tăng tốc độ truy vấn (tùy chọn nhưng khuyến khích)
CREATE INDEX IF NOT EXISTS idx_currencies_code ON Currencies (code);
CREATE INDEX IF NOT EXISTS idx_exchangerates_currency_id ON ExchangeRates (currency_id);
CREATE INDEX IF NOT EXISTS idx_exchangerates_date_recorded ON ExchangeRates (date_recorded DESC);
CREATE INDEX IF NOT EXISTS idx_exchangerates_source_update_time ON ExchangeRates (source_update_time DESC);

-- Thông báo tạo bảng thành công (tùy chọn)
-- SELECT 'Bảng Currencies và ExchangeRates đã được tạo/kiểm tra thành công trong PostgreSQL.' AS status;

CREATE TABLE IF NOT EXISTS GoldTypes (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) UNIQUE NOT NULL, -- Ví dụ: "Vàng SJC 1L - 10L - TP. Hồ Chí Minh"
        original_type_name VARCHAR(255),   -- Ví dụ: "Vàng SJC 1L - 10L" (tên gốc)
        city_name VARCHAR(100),            -- Ví dụ: "TP. Hồ Chí Minh"
        provider VARCHAR(50) DEFAULT 'SJC' NOT NULL -- Nhà cung cấp, mặc định SJC
    );

    CREATE TABLE IF NOT EXISTS GoldPrices (
        id SERIAL PRIMARY KEY,
        gold_type_id INTEGER NOT NULL,
        date_recorded TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
        buy_price BIGINT, -- Lưu giá trị nguyên, ví dụ 87500000
        sell_price BIGINT,
        unit VARCHAR(50) DEFAULT 'đồng/lượng',
        source_update_time TIMESTAMP WITH TIME ZONE, -- Thời gian SJC cập nhật
        CONSTRAINT fk_gold_type
            FOREIGN KEY (gold_type_id)
            REFERENCES GoldTypes (id)
            ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_goldtypes_name ON GoldTypes (name);
    CREATE INDEX IF NOT EXISTS idx_goldprices_gold_type_id ON GoldPrices (gold_type_id);
    CREATE INDEX IF NOT EXISTS idx_goldprices_date_recorded ON GoldPrices (date_recorded DESC);
