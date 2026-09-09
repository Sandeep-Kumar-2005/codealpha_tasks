from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

DATABASE = "project_manager.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Planning',
            priority TEXT DEFAULT 'Medium',
            deadline TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = get_db()

    projects = conn.execute("""
        SELECT p.*,
        COUNT(t.id) AS total_tasks,
        SUM(CASE WHEN t.status = 'Completed' THEN 1 ELSE 0 END)
        AS completed_tasks
        FROM projects p
        LEFT JOIN tasks t ON p.id = t.project_id
        GROUP BY p.id
        ORDER BY p.id DESC
    """).fetchall()

    total_projects = conn.execute(
        "SELECT COUNT(*) FROM projects"
    ).fetchone()[0]

    active_projects = conn.execute("""
        SELECT COUNT(*) FROM projects
        WHERE status != 'Completed'
    """).fetchone()[0]

    completed_projects = conn.execute("""
        SELECT COUNT(*) FROM projects
        WHERE status = 'Completed'
    """).fetchone()[0]

    total_tasks = conn.execute(
        "SELECT COUNT(*) FROM tasks"
    ).fetchone()[0]

    completed_tasks = conn.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE status = 'Completed'
    """).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        projects=projects,
        total_projects=total_projects,
        active_projects=active_projects,
        completed_projects=completed_projects,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks
    )


@app.route("/add_project", methods=["POST"])
def add_project():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    priority = request.form.get("priority", "Medium")
    deadline = request.form.get("deadline", "")

    if name:
        conn = get_db()

        conn.execute("""
            INSERT INTO projects
            (name, description, priority, deadline)
            VALUES (?, ?, ?, ?)
        """, (name, description, priority, deadline))

        conn.commit()
        conn.close()

    return redirect(url_for("index"))


@app.route("/delete_project/<int:project_id>", methods=["POST"])
def delete_project(project_id):
    conn = get_db()

    conn.execute(
        "DELETE FROM tasks WHERE project_id = ?",
        (project_id,)
    )

    conn.execute(
        "DELETE FROM projects WHERE id = ?",
        (project_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("index"))


@app.route("/update_status/<int:project_id>", methods=["POST"])
def update_status(project_id):
    status = request.form.get("status", "Planning")

    conn = get_db()

    conn.execute("""
        UPDATE projects
        SET status = ?
        WHERE id = ?
    """, (status, project_id))

    conn.commit()
    conn.close()

    return redirect(url_for("index"))


@app.route("/add_task/<int:project_id>", methods=["POST"])
def add_task(project_id):
    title = request.form.get("title", "").strip()

    if title:
        conn = get_db()

        conn.execute("""
            INSERT INTO tasks (project_id, title)
            VALUES (?, ?)
        """, (project_id, title))

        conn.commit()
        conn.close()

    return redirect(url_for("index"))


@app.route("/complete_task/<int:task_id>", methods=["POST"])
def complete_task(task_id):
    conn = get_db()

    conn.execute("""
        UPDATE tasks
        SET status = 'Completed'
        WHERE id = ?
    """, (task_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("index"))


@app.route("/delete_task/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    conn = get_db()

    conn.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("index"))


@app.route("/project/<int:project_id>")
def project_details(project_id):
    conn = get_db()

    project = conn.execute(
        "SELECT * FROM projects WHERE id = ?",
        (project_id,)
    ).fetchone()

    tasks = conn.execute("""
        SELECT * FROM tasks
        WHERE project_id = ?
        ORDER BY id DESC
    """, (project_id,)).fetchall()

    conn.close()

    if project is None:
        return redirect(url_for("index"))

    return render_template(
        "project.html",
        project=project,
        tasks=tasks
    )


init_db()


if __name__ == "__main__":
    app.run(debug=True, port=5002)