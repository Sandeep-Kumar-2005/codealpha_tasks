import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, g

app = Flask(__name__)
DATABASE = 'project_manager.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT)''')
        db.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL, title TEXT NOT NULL, assigned_to TEXT, status TEXT DEFAULT 'To Do', FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE)''')
        db.execute('''CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER NOT NULL, author TEXT NOT NULL, content TEXT NOT NULL, FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE)''')
        db.commit()

INDEX_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Project Management Tool</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', sans-serif; }
        body { background-color: #f8fafc; color: #1e293b; padding: 40px 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { font-size: 28px; font-weight: 700; color: #0f172a; margin-bottom: 24px; }
        h2 { font-size: 20px; font-weight: 600; color: #334155; margin: 24px 0 16px 0; }
        .card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 24px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
        form { display: flex; flex-direction: column; gap: 12px; }
        input[type="text"], textarea { width: 100%; padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; outline: none; background: #fff; }
        input[type="text"]:focus, textarea:focus { border-color: #2563eb; }
        textarea { resize: vertical; min-height: 80px; }
        button { background-color: #2563eb; color: #ffffff; font-weight: 600; padding: 10px 18px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; align-self: flex-start; }
        button:hover { background-color: #1d4ed8; }
        .project-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
        .project-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
        .project-card h3 a { text-decoration: none; color: #2563eb; font-weight: 600; font-size: 18px; }
        .project-card p { color: #64748b; font-size: 14px; margin-top: 6px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>CodeAlpha - Project Management Tool</h1>
        <div class="card">
            <h2>Create New Project</h2>
            <form action="{{ url_for('add_project') }}" method="POST">
                <input type="text" name="title" placeholder="Project Title" required>
                <textarea name="description" placeholder="Project Description"></textarea>
                <button type="submit">Add Project</button>
            </form>
        </div>
        <h2>Projects Dashboard</h2>
        <div class="project-list">
            {% if projects %}
                {% for project in projects %}
                    <div class="project-card">
                        <h3><a href="{{ url_for('project_detail', project_id=project['id']) }}">{{ project['title'] }}</a></h3>
                        <p>{{ project['description'] or 'No description provided.' }}</p>
                    </div>
                {% endfor %}
            {% else %}
                <p>No projects found. Create one above!</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

PROJECT_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{{ project['title'] }} - Task Board</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Inter', sans-serif; }
        body { background-color: #f8fafc; color: #1e293b; padding: 40px 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { font-size: 28px; font-weight: 700; color: #0f172a; margin-bottom: 8px; }
        h2 { font-size: 20px; font-weight: 600; color: #334155; margin: 24px 0 16px 0; }
        .desc { color: #64748b; margin-bottom: 24px; font-size: 15px; }
        .card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
        form { display: flex; flex-direction: column; gap: 10px; }
        input[type="text"], select { width: 100%; padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; outline: none; background: #fff; }
        button { background-color: #2563eb; color: #ffffff; font-weight: 600; padding: 9px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; align-self: flex-start; }
        button:hover { background-color: #1d4ed8; }
        .back-link { display: inline-block; text-decoration: none; color: #2563eb; font-size: 14px; font-weight: 500; margin-bottom: 16px; }
        .task-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
        .task-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
        .task-card h4 { font-size: 16px; font-weight: 600; margin-bottom: 6px; color: #0f172a; }
        .comments-section { margin-top: 16px; padding-top: 12px; border-top: 1px solid #f1f5f9; }
        .comments-section h5 { font-size: 13px; color: #475569; margin-bottom: 8px; }
        .comment { background: #f8fafc; padding: 8px 10px; border-radius: 6px; font-size: 13px; margin-bottom: 6px; border: 1px solid #f1f5f9; }
        .comment-form { margin-top: 10px; gap: 6px; }
    </style>
</head>
<body>
    <div class="container">
        <a href="{{ url_for('index') }}" class="back-link">&larr; Back to Dashboard</a>
        <h1>{{ project['title'] }}</h1>
        <p class="desc">{{ project['description'] or 'No description provided.' }}</p>

        <div class="card">
            <h3>Add New Task</h3>
            <form action="{{ url_for('add_task', project_id=project['id']) }}" method="POST">
                <input type="text" name="title" placeholder="Task Title" required>
                <input type="text" name="assigned_to" placeholder="Assignee Name">
                <button type="submit">Create Task</button>
            </form>
        </div>

        <h2>Task Board</h2>
        <div class="task-grid">
            {% if tasks %}
                {% for task in tasks %}
                    <div class="task-card">
                        <h4>{{ task['title'] }}</h4>
                        <p style="font-size: 13px; color: #64748b; margin-bottom: 10px;"><strong>Assignee:</strong> {{ task['assigned_to'] or 'Unassigned' }}</p>
                        
                        <form action="{{ url_for('update_task_status', task_id=task['id'], project_id=project['id']) }}" method="POST">
                            <label style="font-size: 12px; font-weight: 600; color: #475569;">Status:</label>
                            <select name="status" onchange="this.form.submit()">
                                <option value="To Do" {% if task['status'] == 'To Do' %}selected{% endif %}>To Do</option>
                                <option value="In Progress" {% if task['status'] == 'In Progress' %}selected{% endif %}>In Progress</option>
                                <option value="Done" {% if task['status'] == 'Done' %}selected{% endif %}>Done</option>
                            </select>
                        </form>

                        <div class="comments-section">
                            <h5>Comments</h5>
                            {% set task_comments = comments_by_task.get(task['id'], []) %}
                            {% for c in task_comments %}
                                <div class="comment">
                                    <strong>{{ c['author'] }}:</strong> {{ c['content'] }}
                                </div>
                            {% endfor %}

                            <form action="{{ url_for('add_comment', task_id=task['id'], project_id=project['id']) }}" method="POST" class="comment-form">
                                <input type="text" name="author" placeholder="Your Name" required>
                                <input type="text" name="content" placeholder="Write a comment..." required>
                                <button type="submit">Post</button>
                            </form>
                        </div>
                    </div>
                {% endfor %}
            {% else %}
                <p>No tasks added yet.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    db = get_db()
    projects = db.execute('SELECT * FROM projects').fetchall()
    return render_template_string(INDEX_HTML, projects=projects)

@app.route('/project/add', methods=['POST'])
def add_project():
    title = request.form.get('title')
    description = request.form.get('description')
    if title:
        db = get_db()
        db.execute('INSERT INTO projects (title, description) VALUES (?, ?)', (title, description))
        db.commit()
    return redirect(url_for('index'))

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    db = get_db()
    project = db.execute('SELECT * FROM projects WHERE id = ?', (project_id,)).fetchone()
    if not project:
        return redirect(url_for('index'))
    tasks = db.execute('SELECT * FROM tasks WHERE project_id = ?', (project_id,)).fetchall()
    comments_by_task = {}
    for task in tasks:
        task_comments = db.execute('SELECT * FROM comments WHERE task_id = ?', (task['id'],)).fetchall()
        comments_by_task[task['id']] = task_comments
    return render_template_string(PROJECT_HTML, project=project, tasks=tasks, comments_by_task=comments_by_task)

@app.route('/task/add/<int:project_id>', methods=['POST'])
def add_task(project_id):
    title = request.form.get('title')
    assigned_to = request.form.get('assigned_to')
    if title:
        db = get_db()
        db.execute('INSERT INTO tasks (project_id, title, assigned_to) VALUES (?, ?, ?)', (project_id, title, assigned_to))
        db.commit()
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/task/update_status/<int:task_id>/<int:project_id>', methods=['POST'])
def update_task_status(task_id, project_id):
    status = request.form.get('status')
    if status:
        db = get_db()
        db.execute('UPDATE tasks SET status = ? WHERE id = ?', (status, task_id))
        db.commit()
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/comment/add/<int:task_id>/<int:project_id>', methods=['POST'])
def add_comment(task_id, project_id):
    author = request.form.get('author')
    content = request.form.get('content')
    if author and content:
        db = get_db()
        db.execute('INSERT INTO comments (task_id, author, content) VALUES (?, ?, ?)', (task_id, author, content))
        db.commit()
    return redirect(url_for('project_detail', project_id=project_id))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=8000)
