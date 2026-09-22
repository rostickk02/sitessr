import os
import json
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

# 3. Предзаказы (Take Away)
class TakeawayOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(50), nullable=False)
    pickup_time = db.Column(db.String(20), nullable=False)
    items_summary = db.Column(db.Text, nullable=False) # Итоговый список позиций
    total_price = db.Column(db.Integer, nullable=False) # Общая сумма
    comment = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_completed = db.Column(db.Boolean, default=False)

with app.app_context():
    # db.drop_all()  # Раскомментируйте, если требуется пересоздать таблицы с нуля
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

# --- ОБРАБОТКА ПРЕДЗАКАЗА (TAKE AWAY) ---

@app.route('/takeaway', methods=['POST'])
def create_takeaway_order():
    raw_cart = request.form.get('cart_data')
    name = request.form.get('customer_name')
    phone = request.form.get('customer_phone')
    pickup_time = request.form.get('pickup_time')
    comment = request.form.get('comment')

    if not raw_cart or raw_cart == '[]':
        flash('Ваша корзина пуста!')
        return redirect(url_for('portfolio'))

    try:
        cart_items = json.loads(raw_cart)
    except json.JSONDecodeError:
        flash('Ошибка обработки корзины!')
        return redirect(url_for('portfolio'))

    # Формируем читаемую строку со списком заказанных позиций
    items_summary = ", ".join([f"{item['name']} x{item['quantity']}" for item in cart_items])
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)

    new_order = TakeawayOrder(
        customer_name=name,
        customer_phone=phone,
        pickup_time=pickup_time,
        items_summary=items_summary,
        total_price=total_price,
        comment=comment
    )
    
    db.session.add(new_order)
    db.session.commit()

    flash('Ваш предзаказ успешно оформлен! Ждём вас в назначеское время.')
    return redirect(url_for('portfolio'))

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
    takeaway_orders = TakeawayOrder.query.order_by(TakeawayOrder.date.desc()).all()

    stats = {
        'total_messages': len(messages),
        'unread_messages': Message.query.filter_by(is_read=False).count(),
        'total_menu_items': len(menu_items),
        'stop_list_count': MenuItem.query.filter_by(is_available=False).count(),
        'total_takeaway': len(takeaway_orders)
    }

    return render_template('admin.html', messages=messages, menu_items=menu_items, takeaway_orders=takeaway_orders, stats=stats)

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

# Отметка или удаление предзаказов из админки
@app.route('/admin/delete_takeaway/<int:order_id>', methods=['POST'])
def delete_takeaway(order_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    order = TakeawayOrder.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash('Предзаказ удален!')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
