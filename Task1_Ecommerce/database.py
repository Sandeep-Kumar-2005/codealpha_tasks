import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()


# Check existing product columns
cursor.execute("PRAGMA table_info(products)")

columns = [column[1] for column in cursor.fetchall()]


# Add category column if it doesn't exist
if "category" not in columns:

    cursor.execute("""
        ALTER TABLE products
        ADD COLUMN category TEXT DEFAULT 'Other'
    """)


# Create orders table if needed
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT UNIQUE NOT NULL,
    customer_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL,
    total REAL NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")


# Create order items table if needed
cursor.execute("""
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    subtotal REAL NOT NULL
)
""")


# Give categories to existing products
cursor.execute("""
UPDATE products
SET category = 'Electronics'
WHERE name IN ('Smartphone', 'Laptop', 'Headphones', 'Smart Watch')
""")


cursor.execute("""
UPDATE products
SET category = 'Accessories'
WHERE name IN ('Keyboard', 'Wireless Mouse')
""")


conn.commit()

conn.close()

print("Database updated successfully!")