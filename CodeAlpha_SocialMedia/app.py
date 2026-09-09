import os
import sqlite3

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATABASE = os.path.join(BASE_DIR, "socialmedia.db")


# ============================================================
# FLASK APP
# ============================================================

app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR,
    static_url_path="/static"
)

app.secret_key = "codealpha_socialmedia_2026"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    connection = get_db()

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # --------------------------------------------------------
    # POSTS
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            content TEXT NOT NULL,
            likes INTEGER DEFAULT 0
        )
    """)

    # --------------------------------------------------------
    # COMMENTS
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------------------------
    # FOLLOWS
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS follows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id INTEGER NOT NULL,
            following_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(follower_id, following_id)
        )
    """)

    connection.commit()

    connection.close()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    connection = get_db()

    # --------------------------------------------------------
    # POSTS
    # --------------------------------------------------------

    posts = connection.execute("""
        SELECT *
        FROM posts
        ORDER BY id DESC
    """).fetchall()

    # --------------------------------------------------------
    # COMMENTS
    # --------------------------------------------------------

    comments = connection.execute("""
        SELECT *
        FROM comments
        ORDER BY id ASC
    """).fetchall()

    # --------------------------------------------------------
    # CURRENT USER
    # --------------------------------------------------------

    current_user_id = session.get("user_id")

    # --------------------------------------------------------
    # SUGGESTED USERS
    # --------------------------------------------------------

    suggested_users = []

    if current_user_id:

        suggested_users = connection.execute("""
            SELECT
                u.id,
                u.username,
                COUNT(f.id) AS follower_count
            FROM users u
            LEFT JOIN follows f
                ON u.id = f.following_id
            WHERE u.id != ?
            AND u.id NOT IN (
                SELECT following_id
                FROM follows
                WHERE follower_id = ?
            )
            GROUP BY u.id
            ORDER BY follower_count DESC, u.id ASC
            LIMIT 5
        """, (
            current_user_id,
            current_user_id
        )).fetchall()

    else:

        suggested_users = connection.execute("""
            SELECT
                u.id,
                u.username,
                COUNT(f.id) AS follower_count
            FROM users u
            LEFT JOIN follows f
                ON u.id = f.following_id
            GROUP BY u.id
            ORDER BY follower_count DESC, u.id ASC
            LIMIT 5
        """).fetchall()

    # --------------------------------------------------------
    # FOLLOW COUNTS
    # --------------------------------------------------------

    follower_count = 0
    following_count = 0

    if current_user_id:

        follower_result = connection.execute("""
            SELECT COUNT(*) AS total
            FROM follows
            WHERE following_id = ?
        """, (
            current_user_id,
        )).fetchone()

        following_result = connection.execute("""
            SELECT COUNT(*) AS total
            FROM follows
            WHERE follower_id = ?
        """, (
            current_user_id,
        )).fetchone()

        follower_count = follower_result["total"]
        following_count = following_result["total"]

    connection.close()

    # --------------------------------------------------------
    # GROUP COMMENTS BY POST
    # --------------------------------------------------------

    comments_by_post = {}

    for comment in comments:

        post_id = comment["post_id"]

        if post_id not in comments_by_post:
            comments_by_post[post_id] = []

        comments_by_post[post_id].append(comment)

    return render_template(
        "index.html",
        posts=posts,
        comments_by_post=comments_by_post,
        suggested_users=suggested_users,
        follower_count=follower_count,
        following_count=following_count
    )


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not username or not email or not password:

            return render_template(
                "register.html",
                error="Please fill in all fields."
            )

        connection = get_db()

        existing_user = connection.execute("""
            SELECT id
            FROM users
            WHERE email = ?
        """, (
            email,
        )).fetchone()

        if existing_user:

            connection.close()

            return render_template(
                "register.html",
                error="Email already registered."
            )

        existing_username = connection.execute("""
            SELECT id
            FROM users
            WHERE username = ?
        """, (
            username,
        )).fetchone()

        if existing_username:

            connection.close()

            return render_template(
                "register.html",
                error="Username already taken."
            )

        hashed_password = generate_password_hash(
            password
        )

        connection.execute("""
            INSERT INTO users
            (
                username,
                email,
                password
            )
            VALUES (?, ?, ?)
        """, (
            username,
            email,
            hashed_password
        ))

        connection.commit()

        connection.close()

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        connection = get_db()

        user = connection.execute("""
            SELECT *
            FROM users
            WHERE email = ?
        """, (
            email,
        )).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["email"] = user["email"]

            return redirect(
                url_for("home")
            )

        return render_template(
            "login.html",
            error="Invalid email or password."
        )

    return render_template(
        "login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================
# PROFILE
# ============================================================

@app.route("/profile")
def profile():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db()

    posts = connection.execute("""
        SELECT *
        FROM posts
        WHERE username = ?
        ORDER BY id DESC
    """, (
        session["username"],
    )).fetchall()

    follower_result = connection.execute("""
        SELECT COUNT(*) AS total
        FROM follows
        WHERE following_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    following_result = connection.execute("""
        SELECT COUNT(*) AS total
        FROM follows
        WHERE follower_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    connection.close()

    return render_template(
        "profile.html",
        posts=posts,
        follower_count=follower_result["total"],
        following_count=following_result["total"]
    )


# ============================================================
# CREATE POST
# ============================================================

@app.route(
    "/add_post",
    methods=["POST"]
)
def add_post():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    content = request.form.get(
        "content",
        ""
    ).strip()

    if content:

        connection = get_db()

        connection.execute("""
            INSERT INTO posts
            (
                username,
                content,
                likes
            )
            VALUES (?, ?, 0)
        """, (
            session["username"],
            content
        ))

        connection.commit()

        connection.close()

    return redirect(
        url_for("home")
    )


# ============================================================
# LIKE POST
# ============================================================

@app.route(
    "/like/<int:post_id>",
    methods=["POST"]
)
def like_post(post_id):

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    connection = get_db()

    post = connection.execute("""
        SELECT *
        FROM posts
        WHERE id = ?
    """, (
        post_id,
    )).fetchone()

    if post is None:

        connection.close()

        return jsonify({
            "success": False,
            "message": "Post not found."
        }), 404

    new_likes = post["likes"] + 1

    connection.execute("""
        UPDATE posts
        SET likes = ?
        WHERE id = ?
    """, (
        new_likes,
        post_id
    ))

    connection.commit()

    connection.close()

    return jsonify({
        "success": True,
        "likes": new_likes
    })


# ============================================================
# ADD COMMENT
# ============================================================

@app.route(
    "/add_comment/<int:post_id>",
    methods=["POST"]
)
def add_comment(post_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    content = request.form.get(
        "content",
        ""
    ).strip()

    if not content:

        return redirect(
            url_for("home")
        )

    connection = get_db()

    post = connection.execute("""
        SELECT id
        FROM posts
        WHERE id = ?
    """, (
        post_id,
    )).fetchone()

    if post is None:

        connection.close()

        return redirect(
            url_for("home")
        )

    connection.execute("""
        INSERT INTO comments
        (
            post_id,
            username,
            content
        )
        VALUES (?, ?, ?)
    """, (
        post_id,
        session["username"],
        content
    ))

    connection.commit()

    connection.close()

    return redirect(
        url_for("home")
    )


# ============================================================
# DELETE COMMENT
# ============================================================

@app.route(
    "/delete_comment/<int:comment_id>",
    methods=["POST"]
)
def delete_comment(comment_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db()

    comment = connection.execute("""
        SELECT *
        FROM comments
        WHERE id = ?
        AND username = ?
    """, (
        comment_id,
        session["username"]
    )).fetchone()

    if comment:

        connection.execute("""
            DELETE FROM comments
            WHERE id = ?
        """, (
            comment_id,
        ))

        connection.commit()

    connection.close()

    return redirect(
        url_for("home")
    )


# ============================================================
# DELETE POST
# ============================================================

@app.route(
    "/delete_post/<int:post_id>",
    methods=["POST"]
)
def delete_post(post_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    connection = get_db()

    post = connection.execute("""
        SELECT *
        FROM posts
        WHERE id = ?
        AND username = ?
    """, (
        post_id,
        session["username"]
    )).fetchone()

    if post:

        connection.execute("""
            DELETE FROM comments
            WHERE post_id = ?
        """, (
            post_id,
        ))

        connection.execute("""
            DELETE FROM posts
            WHERE id = ?
        """, (
            post_id,
        ))

        connection.commit()

    connection.close()

    return redirect(
        url_for("home")
    )


# ============================================================
# FOLLOW USER
# ============================================================

@app.route(
    "/follow/<int:user_id>",
    methods=["POST"]
)
def follow_user(user_id):

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    current_user_id = session["user_id"]

    # Cannot follow yourself
    if current_user_id == user_id:

        return jsonify({
            "success": False,
            "message": "You cannot follow yourself."
        }), 400

    connection = get_db()

    # Check whether target user exists
    target_user = connection.execute("""
        SELECT id, username
        FROM users
        WHERE id = ?
    """, (
        user_id,
    )).fetchone()

    if target_user is None:

        connection.close()

        return jsonify({
            "success": False,
            "message": "User not found."
        }), 404

    # Check existing follow
    existing_follow = connection.execute("""
        SELECT id
        FROM follows
        WHERE follower_id = ?
        AND following_id = ?
    """, (
        current_user_id,
        user_id
    )).fetchone()

    if existing_follow:

        connection.close()

        return jsonify({
            "success": False,
            "message": "Already following this user."
        }), 400

    # Create follow
    connection.execute("""
        INSERT INTO follows
        (
            follower_id,
            following_id
        )
        VALUES (?, ?)
    """, (
        current_user_id,
        user_id
    ))

    connection.commit()

    # Get new follower count
    follower_count = connection.execute("""
        SELECT COUNT(*) AS total
        FROM follows
        WHERE following_id = ?
    """, (
        user_id,
    )).fetchone()["total"]

    connection.close()

    return jsonify({
        "success": True,
        "following": True,
        "username": target_user["username"],
        "follower_count": follower_count
    })


# ============================================================
# UNFOLLOW USER
# ============================================================

@app.route(
    "/unfollow/<int:user_id>",
    methods=["POST"]
)
def unfollow_user(user_id):

    if "user_id" not in session:

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    current_user_id = session["user_id"]

    connection = get_db()

    connection.execute("""
        DELETE FROM follows
        WHERE follower_id = ?
        AND following_id = ?
    """, (
        current_user_id,
        user_id
    ))

    connection.commit()

    follower_count = connection.execute("""
        SELECT COUNT(*) AS total
        FROM follows
        WHERE following_id = ?
    """, (
        user_id,
    )).fetchone()["total"]

    connection.close()

    return jsonify({
        "success": True,
        "following": False,
        "follower_count": follower_count
    })


# ============================================================
# FOLLOW STATUS
# ============================================================

@app.route(
    "/api/follow_status/<int:user_id>"
)
def follow_status(user_id):

    if "user_id" not in session:

        return jsonify({
            "logged_in": False,
            "following": False
        })

    connection = get_db()

    follow = connection.execute("""
        SELECT id
        FROM follows
        WHERE follower_id = ?
        AND following_id = ?
    """, (
        session["user_id"],
        user_id
    )).fetchone()

    follower_count = connection.execute("""
        SELECT COUNT(*) AS total
        FROM follows
        WHERE following_id = ?
    """, (
        user_id,
    )).fetchone()["total"]

    connection.close()

    return jsonify({
        "logged_in": True,
        "following": follow is not None,
        "follower_count": follower_count
    })


# ============================================================
# CURRENT USER API
# ============================================================

@app.route("/api/me")
def api_me():

    if "user_id" not in session:

        return jsonify({
            "logged_in": False
        })

    connection = get_db()

    follower_count = connection.execute("""
        SELECT COUNT(*) AS total
        FROM follows
        WHERE following_id = ?
    """, (
        session["user_id"],
    )).fetchone()["total"]

    following_count = connection.execute("""
        SELECT COUNT(*) AS total
        FROM follows
        WHERE follower_id = ?
    """, (
        session["user_id"],
    )).fetchone()["total"]

    connection.close()

    return jsonify({
        "logged_in": True,
        "user_id": session["user_id"],
        "username": session["username"],
        "email": session["email"],
        "followers": follower_count,
        "following": following_count
    })


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    init_db()

    print()
    print("==========================================")
    print("       CODEALPHA SOCIAL MEDIA")
    print("==========================================")
    print()

    print("APP       :", __file__)
    print("TEMPLATES :", TEMPLATES_DIR)
    print("STATIC    :", STATIC_DIR)

    print()

    print(
        "INDEX EXISTS   :",
        os.path.exists(
            os.path.join(
                TEMPLATES_DIR,
                "index.html"
            )
        )
    )

    print(
        "LOGIN EXISTS   :",
        os.path.exists(
            os.path.join(
                TEMPLATES_DIR,
                "login.html"
            )
        )
    )

    print(
        "REGISTER EXISTS:",
        os.path.exists(
            os.path.join(
                TEMPLATES_DIR,
                "register.html"
            )
        )
    )

    print()
    print("==========================================")
    print()

    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True
    )