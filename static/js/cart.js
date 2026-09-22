// Хранилище корзины в localStorage
let cart = JSON.parse(localStorage.getItem('sidorov_cart')) || [];

document.addEventListener('DOMContentLoaded', () => {
    updateCartCount();
    renderCartModal();
});

// Добавление товара
function addToCart(id, name, price) {
    const existing = cart.find(item => item.id === id);
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({ id, name, price, quantity: 1 });
    }
    saveCart();
    showNotification(`«${name}» добавлен в корзину`);
}

// Изменение количества
function changeQuantity(id, delta) {
    const item = cart.find(i => i.id === id);
    if (!item) return;
    
    item.quantity += delta;
    if (item.quantity <= 0) {
        cart = cart.filter(i => i.id !== id);
    }
    saveCart();
    renderCartModal();
}

function saveCart() {
    localStorage.setItem('sidorov_cart', JSON.stringify(cart));
    updateCartCount();
}

function updateCartCount() {
    const count = cart.reduce((sum, item) => sum + item.quantity, 0);
    const badge = document.getElementById('cart-badge');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-block' : 'none';
    }
}

// Отображение содержимого модального окна
function renderCartModal() {
    const cartContainer = document.getElementById('cart-items-list');
    const totalPriceEl = document.getElementById('cart-total-price');
    const cartItemsInput = document.getElementById('cart-items-json');
    
    if (!cartContainer) return;

    if (cart.length === 0) {
        cartContainer.innerHTML = '<p class="empty-cart-msg">Ваша корзина пуста</p>';
        if (totalPriceEl) totalPriceEl.textContent = '0 ₽';
        if (cartItemsInput) cartItemsInput.value = '';
        return;
    }

    let total = 0;
    cartContainer.innerHTML = cart.map(item => {
        const itemTotal = item.price * item.quantity;
        total += itemTotal;
        return `
            <div class="cart-item-row">
                <div class="cart-item-info">
                    <strong>${item.name}</strong>
                    <span>${item.price} ₽</span>
                </div>
                <div class="cart-item-controls">
                    <button type="button" onclick="changeQuantity(${item.id}, -1)">-</button>
                    <span>${item.quantity}</span>
                    <button type="button" onclick="changeQuantity(${item.id}, 1)">+</button>
                </div>
            </div>
        `;
    }).join('');

    if (totalPriceEl) totalPriceEl.textContent = `${total} ₽`;
    if (cartItemsInput) cartItemsInput.value = JSON.stringify(cart);
}

// Открытие / закрытие модалки
function toggleCartModal() {
    const modal = document.getElementById('cart-modal');
    if (modal) {
        renderCartModal();
        modal.classList.toggle('active');
    }
}

function showNotification(text) {
    const toast = document.createElement('div');
    toast.className = 'cart-toast';
    toast.textContent = text;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}
