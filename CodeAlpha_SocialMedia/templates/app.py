import os
import sqlite3
from datetime import datetime

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
from werkzeug.utils import secure_filename


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")

DATABASE = os.path.join(BASE_DIR, "socialmedia.db")


# Create upload folder automatically
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# ============================================================
# ALLOWED IMAGE TYPES
# ============================================================

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp"
}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():

    connection = sqlite3.connect(DATABASE)

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

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
            username TEXT UNIQUE NOT NULL,
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
            UNIQUE(follower_id, following_id)
        )
    """)

    # --------------------------------------------------------
    # LIKE TRACKING
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS post_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            UNIQUE(post_id, user_id)
        )
    """)

    # --------------------------------------------------------
    # NOTIFICATIONS
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sender_id INTEGER,
            type TEXT NOT NULL,
            post_id INTEGER,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------------------------
    # MESSAGES
    # --------------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------------------------
    # SAFE MIGRATIONS FOR OLD DATABASE
    # --------------------------------------------------------

    existing_columns = [
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(posts)"
        ).fetchall()
    ]

    if "image" not in existing_columns:

        connection.execute("""
            ALTER TABLE posts
            ADD COLUMN image TEXT
        """)

    if "feeling" not in existing_columns:

        connection.execute("""
            ALTER TABLE posts
            ADD COLUMN feeling TEXT
        """)

    connection.commit()

    connection.close()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def login_required():

    return "user_id" in session


def create_notification(
    connection,
    user_id,
    sender_id,
    notification_type,
    message,
    post_id=None
):

    if user_id == sender_id:
        return

    connection.execute("""
        INSERT INTO notifications (
            user_id,
            sender_id,
            type,
            post_id,
            message
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        sender_id,
        notification_type,
        post_id,
        message
    ))


def get_user_by_id(connection, user_id):

    return connection.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        user_id,
    )).fetchone()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    connection = get_db()

    posts = connection.execute("""
        SELECT
            p.*,
            u.id AS user_id,
            u.username AS post_username
        FROM posts p
        LEFT JOIN users u
            ON LOWER(u.username) = LOWER(p.username)
        ORDER BY p.id DESC
    """).fetchall()

    comments = connection.execute("""
        SELECT *
        FROM comments
        ORDER BY id ASC
    """).fetchall()

    comments_by_post = {}

    for comment in comments:

        post_id = comment["post_id"]

        if post_id not in comments_by_post:
            comments_by_post[post_id] = []

        comments_by_post[post_id].append(comment)

    current_user_id = session.get("user_id")

    # --------------------------------------------------------
    # SUGGESTED USERS
    # --------------------------------------------------------

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
            GROUP BY u.id, u.username
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
            GROUP BY u.id, u.username
            ORDER BY follower_count DESC, u.id ASC
            LIMIT 5
        """).fetchall()

    # --------------------------------------------------------
    # CURRENT USER COUNTS
    # --------------------------------------------------------

    follower_count = 0
    following_count = 0
    notification_count = 0
    unread_messages = 0

    if current_user_id:

        follower_count = connection.execute("""
            SELECT COUNT(*)
            FROM follows
            WHERE following_id = ?
        """, (
            current_user_id,
        )).fetchone()[0]

        following_count = connection.execute("""
            SELECT COUNT(*)
            FROM follows
            WHERE follower_id = ?
        """, (
            current_user_id,
        )).fetchone()[0]

        notification_count = connection.execute("""
            SELECT COUNT(*)
            FROM notifications
            WHERE user_id = ?
              AND is_read = 0
        """, (
            current_user_id,
        )).fetchone()[0]

        unread_messages = connection.execute("""
            SELECT COUNT(*)
            FROM messages
            WHERE receiver_id = ?
              AND is_read = 0
        """, (
            current_user_id,
        )).fetchone()[0]

    connection.close()

    return render_template(
        "index.html",
        posts=posts,
        comments_by_post=comments_by_post,
        suggested_users=suggested_users,
        follower_count=follower_count,
        following_count=following_count,
        notification_count=notification_count,
        unread_messages=unread_messages
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
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        # Validation
        if not username or not email or not password:

            return render_template(
                "register.html",
                error="Please fill in all fields."
            )

        if len(username) < 3:

            return render_template(
                "register.html",
                error="Username must contain at least 3 characters."
            )

        if len(password) < 6:

            return render_template(
                "register.html",
                error="Password must contain at least 6 characters."
            )

        connection = get_db()

        # Email check
        existing_email = connection.execute("""
            SELECT id
            FROM users
            WHERE email = ?
        """, (
            email,
        )).fetchone()

        if existing_email:

            connection.close()

            return render_template(
                "register.html",
                error="Email already registered."
            )

        # Username check
        existing_username = connection.execute("""
            SELECT id
            FROM users
            WHERE LOWER(username) = LOWER(?)
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
            INSERT INTO users (
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

        return redirect(url_for("login"))

    return render_template("register.html")


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

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

            session.clear()

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["email"] = user["email"]

            return redirect(url_for("home"))

        return render_template(
            "login.html",
            error="Invalid email or password."
        )

    return render_template("login.html")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ============================================================
# PROFILE
# ============================================================

@app.route("/profile")
def profile():

    if not login_required():
        return redirect(url_for("login"))

    connection = get_db()

    profile_user = connection.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if profile_user is None:

        connection.close()

        session.clear()

        return redirect(url_for("login"))

    posts = connection.execute("""
        SELECT *
        FROM posts
        WHERE username = ?
        ORDER BY id DESC
    """, (
        profile_user["username"],
    )).fetchall()

    follower_count = connection.execute("""
        SELECT COUNT(*)
        FROM follows
        WHERE following_id = ?
    """, (
        profile_user["id"],
    )).fetchone()[0]

    following_count = connection.execute("""
        SELECT COUNT(*)
        FROM follows
        WHERE follower_id = ?
    """, (
        profile_user["id"],
    )).fetchone()[0]

    post_count = connection.execute("""
        SELECT COUNT(*)
        FROM posts
        WHERE username = ?
    """, (
        profile_user["username"],
    )).fetchone()[0]

    connection.close()

    return render_template(
        "profile.html",
        profile_user=profile_user,
        user=profile_user,
        posts=posts,
        follower_count=follower_count,
        following_count=following_count,
        post_count=post_count
    )


# ============================================================
# CREATE POST
# ============================================================

@app.route("/add_post", methods=["POST"])
def add_post():

    if not login_required():
        return redirect(url_for("login"))

    content = request.form.get(
        "content",
        ""
    ).strip()

    feeling = request.form.get(
        "feeling",
        ""
    ).strip()

    image_file = request.files.get("image")

    image_filename = None

    # --------------------------------------------------------
    # IMAGE UPLOAD
    # --------------------------------------------------------

    if image_file and image_file.filename:

        if not allowed_file(image_file.filename):

            return redirect(url_for("home"))

        original_name = secure_filename(
            image_file.filename
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d%H%M%S%f"
        )

        image_filename = (
            str(session["user_id"])
            + "_"
            + timestamp
            + "_"
            + original_name
        )

        image_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            image_filename
        )

        image_file.save(image_path)

    # Don't create completely empty posts
    if not content and not image_filename:

        return redirect(url_for("home"))

    connection = get_db()

    connection.execute("""
        INSERT INTO posts (
            username,
            content,
            likes,
            image,
            feeling
        )
        VALUES (?, ?, 0, ?, ?)
    """, (
        session["username"],
        content,
        image_filename,
        feeling
    ))

    connection.commit()

    connection.close()

    return redirect(url_for("home"))


# ============================================================
# LIKE / UNLIKE POST
# ============================================================

@app.route("/like/<int:post_id>", methods=["POST"])
def like_post(post_id):

    if not login_required():

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    user_id = session["user_id"]

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

    existing_like = connection.execute("""
        SELECT id
        FROM post_likes
        WHERE post_id = ?
          AND user_id = ?
    """, (
        post_id,
        user_id
    )).fetchone()

    # --------------------------------------------------------
    # UNLIKE
    # --------------------------------------------------------

    if existing_like:

        connection.execute("""
            DELETE FROM post_likes
            WHERE post_id = ?
              AND user_id = ?
        """, (
            post_id,
            user_id
        ))

        connection.execute("""
            UPDATE posts
            SET likes = (
                SELECT COUNT(*)
                FROM post_likes
                WHERE post_id = ?
            )
            WHERE id = ?
        """, (
            post_id,
            post_id
        ))

        connection.commit()

        likes = connection.execute("""
            SELECT likes
            FROM posts
            WHERE id = ?
        """, (
            post_id,
        )).fetchone()["likes"]

        connection.close()

        return jsonify({
            "success": True,
            "liked": False,
            "likes": likes
        })

    # --------------------------------------------------------
    # LIKE
    # --------------------------------------------------------

    connection.execute("""
        INSERT INTO post_likes (
            post_id,
            user_id
        )
        VALUES (?, ?)
    """, (
        post_id,
        user_id
    ))

    connection.execute("""
        UPDATE posts
        SET likes = (
            SELECT COUNT(*)
            FROM post_likes
            WHERE post_id = ?
        )
        WHERE id = ?
    """, (
        post_id,
        post_id
    ))

    # Notify post owner
    owner = connection.execute("""
        SELECT u.id
        FROM users u
        WHERE LOWER(u.username) = LOWER(?)
    """, (
        post["username"],
    )).fetchone()

    if owner:

        create_notification(
            connection,
            owner["id"],
            user_id,
            "like",
            f"{session['username']} liked your post.",
            post_id
        )

    connection.commit()

    likes = connection.execute("""
        SELECT likes
        FROM posts
        WHERE id = ?
    """, (
        post_id,
    )).fetchone()["likes"]

    connection.close()

    return jsonify({
        "success": True,
        "liked": True,
        "likes": likes
    })


# ============================================================
# ADD COMMENT
# ============================================================

@app.route("/add_comment/<int:post_id>", methods=["POST"])
def add_comment(post_id):

    if not login_required():
        return redirect(url_for("login"))

    content = request.form.get(
        "content",
        ""
    ).strip()

    if not content:
        return redirect(url_for("home"))

    if len(content) > 1000:
        content = content[:1000]

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

        return redirect(url_for("home"))

    connection.execute("""
        INSERT INTO comments (
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

    # Notify post owner
    owner = connection.execute("""
        SELECT id
        FROM users
        WHERE LOWER(username) = LOWER(?)
    """, (
        post["username"],
    )).fetchone()

    if owner:

        create_notification(
            connection,
            owner["id"],
            session["user_id"],
            "comment",
            f"{session['username']} commented on your post.",
            post_id
        )

    connection.commit()

    connection.close()

    return redirect(url_for("home"))


# ============================================================
# DELETE COMMENT
# ============================================================

@app.route("/delete_comment/<int:comment_id>", methods=["POST"])
def delete_comment(comment_id):

    if not login_required():
        return redirect(url_for("login"))

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

    return redirect(url_for("home"))


# ============================================================
# DELETE POST
# ============================================================

@app.route("/delete_post/<int:post_id>", methods=["POST"])
def delete_post(post_id):

    if not login_required():
        return redirect(url_for("login"))

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

        # Delete comments
        connection.execute("""
            DELETE FROM comments
            WHERE post_id = ?
        """, (
            post_id,
        ))

        # Delete likes
        connection.execute("""
            DELETE FROM post_likes
            WHERE post_id = ?
        """, (
            post_id,
        ))

        # Delete notifications
        connection.execute("""
            DELETE FROM notifications
            WHERE post_id = ?
        """, (
            post_id,
        ))

        # Delete image file
        if post["image"]:

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                post["image"]
            )

            if os.path.exists(image_path):

                try:
                    os.remove(image_path)
                except OSError:
                    pass

        # Delete post
        connection.execute("""
            DELETE FROM posts
            WHERE id = ?
        """, (
            post_id,
        ))

        connection.commit()

    connection.close()

    return redirect(url_for("home"))


# ============================================================
# FOLLOW USER
# ============================================================

@app.route("/follow/<int:user_id>", methods=["POST"])
def follow_user(user_id):

    if not login_required():

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    current_user_id = session["user_id"]

    if current_user_id == user_id:

        return jsonify({
            "success": False,
            "message": "You cannot follow yourself."
        }), 400

    connection = get_db()

    target_user = get_user_by_id(
        connection,
        user_id
    )

    if target_user is None:

        connection.close()

        return jsonify({
            "success": False,
            "message": "User not found."
        }), 404

    existing_follow = connection.execute("""
        SELECT id
        FROM follows
        WHERE follower_id = ?
          AND following_id = ?
    """, (
        current_user_id,
        user_id
    )).fetchone()

    if not existing_follow:

        connection.execute("""
            INSERT INTO follows (
                follower_id,
                following_id
            )
            VALUES (?, ?)
        """, (
            current_user_id,
            user_id
        ))

        create_notification(
            connection,
            user_id,
            current_user_id,
            "follow",
            f"{session['username']} started following you."
        )

        connection.commit()

    follower_count = connection.execute("""
        SELECT COUNT(*)
        FROM follows
        WHERE following_id = ?
    """, (
        user_id,
    )).fetchone()[0]

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

@app.route("/unfollow/<int:user_id>", methods=["POST"])
def unfollow_user(user_id):

    if not login_required():

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    connection = get_db()

    connection.execute("""
        DELETE FROM follows
        WHERE follower_id = ?
          AND following_id = ?
    """, (
        session["user_id"],
        user_id
    ))

    connection.commit()

    follower_count = connection.execute("""
        SELECT COUNT(*)
        FROM follows
        WHERE following_id = ?
    """, (
        user_id,
    )).fetchone()[0]

    connection.close()

    return jsonify({
        "success": True,
        "following": False,
        "follower_count": follower_count
    })


# ============================================================
# FOLLOW STATUS
# ============================================================

@app.route("/api/follow_status/<int:user_id>")
def follow_status(user_id):

    if not login_required():

        return jsonify({
            "logged_in": False,
            "following": False,
            "follower_count": 0
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
        SELECT COUNT(*)
        FROM follows
        WHERE following_id = ?
    """, (
        user_id,
    )).fetchone()[0]

    connection.close()

    return jsonify({
        "logged_in": True,
        "following": follow is not None,
        "follower_count": follower_count
    })


# ============================================================
# NOTIFICATIONS
# ============================================================

@app.route("/notifications")
def notifications():

    if not login_required():
        return redirect(url_for("login"))

    connection = get_db()

    notification_list = connection.execute("""
        SELECT
            n.*,
            u.username AS sender_username
        FROM notifications n
        LEFT JOIN users u
            ON n.sender_id = u.id
        WHERE n.user_id = ?
        ORDER BY n.id DESC
        LIMIT 50
    """, (
        session["user_id"],
    )).fetchall()

    # Mark as read
    connection.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
    """, (
        session["user_id"],
    ))

    connection.commit()

    connection.close()

    return render_template(
        "notifications.html",
        notifications=notification_list
    )


# ============================================================
# NOTIFICATIONS API
# ============================================================

@app.route("/api/notifications")
def notifications_api():

    if not login_required():

        return jsonify({
            "logged_in": False,
            "notifications": []
        })

    connection = get_db()

    notification_list = connection.execute("""
        SELECT
            n.id,
            n.type,
            n.message,
            n.post_id,
            n.is_read,
            n.created_at,
            u.username AS sender_username
        FROM notifications n
        LEFT JOIN users u
            ON n.sender_id = u.id
        WHERE n.user_id = ?
        ORDER BY n.id DESC
        LIMIT 50
    """, (
        session["user_id"],
    )).fetchall()

    unread = connection.execute("""
        SELECT COUNT(*)
        FROM notifications
        WHERE user_id = ?
          AND is_read = 0
    """, (
        session["user_id"],
    )).fetchone()[0]

    connection.close()

    return jsonify({
        "logged_in": True,
        "unread": unread,
        "notifications": [
            dict(notification)
            for notification in notification_list
        ]
    })


# ============================================================
# MARK NOTIFICATIONS READ
# ============================================================

@app.route("/notifications/read", methods=["POST"])
def mark_notifications_read():

    if not login_required():

        return jsonify({
            "success": False
        }), 401

    connection = get_db()

    connection.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
    """, (
        session["user_id"],
    ))

    connection.commit()

    connection.close()

    return jsonify({
        "success": True
    })


# ============================================================
# MESSAGES
# ============================================================

@app.route("/messages")
def messages():

    if not login_required():
        return redirect(url_for("login"))

    connection = get_db()

    users = connection.execute("""
        SELECT id, username
        FROM users
        WHERE id != ?
        ORDER BY username ASC
    """, (
        session["user_id"],
    )).fetchall()

    connection.close()

    return render_template(
        "messages.html",
        users=users
    )


# ============================================================
# SEND MESSAGE
# ============================================================

@app.route("/send_message", methods=["POST"])
def send_message():

    if not login_required():

        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    receiver_id = request.form.get(
        "receiver_id",
        ""
    ).strip()

    content = request.form.get(
        "content",
        ""
    ).strip()

    if not receiver_id or not content:

        return jsonify({
            "success": False,
            "message": "Receiver and message are required."
        }), 400

    try:
        receiver_id = int(receiver_id)
    except ValueError:

        return jsonify({
            "success": False,
            "message": "Invalid receiver."
        }), 400

    if receiver_id == session["user_id"]:

        return jsonify({
            "success": False,
            "message": "You cannot message yourself."
        }), 400

    connection = get_db()

    receiver = get_user_by_id(
        connection,
        receiver_id
    )

    if receiver is None:

        connection.close()

        return jsonify({
            "success": False,
            "message": "User not found."
        }), 404

    connection.execute("""
        INSERT INTO messages (
            sender_id,
            receiver_id,
            content
        )
        VALUES (?, ?, ?)
    """, (
        session["user_id"],
        receiver_id,
        content
    ))

    create_notification(
        connection,
        receiver_id,
        session["user_id"],
        "message",
        f"{session['username']} sent you a message."
    )

    connection.commit()

    connection.close()

    return jsonify({
        "success": True,
        "message": "Message sent."
    })


# ============================================================
# CONVERSATION
# ============================================================

@app.route("/api/messages/<int:user_id>")
def conversation(user_id):

    if not login_required():

        return jsonify({
            "logged_in": False
        }), 401

    current_user_id = session["user_id"]

    connection = get_db()

    other_user = get_user_by_id(
        connection,
        user_id
    )

    if other_user is None:

        connection.close()

        return jsonify({
            "success": False,
            "message": "User not found."
        }), 404

    messages_list = connection.execute("""
        SELECT
            m.id,
            m.sender_id,
            m.receiver_id,
            m.content,
            m.created_at,
            u.username AS sender_username
        FROM messages m
        JOIN users u
            ON m.sender_id = u.id
        WHERE
            (
                m.sender_id = ?
                AND m.receiver_id = ?
            )
            OR
            (
                m.sender_id = ?
                AND m.receiver_id = ?
            )
        ORDER BY m.id ASC
    """, (
        current_user_id,
        user_id,
        user_id,
        current_user_id
    )).fetchall()

    # Mark received messages as read
    connection.execute("""
        UPDATE messages
        SET is_read = 1
        WHERE sender_id = ?
          AND receiver_id = ?
    """, (
        user_id,
        current_user_id
    ))

    connection.commit()

    connection.close()

    return jsonify({
        "success": True,
        "user": {
            "id": other_user["id"],
            "username": other_user["username"]
        },
        "messages": [
            dict(message)
            for message in messages_list
        ]
    })


# ============================================================
# CURRENT USER API
# ============================================================

@app.route("/api/me")
def api_me():

    if not login_required():

        return jsonify({
            "logged_in": False
        })

    connection = get_db()

    follower_count = connection.execute("""
        SELECT COUNT(*)
        FROM follows
        WHERE following_id = ?
    """, (
        session["user_id"],
    )).fetchone()[0]

    following_count = connection.execute("""
        SELECT COUNT(*)
        FROM follows
        WHERE follower_id = ?
    """, (
        session["user_id"],
    )).fetchone()[0]

    post_count = connection.execute("""
        SELECT COUNT(*)
        FROM posts
        WHERE username = ?
    """, (
        session["username"],
    )).fetchone()[0]

    notification_count = connection.execute("""
        SELECT COUNT(*)
        FROM notifications
        WHERE user_id = ?
          AND is_read = 0
    """, (
        session["user_id"],
    )).fetchone()[0]

    message_count = connection.execute("""
        SELECT COUNT(*)
        FROM messages
        WHERE receiver_id = ?
          AND is_read = 0
    """, (
        session["user_id"],
    )).fetchone()[0]

    connection.close()

    return jsonify({
        "logged_in": True,
        "user_id": session["user_id"],
        "username": session["username"],
        "email": session["email"],
        "followers": follower_count,
        "following": following_count,
        "posts": post_count,
        "notifications": notification_count,
        "messages": message_count
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/api/health")
def health():

    return jsonify({
        "status": "ok",
        "application": "Socially",
        "year": 2026
    })


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "success": False,
        "message": "Image is too large. Maximum size is 10 MB."
    }), 413


@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "index.html"
    ), 404


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    init_db()

    print()
    print("==========================================")
    print("          SOCIALLY - SOCIAL MEDIA")
    print("==========================================")
    print()
    print("Server: http://127.0.0.1:5001")
    print()

    app.run(
        debug=True,
        port=5001
    )