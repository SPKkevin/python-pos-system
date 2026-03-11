CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME,
    total INT,
    status VARCHAR(20),
    payment_method VARCHAR(20),
    paid_amount INT,
    change_amount INT,
    paid_at DATETIME
);

CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT,
    name VARCHAR(100),
    price INT,
    qty INT
);