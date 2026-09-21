from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Секретный ключ для работы сессий (паролей/авторизации)
app.secret_key = 'super_secret_key_change_me'

# Настройки администратора (логин и пароль)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'  # Вы можете изменить пароль на свой!

# Настройка базы данных SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель таблицы сообщений в БД
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/portfolio')
def portfolio():
    projects_list = [
        {
            'title': 'Мой первый сайт на Flask',
            'description': 'Многостраничный сайт с базой данных SQLite, тёмной темой и формой обратной связи.',
            'tech': ['Python', 'Flask', 'HTML/CSS', 'SQLite'],
            'icon': 'fa-solid fa-code'
        },
        {
            'title': 'Телеграм-бот на Python',
            'description': 'Чат-бот для автоматической обработки команд и взаимодействия с пользователями.',
            'tech': ['Python', 'aiogram', 'API'],
            'icon': 'fa-brands fa-telegram'
        },
        {
            'title': 'Дизайн макет в Photoshop',
            'description': 'Авторский UX/UI макет интерфейса, подготовленный для дальнейшей верстки.',
            'tech': ['Photoshop', 'UI/UX', 'Design'],
            'icon': 'fa-solid fa-paintbrush'
        }
    ]
    return render_template('portfolio.html', projects=projects_list)

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

# Страница входа в админку
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

# Выход из админки
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Защищенная панель администратора
@app.route('/admin')
def admin():
    # Проверяем, авторизован ли пользователь
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    all_messages = Message.query.order_by(Message.date.desc()).all()
    return render_template('admin.html', messages=all_messages)

if __name__ == '__main__':
    app.run(debug=True)