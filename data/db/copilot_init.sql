-- =============================================================
-- Enterprise Operations Copilot 数据库初始化
-- 对应 docs/04-数据库设计.md
-- 执行: mysql -u root -p < data/init.sql
-- =============================================================

CREATE DATABASE IF NOT EXISTS copilot
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE copilot;

-- ---------- 1. users 客户表 ----------
CREATE TABLE IF NOT EXISTS users (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(50)  NOT NULL,
  vip_level     TINYINT      NOT NULL DEFAULT 0 COMMENT '0普通 1银 2金 3钻石',
  score         INT          NOT NULL DEFAULT 0,
  city          VARCHAR(50)  NOT NULL,
  phone         VARCHAR(20)  DEFAULT NULL,
  register_time DATETIME     NOT NULL,
  KEY idx_city (city),
  KEY idx_vip  (vip_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------- 2. orders 订单表 ----------
CREATE TABLE IF NOT EXISTS orders (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  order_no      VARCHAR(32)  NOT NULL,
  user_id       BIGINT UNSIGNED NOT NULL,
  price         DECIMAL(10,2)   NOT NULL,
  status        VARCHAR(20)     NOT NULL COMMENT 'pending_payment/paid/shipped/completed/refunded/closed',
  city          VARCHAR(50)     NOT NULL,
  create_time   DATETIME        NOT NULL,
  paid_time     DATETIME        DEFAULT NULL,
  ship_time     DATETIME        DEFAULT NULL,
  complete_time DATETIME        DEFAULT NULL,
  UNIQUE KEY uk_order_no (order_no),
  KEY idx_user   (user_id),
  KEY idx_status (status),
  KEY idx_city   (city),
  KEY idx_ctime  (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------- 3. refunds 退款单表 ----------
CREATE TABLE IF NOT EXISTS refunds (
  id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  order_no    VARCHAR(32)    NOT NULL,
  user_id     BIGINT UNSIGNED NOT NULL,
  reason      VARCHAR(50)    NOT NULL COMMENT 'quality/logistics_slow/no_longer_want/wrong_item/price_change/other',
  amount      DECIMAL(10,2)  NOT NULL,
  status      VARCHAR(20)    NOT NULL DEFAULT 'applying' COMMENT 'applying/approved/rejected/refunded',
  create_time DATETIME       NOT NULL,
  finish_time DATETIME       DEFAULT NULL,
  KEY idx_order  (order_no),
  KEY idx_reason (reason),
  KEY idx_user   (user_id),
  KEY idx_ctime  (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------- 4. 物流轨迹表（第一项目订单/物流查询复用，docs/04 §物流） ----------
CREATE TABLE IF NOT EXISTS tracking (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  order_no VARCHAR(64) NOT NULL,
  carrier VARCHAR(32) NOT NULL,
  tracking_number VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL,        -- shipped=运输中 / delivered=已签收
  events_json TEXT NOT NULL,          -- JSON [{ts, desc}, ...]
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_tracking_no (tracking_number),
  KEY idx_tracking_order (order_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------- 5. SQL Agent 只读账号 ----------
-- '%' 覆盖 docker 网络内 api 容器连接（源 IP 非 localhost）
CREATE USER IF NOT EXISTS 'agent_ro'@'localhost' IDENTIFIED BY 'AgentReadOnly2026';
CREATE USER IF NOT EXISTS 'agent_ro'@'127.0.0.1' IDENTIFIED BY 'AgentReadOnly2026';
CREATE USER IF NOT EXISTS 'agent_ro'@'%' IDENTIFIED BY 'AgentReadOnly2026';
GRANT SELECT ON copilot.* TO 'agent_ro'@'localhost';
GRANT SELECT ON copilot.* TO 'agent_ro'@'127.0.0.1';
GRANT SELECT ON copilot.* TO 'agent_ro'@'%';
FLUSH PRIVILEGES;

-- 初始化完成
SELECT 'init ok' AS status, DATABASE() AS db;
