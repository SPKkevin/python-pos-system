/*-- 1) 建立 POS 專用帳號（如果不存在才建立）
--    目的：讓你的程式用 pos_user 連線，不用 root*/
CREATE USER IF NOT EXISTS 'pos_user'@'localhost'
IDENTIFIED BY 'pos1234';

/*-- 2) 修改 orders 表：加入狀態 + 付款相關欄位
--    目的：讓訂單可以分 OPEN/PAID，並保存付款資訊
--    注意：這段會改表結構，只要執行一次就好*/
ALTER TABLE orders
ADD COLUMN status VARCHAR(16) DEFAULT 'OPEN',
ADD COLUMN payment_method VARCHAR(16),
ADD COLUMN paid_amount INT,
ADD COLUMN change_amount INT,
ADD COLUMN paid_at DATETIME;

/*-- 3) 授權：讓 pos_user 可以對 menu 這個資料庫做 CRUD*/
--    SELECT, INSERT, UPDATE, DELETE
GRANT SELECT, INSERT, UPDATE, DELETE
ON menu.*
TO 'pos_user'@'localhost';


/*-- 4) 刷新權限（讓剛剛 GRANT 立即生效）*/
FLUSH PRIVILEGES;

/*-- 5) 檢查 orders 表結構（確認欄位有加進去）*/
DESCRIBE orders;

/*-- 6) 測試查詢：查看最近 5 筆訂單
--    目的：確認 orders 表有資料、排序正常*/
SELECT * FROM orders ORDER BY id DESC LIMIT 5;

/*-- 7) 測試查詢：查看最近 20 筆訂單明細
--    目的：確認 order_items 有資料、可用於右側明細顯示*/
SELECT * FROM order_items ORDER BY id DESC LIMIT 20;

/*-- 8) 切換資料庫到 menu（後續查詢都在 menu 內）
--    注意：習慣上這句通常放在最前面*/
USE menu;

/*建立菜單表*/
CREATE TABLE IF NOT EXISTS menu_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  category VARCHAR(50) NOT NULL,
  name VARCHAR(80) NOT NULL,
  price INT NULL,
  is_market_price TINYINT(1) NOT NULL DEFAULT 0,
  active TINYINT(1) NOT NULL DEFAULT 1
);

DESCRIBE menu_items;

/*清空列表*/
TRUNCATE TABLE menu_items;
/*搜尋菜單id*/
SELECT id, name FROM menu_items;
/*搜尋整個菜單*/
SELECT * FROM menu_items;

				/*
				ALTER TABLE menu_items
				MODIFY category VARCHAR(50) NOT NULL DEFAULT '海鮮川燙類：';

				新增菜單的內容
				INSERT INTO menu_items (name, price)
				VALUES
				("清蒸龍膽石斑",800),("清蒸鱈魚",700),("清蒸石斑",NULL),("清蒸鮮魚",400),("清蒸鱸魚肉片",300),("川燙大蝦",550),("川燙中卷",400),("川燙鮮蚵",350),("川燙白蝦",300),("川燙虱目魚皮",200);

				更新菜名的狀態(是否為時價)
				UPDATE menu_items
				SET is_market_price = 1
				WHERE id = 5;
				*/

SET SQL_SAFE_UPDATES = 0;

UPDATE menu_items
SET category_sort =
  CASE category
    WHEN '火鍋類' THEN 1
    WHEN '湯鍋類' THEN 2
    WHEN '湯鍋配菜類' THEN 3
    WHEN '麵飯類' THEN 4
    WHEN '熱炒類' THEN 5
    WHEN '熱炒類2' THEN 6
    WHEN '海鮮川燙類' THEN 7
    ELSE 99
  END
WHERE id > 0;

UPDATE menu_items
SET category = '熱炒類'
WHERE category = '快炒類';

UPDATE menu_items
SET category = '熱炒類'
WHERE id = 60;

use menu;
SELECT * FROM orders;
DESCRIBE orders;


