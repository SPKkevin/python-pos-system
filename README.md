# Restaurant POS System
A desktop-based restaurant POS system built with Python.

# How to Run
```
pip install -r requirements.txt
uvicorn backend.api:app --reload
```

#API Endpoints
```
GET /health
POST /orders
GET /orders/{id}
PATCH /orders/{id}/pay
```

#Tech Stack
```
Python
FastAPI
MySQL
Tkinter
```

#Architecture
UI → API → DB

## Overview
This project simulates a real restaurant POS workflow including order creation, item modification, checkout, and status control.  
The system was later refactored to separate frontend and backend logic using FastAPI.


## Core Features
- Create new order
- Add / remove items
- Update quantity (+1 / -1)
- Delete order item
- Order status control (OPEN / PAID)
- API-based CRUD operations
- Database transaction to ensure data consistency

## Database Structure
- orders
- order_items
