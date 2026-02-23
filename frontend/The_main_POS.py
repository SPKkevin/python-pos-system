from tkinter import messagebox
import requests
import tkinter as tk
import tkinter.font as tkFont
import mysql.connector
from datetime import datetime
class DB:
    def __init__(self , db_sitting):
        self.db_sitting = db_sitting
    #連線資料庫
    def con_to_db(self):
        conn = mysql.connector.connect(**self.db_sitting)
        conn.autocommit = False
        return conn
    
    #查詢多筆
    def select_all(self, sql, data=None, dictionary=False):
        conn = self.con_to_db()
        cur = conn.cursor(dictionary=dictionary)
        try:
            cur.execute(sql, data) if data is not None else cur.execute(sql)
            return cur.fetchall()
        finally:
            conn.close()
    
    #查詢單筆
    def select_one(self, sql, data=None, dictionary=False):
        conn =self.con_to_db()
        cur = conn.cursor(dictionary=dictionary)
        try:
            cur.execute(sql, data) if data is not None else cur.execute(sql)
            return cur.fetchone()
        finally:
            conn.close()
    
    #寫入
    def execute(self, sql, data=None, many=False):
        conn = self.con_to_db()
        cur = conn.cursor()

        try:
            if many and not data:
                raise ValueError("executemany 需要 data 為 list/tuple")
            
            if many:
                cur.executemany(sql, data)
            else:
                cur.execute(sql, data) if data is not None else cur.execute(sql)

            conn.commit()
            return cur.rowcount , cur.lastrowid

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()
    #確保全部成功才寫入
    def transaction(self, fn):
        conn = self.con_to_db()
        try:
            cur = conn.cursor()
            result = fn(cur)      # 讓外面用同一個 cursor 跑多段 SQL
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


class POS:
    #主要配置區
    def __init__(self, root):
        self.API_BASE = "http://127.0.0.1:8000"

        #主框架
        self.root = root
        self.root.title("POS 系统")
        self.custom_font = tkFont.Font(family="Helvetica", size=24)

        #資料庫設定區
        self.db_sitting = {
            "host": "localhost",
            "port": 3306,
            "user": "pos_user",
            "password": "pos1234",
            "database": "menu"
            }   
        self.db = DB(self.db_sitting)
        
        self.current_order_id = None

        #計算金額+總數
        self.cart = {}        # {"羊肉爐": {"price": 500, "qty": 2}}
        self.total_amount = 0

        #創建商品
        self.create_widgets()
        
        #顯示框設定
        self.cart_listbox = tk.Listbox(self.root, width=30, font=self.custom_font)
        self.cart_listbox.grid(row=3, column=0, columnspan=2, rowspan=20, padx=10, pady=5)

        #訂單顯示介面
        # ====== 右側：最近訂單 / 訂單明細 ======
        tk.Label(self.root, text="最近訂單").grid(row=0, column=9, padx=10, pady=5, sticky="w")
                                                                        #[exportselection=False]有多選的功能
        self.orders_listbox = tk.Listbox(self.root, width=32, height=10 ,exportselection=False)
        self.orders_listbox.grid(row=1, column=9, rowspan=6, padx=10, pady=5, sticky="n")

        tk.Label(self.root, text="訂單明細").grid(row=7, column=9, padx=10, pady=5, sticky="w")
                                                                                #[exportselection=False]有多選的功能
        self.order_detail_listbox = tk.Listbox(self.root, width=32, height=12 , exportselection=False)
        self.order_detail_listbox.grid(row=8, column=9, rowspan=10, padx=10, pady=5, sticky="n")

        
        # 點選訂單 → 顯示明細
        self.orders_listbox.bind("<<ListboxSelect>>", self.on_select_order)

        #統計總金額
        self.total_var = tk.StringVar(value="總計：0")
        #總金額顯示位置
        tk.Label(self.root,textvariable=self.total_var,font=("Arial", 20)).grid(row=17, column=0, columnspan=2, sticky="w", padx=10, pady=5)
        self.bind_keys()
        self.order_ids = []  # 對應 orders_listbox 每一行的 order_id
        self.refresh_order_list()

        #事件觸發按鈕
        tk.Button(self.root, text="+1", width=6, command=self.inc_qty).grid(row=22, column=0, pady=5)
        tk.Button(self.root, text="-1", width=6, command=self.dec_qty).grid(row=22, column=1, pady=5)
        tk.Button(self.root, text="刪除", width=10, command=self.remove_item).grid(row=22, column=2, pady=5)
        tk.Button(self.root, text="提交", width=10,height=1 , command=self.submit_order).grid(row=23, column=0, columnspan=2, pady=20)
        

        self.pay_bill = tk.Button(self.root, text="結帳", width=12, command=self.open_checkout_window)
        self.pay_bill.grid(row=23, column=3, pady=20)

        self.chang_delete_button = tk.Button(self.root, text="變更/刪除", width=10, command=self.edit_delete_item)
        self.chang_delete_button.grid(row=19, column=9, padx=10, pady=5, sticky="w")
        self.order_mode = tk.Button(self.root, text="開單模式", width=6, command=self.set_order_mode)
        self.order_mode.grid(row=21, column=0, pady=5)
        self.add_mode = tk.Button(self.root, text="加單模式", width=6, command=self.set_add_mode)
        self.add_mode.grid(row=21, column=1, pady=5)
        self.mode = "ORDER"   # "ORDER"=點單模式, "ADD"=加單模式
        self.apply_mode_ui()  # 初始化狀態

    #時價判定
    def add_to_cart(self, product):

        #防改動判定
        if not self.ensure_order_open():
            return

        name, price = product

        #判定是否為時價 price 不是數字 => 視為時價，跳出輸入介面
        if not isinstance(price, (int, float)):
            self.open_price_input(name)
            return
        
        # 正常商品直接加入
        self.add_item(name,price)
    
    #加入至顯示框
    def add_item(self, name, price):
        key = name

        # 累加資料
        if key in self.cart:
            self.cart[key]["qty"] += 1
        else:
            self.cart[key] = {"name": name, "price": price, "qty": 1}

        # 重算總金額
        self.total_amount += price

        # 更新畫面
        self.refresh_cart()
    
    #時價的區分方法
    def add_market_price_item(self, name, price):
        key = f"{name}@{price}"  # ← 關鍵：每次都不同

        self.cart[key] = {
            "name": name,
            "price": price,
            "qty": 1
        }

        self.total_amount += price
        self.refresh_cart()

    #快捷鍵設定
    def bind_keys(self):
        self.root.bind("<Return>", self.on_enter)          # Enter
        self.root.bind("<Escape>", self.on_escape)         # Esc
        self.root.bind("<BackSpace>", self.on_delete)      # Backspace
        self.root.bind("<Delete>", self.on_delete)         # Delete
        self.root.bind("<plus>", self.on_plus)             # +
        self.root.bind("<minus>", self.on_minus)           # -
    #鍵盤按鍵控制
    def on_enter(self, event=None): #空格
        self.clear_the_listbox()
    def on_escape(self, event=None):#esc
        self.clear_the_listbox()
    def on_delete(self, event=None):#delete
        self.remove_item()
    def on_plus(self, event=None):  #+號
        self.inc_qty()
    def on_minus(self, event=None): #-號
        self.dec_qty()

    #排列菜單的區域
    def create_widgets(self):

        rows = self.db.select_all("""
            SELECT category, name, price, is_market_price , category_sort
            FROM menu_items
            WHERE active = 1
            ORDER BY category_sort, id
        """)

        # 分類整理
        categories = {}
        for category, name, price, is_market_price , category_sort in rows:
            if category not in categories:
                categories[category] = []
            if is_market_price:
                categories[category].append((name, "時價"))
            else:
                categories[category].append((name, price))

        # 依分類產生按鈕
        start_col = 2
        for i, (dish_name, products) in enumerate(categories.items()):
            col = start_col + i
            tk.Label(self.root, text=f"{dish_name} :", font=("Arial", 12)).grid(row=0, column=col, padx=10, pady=10)

            for j, product in enumerate(products):
                tk.Button(self.root , text=product[0] , width=10 ,height=1,font=("Arial", 12) , command=lambda p=product: self.add_to_cart(p)
                ).grid(row=j+1, column=col, padx=10, pady=5)
    
    #結帳處理
    def checkout_selected_order(self, payment_method="CASH", paid_amount=None):
        full_order = self.get_selected_order()
        if full_order == None:
            return

        if full_order["status"] != "OPEN":
            messagebox.showinfo("提示", "此訂單已結帳")
            return

        order_id = full_order["id"]
        total = int(full_order["total"])

        # 付款驗證（留在前端）
        if payment_method == "CASH":
            if paid_amount is None:
                messagebox.showinfo("提示", "現金結帳需要實收金額")
                return
            paid_amount = int(paid_amount)
            if paid_amount < total:
                messagebox.showinfo("提示", "實收金額不足")
                return
            change_amount = paid_amount - total
        else:  # CARD
            paid_amount = total
            change_amount = 0

        try:
            resp = requests.patch(
                f"{self.API_BASE}/orders/{order_id}/pay",
                json={"payment_method": payment_method}
            )

            if resp.status_code == 404:
                messagebox.showerror("錯誤", "找不到訂單")
                return

            if resp.status_code != 200:
                messagebox.showerror("錯誤", f"API 結帳失敗：{resp.text}")
                return

            messagebox.showinfo("完成", f"結帳完成：單號 {order_id}，找零 {change_amount}")
            self.orders_listbox.selection_clear(0, tk.END)

            self.refresh_order_list()
            self.show_order_detail(order_id)
            self.set_order_mode()

        except Exception as e:
            messagebox.showerror("錯誤", f"結帳失敗：{e}")
    #交易控制介面
    def open_checkout_window(self):
        full_order = self.get_selected_order()
        if full_order is None:
            return

        if full_order["status"] != "OPEN":
            messagebox.showinfo("提示", "此訂單已結帳")
            return

        order_id = full_order["id"]
        total = int(full_order["total"])

        win = tk.Toplevel(self.root)
        win.title("結帳")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text=f"訂單 #{order_id}").grid(row=0, column=0, columnspan=2, pady=10)
        tk.Label(win, text=f"應收金額：{total}").grid(row=1, column=0, columnspan=2)

        tk.Label(win, text="付款方式").grid(row=2, column=0, pady=5)

        payment_var = tk.StringVar(value="CASH")

        tk.Radiobutton(win, text="現金", variable=payment_var, value="CASH").grid(row=2, column=1)
        tk.Radiobutton(win, text="信用卡", variable=payment_var, value="CARD").grid(row=3, column=1)

        tk.Label(win, text="實收金額").grid(row=4, column=0)
        entry = tk.Entry(win)
        entry.grid(row=4, column=1)

        def confirm():
            method = payment_var.get()

            if method == "CASH":
                try:
                    paid = int(entry.get())
                except ValueError:
                    messagebox.showinfo("提示", "請輸入數字")
                    return
            else:
                paid = total

            win.destroy()
            self.checkout_selected_order(method, paid)

        tk.Button(win, text="確認", command=confirm).grid(row=5, column=0, pady=10)
        tk.Button(win, text="取消", command=win.destroy).grid(row=5, column=1)

    #清空輸入框
    def clear_the_listbox(self):
        if not self.ensure_order_open():
            return

        if not self.cart:
            return

        if not messagebox.askyesno("確認", "確定要清空購物車？"):
            return

        self.cart.clear()
        self.total_amount = 0
        self.refresh_cart()

    #訂單結帳防呆更改
    def ensure_order_open(self):
        """回傳 True 表示目前允許操作購物車；False 表示應禁止"""
        if self.current_order_id is None:
            # 尚未提交成訂單：允許操作（建立新單）
            return True

        try:
            row = self.db.select_one(
                "SELECT status FROM orders WHERE id=%s",
                  (self.current_order_id,)
            )

            if not row:
                # 找不到訂單：保守起見禁止
                messagebox.showerror("錯誤", "找不到目前訂單，已禁止操作")
                return False

            status = row[0]
            if status != "OPEN":
                messagebox.showinfo("提示", f"此訂單狀態為 {status}，已鎖單，禁止修改")
                return False

            return True

        except Exception as e:
            messagebox.showerror("錯誤", f"檢查訂單狀態失敗：{e}")
            return False

    #重製購物車
    def refresh_cart(self):
        self.cart_listbox.delete(0, tk.END)
        self.line_keys = []  # 每一行對應 self.cart 的 key

        for key, info in self.cart.items():
            self.cart_listbox.insert(
                tk.END,
                f"{info['name']:<8} {info['price']:>4} x{info['qty']}"
            )
            self.line_keys.append(key)

        self.total_var.set(f"總計：{self.total_amount}")
    
    #更新明細
    def refresh_order_list(self, limit=10):
        try:
            resp = requests.get(
                f"{self.API_BASE}/orders/recent",
                params={"limit": limit}
            )

            if resp.status_code != 200:
                messagebox.showerror("錯誤", f"API 錯誤：{resp.text}")
                return

            rows = resp.json()

            self.orders_listbox.delete(0, tk.END)
            self.order_ids = []

            for row in rows:
                oid = row["id"]
                status = row["status"]
                total = row["total"]
                pm = row.get("payment_method", "") or "-"

                self.orders_listbox.insert(
                    tk.END,
                    f"#{oid} | {status:<4} | ${total:<5} | {pm}"
                )
                self.order_ids.append(oid)

        except Exception as e:
            messagebox.showerror("錯誤", f"刷新訂單失敗：{e}")
    
    #刪除的控制
    def remove_item(self):
        #防改動判定
        if not self.ensure_order_open():
            return

        key = self.get_selected_name()

        if not key:
            return

        price = self.cart[key]["price"]
        qty = self.cart[key]["qty"]

        self.total_amount -= price * qty
        del self.cart[key]
        self.refresh_cart()
    
# 顯示訂單明細（改成打 API）
    def show_order_detail(self, order_id):
        try:
            resp = requests.get(f"{self.API_BASE}/orders/{order_id}")

            if resp.status_code == 404:
                messagebox.showinfo("提示", "找不到訂單")
                return

            if resp.status_code != 200:
                messagebox.showerror("錯誤", f"API 錯誤：{resp.text}")
                return

            data = resp.json()
            items = data.get("items", [])

            self.detail_item_ids = []
            self.order_detail_listbox.delete(0, tk.END)
            self.order_detail_listbox.insert(tk.END, f"訂單 #{order_id}")
            self.order_detail_listbox.insert(tk.END, "----------------------")

            if not items:
                self.order_detail_listbox.insert(tk.END, "（此訂單沒有明細）")
                return

            for it in items:
                item_id = it["id"]
                name = it["name"]
                price = it["price"]
                qty = it["qty"]

                self.order_detail_listbox.insert(tk.END, f"{name}  {price} x{qty}")
                self.detail_item_ids.append(item_id)

        except Exception as e:
            messagebox.showerror("錯誤", f"讀取明細失敗：{e}")
    #同步顯示的功能
    def on_select_order(self, event=None):
        sel = self.orders_listbox.curselection()
        if not sel:
            return

        idx = sel[0]
        if idx < 0 or idx >= len(self.order_ids):
            return

        order_id = self.order_ids[idx]

        # 只在 ADD 模式才改 current_order_id
        if self.mode == "ADD":
            self.current_order_id = order_id

        self.show_order_detail(order_id)

    #變更\刪除控制
    def edit_delete_item(self):
        full_order = self.ensure_selected_open_order()
        if full_order is None:
            return

        order_id = full_order["id"]

        item_id = self.get_selected_detail_item_id()
        if item_id is None:
            return

        if not messagebox.askyesno("確認", "確定要刪除此品項？"):
            return

        try:
            resp = requests.delete(f"{self.API_BASE}/orders/{order_id}/items/{item_id}")

            if resp.status_code == 404:
                messagebox.showerror("錯誤", "找不到訂單或品項")
                return

            if resp.status_code != 200:
                messagebox.showerror("錯誤", f"API 刪除失敗：{resp.text}")
                return

            # 刷新右側
            self.refresh_order_list()
            self.show_order_detail(order_id)

        except Exception as e:
            messagebox.showerror("錯誤", f"刪除失敗：{e}")

    #開單/加單的判定口
    def submit_order(self):
        if self.mode == "ORDER":
            self.submit_new_order()
        else:  # ADD
            self.submit_add_order()

    # 開單（改成打 API）
    def submit_new_order(self):

        if not self.cart:
            messagebox.showinfo("提示", "購物車是空的")
            return

        if not messagebox.askyesno("確認", "確定要提交這張單？"):
            return

        # 組成 API 需要的 JSON 格式
        items = [
            {
                "name": it["name"],
                "price": int(it["price"]),
                "qty": int(it["qty"])
            }
            for it in self.cart.values()
        ]

        try:
            resp = requests.post(
                f"{self.API_BASE}/orders",
                json={"items": items}
            )

            if resp.status_code != 200:
                messagebox.showerror("錯誤", f"API 錯誤：{resp.text}")
                return

            data = resp.json()
            order_id = data["order_id"]

            # 刷新右側訂單列表
            self.refresh_order_list()
            self.current_order_id = order_id

        except Exception as e:
            messagebox.showerror("錯誤", f"提交失敗：{e}")
            return

        # 成功才清空
        self.cart.clear()
        self.total_amount = 0
        self.refresh_cart()
        messagebox.showinfo("完成", f"已提交，單號：{order_id}")

    #加單的程式碼
    def submit_add_order(self):
        if not self.cart:
            messagebox.showinfo("提示", "購物車是空的")
            return

        if self.current_order_id is None:
            messagebox.showinfo("提示", "沒有選定要加單的訂單")
            return

        if not messagebox.askyesno("確認", f"確定要加到訂單 #{self.current_order_id}？"):
            return

        order_id = self.current_order_id

        items = [
            {"name": it["name"], "price": int(it["price"]), "qty": int(it["qty"])}
            for it in self.cart.values()
        ]

        try:
            resp = requests.post(
                f"{self.API_BASE}/orders/{order_id}/items",
                json={"items": items}
            )

            if resp.status_code == 404:
                messagebox.showerror("錯誤", "找不到訂單")
                return

            if resp.status_code != 200:
                messagebox.showerror("錯誤", f"API 加單失敗：{resp.text}")
                return

        except Exception as e:
            messagebox.showerror("錯誤", f"加單失敗：{e}")
            return

        self.cart.clear()
        self.total_amount = 0
        self.refresh_cart()
        self.refresh_order_list()
        self.show_order_detail(order_id)
        messagebox.showinfo("完成", f"已加單到 #{order_id}")
   
   #判斷是否選中單子
    def get_selected_order(self):
        sel = self.orders_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "請先選擇一筆訂單")
            return None

        idx = sel[0]
        if idx < 0 or idx >= len(self.order_ids):
            return None

        order_id = self.order_ids[idx]

        try:
            resp = requests.get(f"{self.API_BASE}/orders/{order_id}")

            if resp.status_code == 404:
                messagebox.showerror("錯誤", "找不到訂單")
                return None

            if resp.status_code != 200:
                messagebox.showerror("錯誤", f"API 錯誤：{resp.text}")
                return None

            data = resp.json()
            return data["order"]   # 只回傳主檔

        except Exception as e:
            messagebox.showerror("錯誤", f"讀取訂單失敗：{e}")
            return None

    #取得項目的具體數量
    def get_selected_name(self):
        sel = self.cart_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "請先選擇一個品項")
            return None

        idx = sel[0]
        if idx < 0 or idx >= len(self.line_keys):
            return None

        return self.line_keys[idx]
    
    #加號的控制
    def inc_qty(self):
        if self.mode =="ORDER":
            key = self.get_selected_name()

            if not key:
                return
            price = self.cart[key]["price"]
            self.cart[key]["qty"] += 1
            self.total_amount += price
            self.refresh_cart()

        if self.mode == "ADD":

            item_id = self.get_selected_detail_item_id()
            if item_id is None:
                return

        if self.mode == "ADD":

            item_id = self.get_selected_detail_item_id()
            if item_id is None:
                return

            try:
                resp = requests.patch(
                    f"{self.API_BASE}/orders/{self.current_order_id}/items/{item_id}",
                    json={"delta": 1}
                )

                if resp.status_code != 200:
                    messagebox.showerror("錯誤", resp.text)
                    return

                self.refresh_order_list()
                self.show_order_detail(self.current_order_id)

            except Exception as e:
                messagebox.showerror("錯誤", str(e))

            self.refresh_order_list()
            self.show_order_detail(self.current_order_id)

            
    def dec_qty(self):
        if self.mode =="ORDER":
            key = self.get_selected_name()

            if not key:
                return
            price = self.cart[key]["price"]
            self.cart[key]["qty"] -= 1
            self.total_amount -= price
            self.refresh_cart()

        if self.mode == "ADD":

            item_id = self.get_selected_detail_item_id()
            if item_id is None:
                return

            try:
                resp = requests.patch(
                    f"{self.API_BASE}/orders/{self.current_order_id}/items/{item_id}",
                    json={"delta": -1}
                )

                if resp.status_code != 200:
                    messagebox.showerror("錯誤", resp.text)
                    return

                self.refresh_order_list()
                self.show_order_detail(self.current_order_id)

            except Exception as e:
                messagebox.showerror("錯誤", str(e))

            self.refresh_order_list()
            self.show_order_detail(self.current_order_id)


    #時價設定介面
    def open_price_input(self, name):
        win = tk.Toplevel(self.root)
        win.title("輸入時價")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text=f"{name}（時價）").grid(row=0, column=0, columnspan=2, pady=10)
        tk.Label(win, text="金額").grid(row=1, column=0, padx=10)
        entry = tk.Entry(win, width=15)
        entry.grid(row=1, column=1, padx=10)
        entry.focus_set()

        def confirm():
            try:
                price = int(entry.get())
            except ValueError:
                messagebox.showinfo("提示", "請輸入數字")
                return

            self.add_market_price_item(name, price)
            win.destroy()

        tk.Button(win, text="確認", width=8, command=confirm).grid(row=2, column=0, pady=10)
        tk.Button(win, text="取消", width=8, command=win.destroy).grid(row=2, column=1, pady=10)

        win.bind("<Return>", lambda e: confirm())
        win.bind("<Escape>", lambda e: win.destroy())

    #加單控制
    def set_add_mode(self):
        full_order = self.get_selected_order()
        if full_order is None:
            return
        if full_order["status"] != "OPEN":
            messagebox.showinfo("提示", "此訂單已結帳")
            return

        self.current_order_id = full_order["id"]
        self.mode = "ADD"
        self.apply_mode_ui()

    #開單控制
    def set_order_mode(self):
        self.current_order_id = None 
        self.orders_listbox.selection_clear(0, tk.END)
        self.mode = "ORDER"
        self.apply_mode_ui()
   
    #開單/加單互斥控制
    def apply_mode_ui(self):
        if self.mode == "ORDER":
            self.chang_delete_button.config(state=("disabled"))
            self.order_mode.config(state="disabled")
            self.add_mode.config(state="normal")
            self.pay_bill.config(state="normal")
            
            

        else:  # "ADD"
            self.chang_delete_button.config(state=("normal"))
            self.order_mode.config(state="normal")
            self.add_mode.config(state="disabled")
            self.pay_bill.config(state="disabled")

    def ensure_selected_open_order(self):
        if self.current_order_id is None:
            messagebox.showinfo("提示", "請先在右上最近訂單選一張單")
            return None

        full_order = self.get_selected_order()
        if full_order is None:
            return None

        if full_order["status"] != "OPEN":
            messagebox.showinfo("提示", "此訂單已結帳，禁止操作")
            return None

        return full_order
    def get_selected_detail_item_id(self):
        # 必須先有選訂單
        if self.current_order_id is None:
            messagebox.showinfo("提示", "請先選擇訂單")
            return None

        sel = self.order_detail_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "請在右側明細選一個品項")
            return None

        line = sel[0]
        if line < 2:
            messagebox.showinfo("提示", "請選擇品項行")
            return None

        idx = line - 2
        if not hasattr(self, "detail_item_ids") or idx < 0 or idx >= len(self.detail_item_ids):
            messagebox.showerror("錯誤", "明細索引錯誤")
            return None

        return self.detail_item_ids[idx]


if __name__ == "__main__":
    root = tk.Tk()
    app = POS(root)
    #設定視窗位置
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - w) // 2
    y = (screen_h - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    #啟動按鍵
    root.focus_force()
    root.after(100, lambda: root.focus_force())

    #啟動程式
    root.mainloop()
    
