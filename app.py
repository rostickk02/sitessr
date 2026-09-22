import os
import json
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_change_me')

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

# --- НАСТРОЙКИ TELEGRAM БОТА ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', 'YOUR_CHAT_ID_HERE')

def send_telegram_notification(text):
    """Отправка сообщений в Telegram"""
    if TELEGRAM_BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE' or not TELEGRAM_BOT_TOKEN:
        print("Telegram Bot Token не настроен.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

# --- ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ ---
db_url = os.environ.get('DATABASE_URL', 'sqlite:///site.db')

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- МОДЕЛИ БАЗЫ ДАННЫХ ---

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50), default='Новая')

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False, default='Кофе')
    price = db.Column(db.String(50), nullable=False)
    volume = db.Column(db.String(50), default='300 мл')
    description = db.Column(db.Text, nullable=True)
    is_available = db.Column(db.Boolean, default=True)

class TakeawayOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(50), nullable=False)
    pickup_time = db.Column(db.String(20), nullable=False)
    items_summary = db.Column(db.Text, nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    is_completed = db.Column(db.Boolean, default=False)

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

        # Уведомление в Telegram
        tg_message = (
            f"📩 <b>НОВАЯ БРОНЬ / СООБЩЕНИЕ</b>\n\n"
            f"👤 <b>От кого:</b> {name}\n"
            f"💬 <b>Текст:</b> {msg}"
        )
        send_telegram_notification(tg_message)

        return render_template('contact.html', name=name, message=msg)

    return render_template('contact.html')

@app.route('/takeaway', methods=['POST'])
def create_takeaway_order():
    raw_cart = request.form.get('cart_data')
    name = request.form.get('customer_name')
    phone = request.form.get('customer_phone')
    pickup_time = request.form.get('pickup_time')
    comment = request.form.get('comment') or "Нет"

    if not raw_cart or raw_cart == '[]':
        flash('Ваша корзина пуста!')
        return redirect(url_for('portfolio'))

    try:
        cart_items = json.loads(raw_cart)
    except json.JSONDecodeError:
        flash('Ошибка обработки корзины!')
        return redirect(url_for('portfolio'))

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

    # Уведомление в Telegram
    tg_message = (
        f"🛍 <b>НОВЫЙ ПРЕДЗАКАЗ (Take Away)</b>\n\n"
        f"👤 <b>Имя:</b> {name}\n"
        f"📞 <b>Телефон:</b> {phone}\n"
        f"⏰ <b>Самовывоз:</b> {pickup_time}\n"
        f"🛒 <b>Заказ:</b> {items_summary}\n"
        f"💰 <b>Сумма:</b> {total_price} ₽\n"
        f"💬 <b>Коммент:</b> {comment}"
    )
    send_telegram_notification(tg_message)

    flash('Ваш предзаказ успешно оформлен!')
    return redirect(url_for('portfolio'))

# --- АВТОРИЗАЦИЯ И АДМИНКА ---

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

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    messages = Message.query.order_by(Message.date.desc()).all()
    menu_items = MenuItem.query.all()
    takeaway_orders = TakeawayOrder.query.order_by(TakeawayOrder.date.desc()).all()

    # Сбор данных для аналитики
    days_map = {0: 'Пн', 1: 'Вт', 2: 'Ср', 3: 'Чт', 4: 'Пт', 5: 'Сб', 6: 'Вс'}
    bookings_by_day = [0] * 7
    for msg in messages:
        if msg.date:
            bookings_by_day[msg.date.weekday()] += 1

    items_count = {}
    for order in takeaway_orders:
        parts = order.items_summary.split(',')
        for part in parts:
            part = part.strip()
            if ' x' in part:
                name, qty = part.rsplit(' x', 1)
                try:
                    items_count[name] = items_count.get(name, 0) + int(qty)
                except ValueError:
                    pass

    sorted_items = sorted(items_count.items(), key=lambda x: x[1], reverse=True)[:5]
    popular_labels = [item[0] for item in sorted_items] or ["Нет данных"]
    popular_data = [item[1] for item in sorted_items] or [0]

    stats = {
        'total_messages': len(messages),
        'unread_messages': Message.query.filter_by(is_read=False).count(),
        'total_menu_items': len(menu_items),
        'stop_list_count': MenuItem.query.filter_by(is_available=False).count(),
        'total_takeaway': len(takeaway_orders)
    }

    return render_template(
        'admin.html', 
        messages=messages, 
        menu_items=menu_items, 
        takeaway_orders=takeaway_orders, 
        stats=stats,
        chart_days_labels=list(days_map.values()),
        chart_days_data=bookings_by_day,
        popular_labels=popular_labels,
        popular_data=popular_data
    )

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
    flash('Позиция добавлена!')
    return redirect(url_for('admin'))

@app.route('/admin/toggle_availability/<int:item_id>', methods=['POST'])
def toggle_availability(item_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    item = MenuItem.query.get_or_404(item_id)
    item.is_available = not item.is_available
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/delete_menu_item/<int:item_id>', methods=['POST'])
def delete_menu_item(item_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    item = MenuItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Позиция удалена!')
    return redirect(url_for('admin'))

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
