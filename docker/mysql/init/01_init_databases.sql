-- ============================================================
-- MySQL 초기화 스크립트 — docker/mysql/init/01_init_databases.sql
-- docker-compose mysql 컨테이너 최초 시작 시 자동 실행
-- ============================================================

-- 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS order_db      CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS account_db    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS settlement_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- exchange 사용자에게 모든 DB 권한 부여
GRANT ALL PRIVILEGES ON order_db.*      TO 'exchange'@'%';
GRANT ALL PRIVILEGES ON account_db.*    TO 'exchange'@'%';
GRANT ALL PRIVILEGES ON settlement_db.* TO 'exchange'@'%';

FLUSH PRIVILEGES;
