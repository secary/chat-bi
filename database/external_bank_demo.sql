SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS chatbi_bank_external
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

GRANT ALL PRIVILEGES ON chatbi_bank_external.* TO 'demo_user'@'%';

SOURCE data/external_bank_business.sql;
SOURCE data/external_bank_semantic.sql;
