# 🛒 CodeAlpha E-Commerce Store

A full-stack e-commerce web application built using Python, Flask, SQLite, HTML, CSS, and Jinja2.

## 🚀 Features

### 👤 User Features

- User registration and login
- User logout
- Product browsing
- Product search
- Category filtering
- Product details
- Add to cart
- Increase/decrease quantity
- Remove products from cart
- Checkout
- Place orders
- Order confirmation
- My Orders
- User-specific order history

### 🔐 Admin Features

- Separate admin login
- Secure admin dashboard
- View all registered users
- View all customer orders
- View total orders
- View total sales
- View total products
- View total users
- Separate admin logout
- Users cannot access the admin dashboard

## 🛠️ Technologies Used

- Python
- Flask
- SQLite
- HTML5
- CSS3
- Jinja2
- Git
- GitHub

## 🛒 Shopping Flow

Register / Login → Browse Products → Add to Cart → Checkout → Place Order → Order Confirmation → My Orders

## 🔐 Admin Flow

Admin Login → Authentication → Admin Dashboard → Users & Orders Management

## 🗄️ Database

SQLite is used to store:

- User accounts
- Products
- Orders
- Order items

## 📂 Project Structure

```text
CodeAlpha_Ecommerce/
│
├── app.py
├── database.db
├── README.md
├── requirements.txt
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── cart.html
│   ├── checkout.html
│   ├── orders.html
│   ├── success.html
│   ├── product.html
│   ├── admin_login.html
│   └── admin.html
│
└── static/
    └── images/