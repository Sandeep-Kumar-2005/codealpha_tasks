from flask import Flask, render_template, redirect, url_for, session, request
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "codealpha_secret_key"


# =========================================================
# ADMIN CREDENTIALS
# =========================================================

ADMIN_EMAIL = "admin@codealpha.com"
ADMIN_PASSWORD = "Admin@123"


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# CART
# =========================================================

def get_cart():

    cart = session.get("cart", {})

    if not isinstance(cart, dict):
        cart = {}
        session["cart"] = cart

    return cart


def get_cart_products():

    cart = get_cart()

    cart_products = []
    total = 0

    conn = get_db()

    image_map = {
        "Smartphone": "smartphone.jpg",
        "Laptop": "laptop.jpg",
        "Headphones": "headphones.jpg",
        "Smart Watch": "smartwatch.jpg",
        "Keyboard": "keyboard.jpg",
        "Wireless Mouse": "mouse.jpg"
    }

    for product_id, quantity in cart.items():

        try:
            product_id = int(product_id)
            quantity = int(quantity)
        except (ValueError, TypeError):
            continue

        product = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product:

            subtotal = product["price"] * quantity

            cart_products.append({
                "id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "description": product["description"],
                "category": product["category"],
                "quantity": quantity,
                "subtotal": subtotal,
                "image": image_map.get(
                    product["name"],
                    "smartphone.jpg"
                )
            })

            total += subtotal

    conn.close()

    return cart_products, total


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()

    conn = get_db()

    query = "SELECT * FROM products WHERE 1=1"
    parameters = []

    if search:

        query += """
            AND (
                name LIKE ?
                OR description LIKE ?
            )
        """

        search_value = "%" + search + "%"

        parameters.append(search_value)
        parameters.append(search_value)

    if category:

        query += " AND category = ?"
        parameters.append(category)

    query += " ORDER BY id ASC"

    products = conn.execute(
        query,
        parameters
    ).fetchall()

    categories = conn.execute("""
        SELECT DISTINCT category
        FROM products
        WHERE category IS NOT NULL
        AND category != ''
        ORDER BY category
    """).fetchall()

    conn.close()

    cart = get_cart()

    return render_template(
        "index.html",
        products=products,
        categories=categories,
        search=search,
        selected_category=category,
        cart_count=sum(cart.values()),
        logged_in="user_id" in session,
        user_name=session.get("user_name")
    )


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        if not name:
            name = request.form.get("username", "").strip()

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not name or not email or not password:

            return render_template(
                "register.html",
                error="Please fill in all fields."
            )

        if confirm_password and password != confirm_password:

            return render_template(
                "register.html",
                error="Passwords do not match."
            )

        conn = get_db()

        existing_user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:

            conn.close()

            return render_template(
                "register.html",
                error="An account with this email already exists."
            )

        conn.execute(
            """
            INSERT INTO users
            (name, email, password)
            VALUES (?, ?, ?)
            """,
            (
                name,
                email,
                password
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# =========================================================
# USER LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    # If admin is logged in, don't allow admin to enter user area
    if session.get("admin_logged_in"):
        session.pop("admin_logged_in", None)

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:

            return render_template(
                "login.html",
                error="Please enter your email and password."
            )

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            AND password = ?
            """,
            (
                email,
                password
            )
        ).fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]

            session.pop("admin_logged_in", None)

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Invalid email or password."
        )

    return render_template("login.html")


# =========================================================
# USER LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_email", None)

    return redirect(url_for("home"))


# =========================================================
# PRODUCT DETAILS
# =========================================================

@app.route("/product/<int:product_id>")
def product_details(product_id):

    conn = get_db()

    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    conn.close()

    if product is None:
        return "Product not found", 404

    cart = get_cart()

    return render_template(
        "product.html",
        product=product,
        cart_count=sum(cart.values()),
        logged_in="user_id" in session,
        user_name=session.get("user_name")
    )


# =========================================================
# ADD TO CART
# =========================================================

@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):

    conn = get_db()

    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    conn.close()

    if product is None:
        return "Product not found", 404

    cart = get_cart()

    product_id = str(product_id)

    cart[product_id] = cart.get(product_id, 0) + 1

    session["cart"] = cart
    session.modified = True

    return redirect(url_for("home"))


# =========================================================
# CART
# =========================================================

@app.route("/cart")
def cart():

    cart_products, total = get_cart_products()

    cart = get_cart()

    return render_template(
        "cart.html",
        cart=cart_products,
        cart_products=cart_products,
        total=total,
        cart_count=sum(cart.values()),
        logged_in="user_id" in session,
        user_name=session.get("user_name")
    )


# =========================================================
# INCREASE
# =========================================================

@app.route("/increase_quantity/<int:product_id>")
def increase_quantity(product_id):

    cart = get_cart()

    product_id = str(product_id)

    if product_id in cart:
        cart[product_id] += 1
    else:
        cart[product_id] = 1

    session["cart"] = cart
    session.modified = True

    return redirect(url_for("cart"))


@app.route("/increase/<int:product_id>")
def increase(product_id):

    return redirect(
        url_for(
            "increase_quantity",
            product_id=product_id
        )
    )


# =========================================================
# DECREASE
# =========================================================

@app.route("/decrease_quantity/<int:product_id>")
def decrease_quantity(product_id):

    cart = get_cart()

    product_id = str(product_id)

    if product_id in cart:

        cart[product_id] -= 1

        if cart[product_id] <= 0:
            del cart[product_id]

    session["cart"] = cart
    session.modified = True

    return redirect(url_for("cart"))


@app.route("/decrease/<int:product_id>")
def decrease(product_id):

    return redirect(
        url_for(
            "decrease_quantity",
            product_id=product_id
        )
    )


# =========================================================
# REMOVE
# =========================================================

@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):

    cart = get_cart()

    product_id = str(product_id)

    if product_id in cart:
        del cart[product_id]

    session["cart"] = cart
    session.modified = True

    return redirect(url_for("cart"))


# =========================================================
# CLEAR CART
# =========================================================

@app.route("/clear_cart")
def clear_cart():

    session["cart"] = {}
    session.modified = True

    return redirect(url_for("cart"))


# =========================================================
# CHECKOUT
# =========================================================

@app.route("/checkout")
def checkout():

    # User must be logged in to checkout
    if "user_id" not in session:

        return redirect(url_for("login"))

    cart_products, total = get_cart_products()

    if not cart_products:
        return redirect(url_for("cart"))

    cart = get_cart()

    return render_template(
        "checkout.html",
        cart_products=cart_products,
        cart=cart_products,
        total=total,
        cart_count=sum(cart.values()),
        logged_in=True,
        user_name=session.get("user_name"),
        user_email=session.get("user_email", "")
    )


# =========================================================
# PLACE ORDER
# =========================================================

@app.route("/place_order", methods=["POST"])
def place_order():

    # Only logged-in users can place orders
    if "user_id" not in session:

        return redirect(url_for("login"))

    name = request.form.get(
        "name",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip()

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    address = request.form.get(
        "address",
        ""
    ).strip()

    cart_products, total = get_cart_products()

    if not cart_products:
        return redirect(url_for("cart"))

    order_id = "CA" + datetime.now().strftime(
        "%Y%m%d%H%M%S%f"
    )

    conn = get_db()

    conn.execute(
        """
        INSERT INTO orders
        (
            order_id,
            customer_name,
            email,
            phone,
            address,
            total
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            order_id,
            name,
            email,
            phone,
            address,
            total
        )
    )

    for product in cart_products:

        conn.execute(
            """
            INSERT INTO order_items
            (
                order_id,
                product_name,
                price,
                quantity,
                subtotal
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                order_id,
                product["name"],
                product["price"],
                product["quantity"],
                product["subtotal"]
            )
        )

    conn.commit()
    conn.close()

    session["order"] = {
        "order_id": order_id,
        "name": name,
        "email": email,
        "phone": phone,
        "address": address,
        "total": total
    }

    session["cart"] = {}
    session.modified = True

    return redirect(url_for("order_success"))


# =========================================================
# ORDER SUCCESS
# =========================================================

@app.route("/order_success")
def order_success():

    order = session.get("order")

    if not order:
        return redirect(url_for("home"))

    return render_template(
        "success.html",
        order=order
    )


# =========================================================
# USER ORDERS
# =========================================================

@app.route("/orders")
def orders():

    if "user_id" not in session:

        return redirect(url_for("login"))

    email = session.get("user_email")

    conn = get_db()

    orders = conn.execute(
        """
        SELECT *
        FROM orders
        WHERE email = ?
        ORDER BY id DESC
        """,
        (email,)
    ).fetchall()

    conn.close()

    return render_template(
        "orders.html",
        orders=orders,
        user_name=session.get("user_name")
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():

    # Already logged-in admin
    if session.get("admin_logged_in"):

        return redirect(url_for("admin"))

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if (
            email == ADMIN_EMAIL
            and password == ADMIN_PASSWORD
        ):

            # Create admin session
            session["admin_logged_in"] = True

            # Remove normal user session
            session.pop("user_id", None)
            session.pop("user_name", None)
            session.pop("user_email", None)

            return redirect(url_for("admin"))

        return render_template(
            "admin_login.html",
            error="Invalid admin email or password."
        )

    return render_template("admin_login.html")


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin_logout")
def admin_logout():

    session.pop("admin_logged_in", None)

    return redirect(url_for("home"))


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
def admin():

    # =====================================================
    # SECURITY CHECK
    # =====================================================

    if not session.get("admin_logged_in"):

        return redirect(url_for("admin_login"))

    # =====================================================
    # DATABASE
    # =====================================================

    conn = get_db()

    orders = conn.execute(
        """
        SELECT *
        FROM orders
        ORDER BY id DESC
        """
    ).fetchall()

    users = conn.execute(
        """
        SELECT id, name, email
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    total_orders = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM orders
        """
    ).fetchone()["count"]

    total_sales = conn.execute(
        """
        SELECT COALESCE(SUM(total), 0) AS total
        FROM orders
        """
    ).fetchone()["total"]

    total_products = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM products
        """
    ).fetchone()["count"]

    total_users = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM users
        """
    ).fetchone()["count"]

    conn.close()

    return render_template(
        "admin.html",
        orders=orders,
        users=users,
        total_orders=total_orders,
        total_sales=total_sales,
        total_products=total_products,
        total_users=total_users
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )