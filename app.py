import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_change_me')

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

# --- ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ ---
# Если переменная DATABASE_URL есть (на Render), используем PostgreSQL.
# Иначе подключаем локальную базу SQLite.
db_url = os.environ.get('DATABASE_URL', 'sqlite:///site.db')

# Исправление особенности строк подключения PostgreSQL на Render (postgres:// -> postgresql://)
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- МОДЕЛИ БАЗЫ ДАННЫХ ---

# 1. Таблица сообщений с поддержкой статуса прочтения (is_read)
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

# 2. Таблица проектов портфолио
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    tech = db.Column(db.String(200), nullable=False)  # Технологии через запятую
    icon = db.Column(db.String(100), default='fa-solid fa-code')

with app.app_context():
    db.create_all()

# --- ОСНОВНЫЕ МАРШРУТЫ ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/portfolio')
def portfolio():
    projects = Project.query.all()
    
    projects_data = []
    for p in projects:
        tech_list = [t.strip() for t in p.tech.split(',') if t.strip()]
        projects_data.append({
            'id': p.id,
            'title': p.title,
            'description': p.description,
            'tech': tech_list,
            'icon': p.icon
        })
        
    return render_template('portfolio.html', projects=projects_data)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('username')
        msg = request.form.get('user_message')

        new_msg = Message(username=name, user_message=msg)
        db.session.add(new_msg)
        db.session.commit()

        return render_template('contact.html', name=name, message=msg)

    return render_template('contact.html')

# --- АВТОРИЗАЦИЯ ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Неверный логин или пароль!')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# --- ПАНЕЛЬ АДМИНИСТРАТОРА И УПРАВЛЕНИЕ ---

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    messages = Message.query.order_by(Message.date.desc()).all()
    projects = Project.query.all()

    # Сбор статистики
    total_messages = len(messages)
    unread_messages = Message.query.filter_by(is_read=False).count()
    total_projects = len(projects)

    stats = {
        'total_messages': total_messages,
        'unread_messages': unread_messages,
        'total_projects': total_projects
    }

    return render_template('admin.html', messages=messages, projects=projects, stats=stats)

# Удаление сообщения
@app.route('/admin/delete_message/<int:msg_id>', methods=['POST'])
def delete_message(msg_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    msg = Message.query.get_or_404(msg_id)
    db.session.delete(msg)
    db.session.commit()
    flash('Сообщение успешно удалено!')
    return redirect(url_for('admin'))

# Переключение статуса прочтения
@app.route('/admin/toggle_read/<int:msg_id>', methods=['POST'])
def toggle_read(msg_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    msg = Message.query.get_or_404(msg_id)
    msg.is_read = not msg.is_read
    db.session.commit()
    return redirect(url_for('admin'))

# Добавление нового проекта
@app.route('/admin/add_project', methods=['POST'])
def add_project():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    title = request.form.get('title')
    description = request.form.get('description')
    tech = request.form.get('tech')
    icon = request.form.get('icon') or 'fa-solid fa-code'

    new_project = Project(title=title, description=description, tech=tech, icon=icon)
    db.session.add(new_project)
    db.session.commit()
    flash('Новый проект успешно добавлен!')
    return redirect(url_for('admin'))

# Удаление проекта
@app.route('/admin/delete_project/<int:proj_id>', methods=['POST'])
def delete_project(proj_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    project = Project.query.get_or_404(proj_id)
    db.session.delete(project)
    db.session.commit()
    flash('Проект удален из портфолио!')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
