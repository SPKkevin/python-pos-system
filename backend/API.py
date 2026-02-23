from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
from datetime import datetime
from typing import List
#cd C:\Users\a1137\OneDrive\桌面\示範程式\測試 uvicorn API:app --reload

app = FastAPI()

DB_SETTING = {
    "host": "localhost",
    "port": 3306,
    "user": "pos_user",
    "password": "pos1234",
    "database": "menu",
}
# ---------- 需求資料格式（前端送進來的 JSON） ----------
class OrderItemIn(BaseModel):
    name: str
    price: int
    qty: int

# ---------- 新增：加單（新增明細 + 更新 total） ----------
class AddItemsIn(BaseModel):
    items: List[OrderItemIn]

class OrderCreateIn(BaseModel):
    items: List[OrderItemIn]

class PayIn(BaseModel):
    payment_method: str  # "CASH" 或 "CARD"

# ---------- 基本：健康檢查 ----------
@app.get("/health", tags=["系統"], summary="健康檢查")
def health():
    return {"ok": True}

# ---------- 基本：最近訂單 ----------
@app.get("/orders/recent", tags=["訂單"], summary="最近訂單")
def recent_orders(limit: int = 10):
    conn = mysql.connector.connect(**DB_SETTING)
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, status, total, COALESCE(payment_method,'') AS payment_method, created_at
            FROM orders
            ORDER BY id DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()
    finally:
        conn.close()

# ---------- 新增：建立訂單 ----------
@app.post("/orders", tags=["Orders"], summary="建立訂單")
def create_order(body: OrderCreateIn):

    # 1) 基本驗證
    if not body.items:
        raise HTTPException(status_code=400, detail="items 不可為空")

    for it in body.items:
        if not it.name.strip():
            raise HTTPException(status_code=400, detail="name 不可為空字串")
        if it.price < 0:
            raise HTTPException(status_code=400, detail="price 不可小於 0")
        if it.qty <= 0:
            raise HTTPException(status_code=400, detail="qty 必須大於 0")

    total = sum(int(it.price) * int(it.qty) for it in body.items)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = mysql.connector.connect(**DB_SETTING)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 2) 建立 orders 主檔（狀態固定 OPEN）
        cur.execute(
            "INSERT INTO orders (created_at, total, status) VALUES (%s, %s, 'OPEN')",
            (created_at, int(total))
        )
        order_id = cur.lastrowid

        # 3) 建立 order_items 明細
        cur.executemany(
            "INSERT INTO order_items (order_id, name, price, qty) VALUES (%s, %s, %s, %s)",
            [(order_id, it.name, int(it.price), int(it.qty)) for it in body.items]
        )

        conn.commit()
        return {"order_id": order_id, "total": total, "status": "OPEN"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"建立訂單失敗：{e}")

    finally:
        conn.close()

@app.get("/orders/{order_id}", tags=["Orders"], summary="查詢訂單")
def get_order(order_id: int):
    conn = mysql.connector.connect(**DB_SETTING)
    cur = conn.cursor(dictionary=True)
    try:
        # 1) 取主檔
        cur.execute("""
            SELECT id, status, total, COALESCE(payment_method,'') AS payment_method, created_at
            FROM orders
            WHERE id=%s
        """, (order_id,))
        order = cur.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="找不到訂單")

        # 2) 取明細（依你的表欄位：name/price/qty）
        cur.execute("""
            SELECT id, name, price, qty
            FROM order_items
            WHERE order_id=%s
            ORDER BY id
        """, (order_id,))
        items = cur.fetchall()

        return {
            "order": order,
            "items": items
        }

    finally:
        conn.close()

@app.patch("/orders/{order_id}/pay", tags=["Orders"], summary="訂單結帳")
def pay_order(order_id: int, body: PayIn):
    method = body.payment_method.strip().upper()
    if method not in ("CASH", "CARD"):
        raise HTTPException(status_code=400, detail="payment_method 只能是 CASH 或 CARD")

    conn = mysql.connector.connect(**DB_SETTING)
    conn.autocommit = False
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, status FROM orders WHERE id=%s", (order_id,))
        order = cur.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="找不到訂單")
        if order["status"] != "OPEN":
            raise HTTPException(status_code=400, detail="訂單已結帳")

        cur.execute("""
            UPDATE orders
            SET status='PAID', payment_method=%s
            WHERE id=%s AND status='OPEN'
        """, (method, order_id))

        if cur.rowcount != 1:
            raise HTTPException(status_code=409, detail="更新失敗（狀態可能已變更）")

        conn.commit()
        return {"order_id": order_id, "status": "PAID", "payment_method": method}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/orders/{order_id}/items", tags=["Orders"], summary="加單（新增品項到既有訂單）")
def add_items(order_id: int, body: AddItemsIn):
    if not body.items:
        raise HTTPException(status_code=400, detail="items 不可為空")

    for it in body.items:
        if not it.name.strip():
            raise HTTPException(status_code=400, detail="name 不可為空字串")
        if it.price < 0:
            raise HTTPException(status_code=400, detail="price 不可小於 0")
        if it.qty <= 0:
            raise HTTPException(status_code=400, detail="qty 必須大於 0")

    add_total = sum(int(it.price) * int(it.qty) for it in body.items)

    conn = mysql.connector.connect(**DB_SETTING)
    conn.autocommit = False
    cur = conn.cursor(dictionary=True)

    try:
        # 1) 確認訂單存在且為 OPEN
        cur.execute("SELECT id, status, total FROM orders WHERE id=%s", (order_id,))
        order = cur.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="找不到訂單")
        if order["status"] != "OPEN":
            raise HTTPException(status_code=400, detail="訂單已結帳，禁止加單")

        # 2) 更新主檔 total
        cur.execute(
            "UPDATE orders SET total = total + %s WHERE id=%s AND status='OPEN'",
            (int(add_total), order_id)
        )
        if cur.rowcount != 1:
            raise HTTPException(status_code=409, detail="加單失敗（狀態可能已變更）")

        # 3) 新增明細
        cur2 = conn.cursor()
        cur2.executemany(
            "INSERT INTO order_items (order_id, name, price, qty) VALUES (%s, %s, %s, %s)",
            [(order_id, it.name, int(it.price), int(it.qty)) for it in body.items]
        )

        conn.commit()

        # 回傳更新後 total（可選，但好用）
        cur.execute("SELECT total FROM orders WHERE id=%s", (order_id,))
        new_total = cur.fetchone()["total"]

        return {"order_id": order_id, "added_total": add_total, "total": new_total}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/orders/{order_id}/items/{item_id}", tags=["Orders"], summary="刪除訂單明細（同步扣總額）")
def delete_order_item(order_id: int, item_id: int):
    conn = mysql.connector.connect(**DB_SETTING)
    conn.autocommit = False
    cur = conn.cursor(dictionary=True)

    try:
        # 1) 確認訂單存在且 OPEN
        cur.execute("SELECT id, status FROM orders WHERE id=%s", (order_id,))
        order = cur.fetchone()
        if not order:
            raise HTTPException(status_code=404, detail="找不到訂單")
        if order["status"] != "OPEN":
            raise HTTPException(status_code=400, detail="訂單已結帳，禁止刪除")

        # 2) 取明細金額
        cur.execute("""
            SELECT price, qty
            FROM order_items
            WHERE id=%s AND order_id=%s
        """, (item_id, order_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="找不到該品項（可能已被刪除）")

        delta = int(row["price"]) * int(row["qty"])

        # 3) 刪除明細
        cur2 = conn.cursor()
        cur2.execute("DELETE FROM order_items WHERE id=%s AND order_id=%s", (item_id, order_id))
        if cur2.rowcount != 1:
            raise HTTPException(status_code=409, detail="刪除失敗")

        # 4) 更新主檔 total
        cur2.execute("""
            UPDATE orders
            SET total = total - %s
            WHERE id=%s AND status='OPEN'
        """, (delta, order_id))
        if cur2.rowcount != 1:
            raise HTTPException(status_code=409, detail="更新總金額失敗（狀態可能已變更）")

        conn.commit()
        return {"order_id": order_id, "item_id": item_id, "deducted": delta}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.patch("/orders/{order_id}/items/{item_id}", tags=["Orders"], summary="修改明細數量")
def update_item_qty(order_id: int, item_id: int, data: dict):
    delta = int(data.get("delta", 0))

    if delta == 0:
        raise HTTPException(status_code=400, detail="delta 不可為 0")

    conn = mysql.connector.connect(**DB_SETTING)
    conn.autocommit = False
    cur = conn.cursor(dictionary=True)

    try:
        # 確認訂單 OPEN
        cur.execute("SELECT status FROM orders WHERE id=%s", (order_id,))
        order = cur.fetchone()
        if not order or order["status"] != "OPEN":
            raise HTTPException(status_code=400, detail="訂單不可修改")

        # 取目前 qty / price
        cur.execute("""
            SELECT price, qty
            FROM order_items
            WHERE id=%s AND order_id=%s
        """, (item_id, order_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="找不到品項")

        new_qty = int(row["qty"]) + delta
        if new_qty <= 0:
            raise HTTPException(status_code=400, detail="數量不可小於等於 0")

        price = int(row["price"])
        total_delta = price * delta

        cur2 = conn.cursor()
        cur2.execute("""
            UPDATE order_items
            SET qty=%s
            WHERE id=%s AND order_id=%s
        """, (new_qty, item_id, order_id))

        cur2.execute("""
            UPDATE orders
            SET total = total + %s
            WHERE id=%s
        """, (total_delta, order_id))

        conn.commit()
        return {"new_qty": new_qty}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()