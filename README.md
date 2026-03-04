# 餐飲 POS 訂單管理系統

使用 Python FastAPI + MySQL + Vue 3 建立的 POS 系統，
模擬餐廳點餐到結帳的完整流程。

## 使用技術

Python · FastAPI · RESTful API · MySQL · Transaction · Vue 3 · TypeScript

## 系統架構

Frontend (Vue) → FastAPI Backend → MySQL Database

## How to Run

1. 安裝後端套件

pip install fastapi uvicorn mysql-connector-python pydantic

2. 建立資料庫

匯入
database/SQL_file.sql

3. 啟動後端

uvicorn backend.API:app --reload

4. 啟動前端

cd frontend  
npm install  
npm run dev

## API Endpoints

GET /health  
POST /orders  
GET /orders/{id}  
PATCH /orders/{id}/pay

