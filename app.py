import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_change_me')

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

# --- ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ ---
db_url = os.environ.get('DATABASE_URL', 'sqlite:///site.db')

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- МОДЕЛИ БАЗЫ ДАННЫХ ---

# 1. Сообщения и бронирования
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50), default='Новая') # Новая, Подтверждена, Отклонена

# 2. Позиции меню кофейни
class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False, default='Кофе') # Кофе, Авторские, Чай, Выпечка
    price = db.Column(db.String(50), nullable=False) # e.g. "180 ₽" или "180 / 220 ₽"
    volume = db.Column(db.String(50), default='300 мл')
    description = db.Column(db.Text, nullable=True)
    is_available = db.Column(db.Boolean, default=True) # Стоп-лист

with app.app_context():
    # db.drop_all()  # Пересоздаст таблицы под новую модель MenuItem
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
    # Загружаем позиции меню из БД
    menu_items = MenuItem.query.all()
    return render_template('portfolio.html', menu_items=menu_items)

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
            flash('Неверный логин или пароль управляющего!')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# --- КАБИНЕТ АДМИНИСТРАТОРА ---

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    messages = Message.query.order_by(Message.date.desc()).all()
    menu_items = MenuItem.query.all()

    stats = {
        'total_messages': len(messages),
        'unread_messages': Message.query.filter_by(is_read=False).count(),
        'total_menu_items': len(menu_items),
        'stop_list_count': MenuItem.query.filter_by(is_available=False).count()
    }

    return render_template('admin.html', messages=messages, menu_items=menu_items, stats=stats)

# Добавление новой позиции в меню
@app.route('/admin/add_menu_item', methods=['POST'])
def add_menu_item():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    title = request.form.get('title')
    category = request.form.get('category')
    price = request.form.get('price')
    volume = request.form.get('volume')
    description = request.form.get('description')

    new_item = MenuItem(title=title, category=category, price=price, volume=volume, description=description)
    db.session.add(new_item)
    db.session.commit()
    flash('Позиция успешно добавлена в меню кофейни!')
    return redirect(url_for('admin'))

# Переключение стоп-листа (В наличии / Нет в наличии)
@app.route('/admin/toggle_availability/<int:item_id>', methods=['POST'])
def toggle_availability(item_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    item = MenuItem.query.get_or_404(item_id)
    item.is_available = not item.is_available
    db.session.commit()
    return redirect(url_for('admin'))

# Удаление позиции из меню
@app.route('/admin/delete_menu_item/<int:item_id>', methods=['POST'])
def delete_menu_item(item_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    item = MenuItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Позиция удалена из меню!')
    return redirect(url_for('admin'))

# Управление статусом заявки / сообщения
@app.route('/admin/toggle_read/<int:msg_id>', methods=['POST'])
def toggle_read(msg_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    msg = Message.query.get_or_404(msg_id)
    msg.is_read = not msg.is_read
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/delete_message/<int:msg_id>', methods=['POST'])
def delete_message(msg_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    msg = Message.query.get_or_404(msg_id)
    db.session.delete(msg)
    db.session.commit()
    flash('Заявка удалена!')
    return redirect(url_for('admin'))

if __name__ == '__main__':
  app.run(debug=True)
