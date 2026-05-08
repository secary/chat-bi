SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS chatbi_bank_external
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'demo_user'@'localhost' IDENTIFIED BY 'demo_pass';
CREATE USER IF NOT EXISTS 'demo_user'@'%' IDENTIFIED BY 'demo_pass';
ALTER USER 'demo_user'@'localhost' IDENTIFIED BY 'demo_pass';
ALTER USER 'demo_user'@'%' IDENTIFIED BY 'demo_pass';

GRANT ALL PRIVILEGES ON chatbi_bank_external.* TO 'demo_user'@'localhost';
GRANT ALL PRIVILEGES ON chatbi_bank_external.* TO 'demo_user'@'%';
FLUSH PRIVILEGES;
