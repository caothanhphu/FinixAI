-- Script tạo user 'exchange_user' và cấp quyền đầy đủ trên database 'ea'

-- Bắt đầu một transaction, nếu có lỗi, toàn bộ sẽ được rollback (tùy chọn nhưng khuyến khích)
BEGIN;

-- 1. Tạo người dùng mới 'exchange_user'
-- LƯU Ý: Thay 'MẬT_KHẨU_MẠNH_MẼ_CHO_USER' bằng một mật khẩu thực sự mạnh!
-- Nếu người dùng đã tồn tại, lệnh này sẽ báo lỗi. Bạn có thể kiểm tra trước nếu muốn.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'exchange_user') THEN
        CREATE USER exchange_user WITH PASSWORD '212#2sdf34@!$%#@!'; -- Thay mật khẩu mạnh vào đây
        RAISE NOTICE 'Người dùng exchange_user đã được tạo.';
    ELSE
        RAISE NOTICE 'Người dùng exchange_user đã tồn tại, bỏ qua việc tạo mới.';
    END IF;
END
$$;

-- 2. Cấp quyền kết nối (CONNECT) vào cơ sở dữ liệu 'ea' cho 'exchange_user'
-- Nếu không có quyền này, user sẽ không thể kết nối vào database.
GRANT CONNECT ON DATABASE ea TO exchange_user;

-- 3. Cấp quyền sử dụng (USAGE) và tạo đối tượng (CREATE) trên schema 'public' trong database 'ea'
-- Hầu hết các đối tượng sẽ nằm trong schema 'public' theo mặc định.
-- Lệnh này cần được chạy KHI ĐÃ KẾT NỐI VÀO DATABASE 'ea'.
-- Nếu bạn chạy script này từ một kết nối khác, bạn cần kết nối vào 'ea' trước các lệnh GRANT trên schema.
-- Tuy nhiên, các lệnh GRANT dưới đây sẽ hoạt động đúng nếu user chạy script có quyền trên 'ea'.
GRANT USAGE, CREATE ON SCHEMA public TO exchange_user;

-- 4. Cấp tất cả các quyền trên TẤT CẢ CÁC BẢNG HIỆN TẠI trong schema 'public'
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO exchange_user;

-- 5. Cấp tất cả các quyền trên TẤT CẢ CÁC SEQUENCE HIỆN TẠI trong schema 'public'
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO exchange_user;

-- 6. Cấp tất cả các quyền (EXECUTE) trên TẤT CẢ CÁC FUNCTION HIỆN TẠI trong schema 'public'
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO exchange_user;

-- 7. Thiết lập quyền mặc định cho các ĐỐI TƯỢNG SẼ ĐƯỢC TẠO TRONG TƯƠNG LAI trong schema 'public'
-- Điều này đảm bảo 'exchange_user' sẽ có quyền trên các bảng, sequence, function mới được tạo
-- bởi BẤT KỲ USER NÀO (khi lệnh này được chạy bởi superuser).
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO exchange_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO exchange_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON FUNCTIONS TO exchange_user;

-- Kết thúc transaction
COMMIT;


-- LƯU Ý QUAN TRỌNG:
-- 1. "Đầy đủ các permission" ở đây được hiểu là quyền đầy đủ trên schema 'public' của database 'ea'.
--    Nếu bạn có các schema khác trong 'ea' mà 'exchange_user' cần truy cập,
--    bạn cần lặp lại các lệnh GRANT từ bước 3 đến 7 cho các schema đó.
--    Ví dụ, cho schema 'myschema':
--    GRANT USAGE, CREATE ON SCHEMA myschema TO exchange_user;
--    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA myschema TO exchange_user;
--    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA myschema TO exchange_user;
--    GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA myschema TO exchange_user;
--    ALTER DEFAULT PRIVILEGES IN SCHEMA myschema GRANT ALL PRIVILEGES ON TABLES TO exchange_user;
--    ALTER DEFAULT PRIVILEGES IN SCHEMA myschema GRANT ALL PRIVILEGES ON SEQUENCES TO exchange_user;
--    ALTER DEFAULT PRIVILEGES IN SCHEMA myschema GRANT ALL PRIVILEGES ON FUNCTIONS TO exchange_user;
--
-- 2. Nếu "đầy đủ các permission" có nghĩa là 'exchange_user' nên là chủ sở hữu (owner) của database 'ea',
--    bạn có thể chạy lệnh sau (thay vì các quyền chi tiết ở trên, hoặc bổ sung).
--    Việc này cho quyền kiểm soát cao nhất đối với database, bao gồm cả việc xóa database.
--    CÂN NHẮC KỸ lưỡng trước khi thực hiện:
--    -- ALTER DATABASE ea OWNER TO exchange_user;
--    -- RAISE NOTICE 'Đã thay đổi chủ sở hữu của database ea thành exchange_user.';
--
-- 3. Luôn sử dụng mật khẩu mạnh cho người dùng cơ sở dữ liệu.