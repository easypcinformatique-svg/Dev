// ========================================
// Sur Le Pouce ML - E-commerce Application
// Cart, Ordering & Checkout
// ========================================

(function() {
    'use strict';

    // ---- State ----
    let cart = [];
    let currentCategory = 'all';

    // ---- DOM Elements ----
    const productsGrid = document.getElementById('products-grid');
    const cartIcon = document.getElementById('cart-icon');
    const cartSidebar = document.getElementById('cart-sidebar');
    const cartOverlay = document.getElementById('cart-overlay');
    const cartClose = document.getElementById('cart-close');
    const cartItems = document.getElementById('cart-items');
    const cartFooter = document.getElementById('cart-footer');
    const cartCount = document.getElementById('cart-count');
    const cartTotalPrice = document.getElementById('cart-total-price');
    const btnCheckout = document.getElementById('btn-checkout');
    const checkoutModal = document.getElementById('checkout-modal');
    const modalClose = document.getElementById('modal-close');
    const checkoutForm = document.getElementById('checkout-form');
    const orderSummary = document.getElementById('order-summary');
    const confirmationModal = document.getElementById('confirmation-modal');
    const confirmationDetails = document.getElementById('confirmation-details');
    const contactForm = document.getElementById('contact-form');
    const menuToggle = document.querySelector('.menu-toggle');
    const navLinks = document.querySelector('.nav-links');
    const categoryTabs = document.querySelectorAll('.cat-tab');

    // ---- Init ----
    function init() {
        renderProducts('all');
        bindEvents();
        setMinDate();
        loadCartFromStorage();
    }

    // ---- Render Products ----
    function renderProducts(category) {
        currentCategory = category;
        const filtered = category === 'all'
            ? PRODUCTS
            : PRODUCTS.filter(p => p.category === category);

        productsGrid.innerHTML = filtered.map(product => `
            <div class="product-card" data-category="${product.category}">
                <div class="product-image">
                    <span>${product.emoji}</span>
                    ${product.badge ? `<span class="product-badge">${product.badge}</span>` : ''}
                </div>
                <div class="product-info">
                    <span class="product-category">${CATEGORY_LABELS[product.category] || product.category}</span>
                    <h3 class="product-name">${product.name}</h3>
                    <p class="product-desc">${product.desc}</p>
                    <div class="product-footer">
                        <span class="product-price">${formatPrice(product.price)}</span>
                        <button class="btn-add-cart" onclick="addToCart(${product.id})">+ Ajouter</button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // ---- Category Tabs ----
    function bindCategoryTabs() {
        categoryTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                categoryTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                renderProducts(tab.dataset.category);
            });
        });
    }

    // ---- Cart Functions ----
    window.addToCart = function(productId) {
        const product = PRODUCTS.find(p => p.id === productId);
        if (!product) return;

        const existing = cart.find(item => item.id === productId);
        if (existing) {
            existing.qty++;
        } else {
            cart.push({ ...product, qty: 1 });
        }

        updateCartUI();
        saveCartToStorage();
        showToast(`${product.name} ajouté au panier`);
    };

    window.addFormulaToCart = function(name, pricePerPerson, minPersons) {
        const formulaId = 'formula-' + name.replace(/\s+/g, '-').toLowerCase();
        const existing = cart.find(item => item.formulaId === formulaId);

        if (existing) {
            existing.qty += minPersons;
        } else {
            cart.push({
                id: Date.now(),
                formulaId: formulaId,
                name: name,
                desc: `${minPersons} personnes minimum`,
                price: pricePerPerson,
                qty: minPersons,
                emoji: '🎉',
                isFormula: true
            });
        }

        updateCartUI();
        saveCartToStorage();
        showToast(`${name} ajouté (${minPersons} pers.)`);
        openCart();
    };

    function removeFromCart(index) {
        cart.splice(index, 1);
        updateCartUI();
        saveCartToStorage();
    }

    function updateQty(index, delta) {
        cart[index].qty += delta;
        if (cart[index].qty <= 0) {
            cart.splice(index, 1);
        }
        updateCartUI();
        saveCartToStorage();
    }

    function getCartTotal() {
        return cart.reduce((sum, item) => sum + item.price * item.qty, 0);
    }

    function getCartCount() {
        return cart.reduce((sum, item) => sum + item.qty, 0);
    }

    // ---- Update Cart UI ----
    function updateCartUI() {
        const count = getCartCount();
        cartCount.textContent = count;

        if (cart.length === 0) {
            cartItems.innerHTML = '<p class="cart-empty">Votre panier est vide</p>';
            cartFooter.style.display = 'none';
            return;
        }

        cartFooter.style.display = 'block';
        cartTotalPrice.textContent = formatPrice(getCartTotal());

        cartItems.innerHTML = cart.map((item, index) => `
            <div class="cart-item">
                <div class="cart-item-icon">${item.emoji}</div>
                <div class="cart-item-details">
                    <div class="cart-item-name">${item.name}</div>
                    <div class="cart-item-price">${formatPrice(item.price)}${item.isFormula ? '/pers.' : ''}</div>
                </div>
                <div class="cart-item-qty">
                    <button class="qty-btn" onclick="updateCartQty(${index}, -1)">-</button>
                    <span>${item.qty}</span>
                    <button class="qty-btn" onclick="updateCartQty(${index}, 1)">+</button>
                </div>
            </div>
        `).join('');
    }

    window.updateCartQty = function(index, delta) {
        updateQty(index, delta);
    };

    // ---- Cart Open/Close ----
    function openCart() {
        cartSidebar.classList.add('active');
        cartOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeCart() {
        cartSidebar.classList.remove('active');
        cartOverlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    // ---- Checkout ----
    function openCheckout() {
        closeCart();
        renderOrderSummary();
        checkoutModal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeCheckout() {
        checkoutModal.classList.remove('active');
        document.body.style.overflow = '';
    }

    function renderOrderSummary() {
        let html = '<h4>Recapitulatif de commande</h4>';
        cart.forEach(item => {
            html += `<div class="order-summary-item">
                <span>${item.qty}x ${item.name}</span>
                <span>${formatPrice(item.price * item.qty)}</span>
            </div>`;
        });
        html += `<div class="order-summary-total">
            <span>Total</span>
            <span>${formatPrice(getCartTotal())}</span>
        </div>`;
        orderSummary.innerHTML = html;
    }

    function handleCheckout(e) {
        e.preventDefault();

        const formData = new FormData(checkoutForm);
        const orderData = {
            client: {
                nom: formData.get('nom'),
                prenom: formData.get('prenom'),
                email: formData.get('email'),
                tel: formData.get('tel'),
                adresse: formData.get('adresse'),
                cp: formData.get('cp'),
                ville: formData.get('ville')
            },
            livraison: {
                date: formData.get('date'),
                heure: formData.get('heure'),
                mode: formData.get('mode')
            },
            notes: formData.get('notes'),
            items: cart.map(item => ({
                name: item.name,
                qty: item.qty,
                price: item.price,
                subtotal: item.price * item.qty
            })),
            total: getCartTotal(),
            orderNumber: generateOrderNumber(),
            orderDate: new Date().toLocaleString('fr-FR')
        };

        // Show confirmation
        closeCheckout();
        showConfirmation(orderData);

        // Send order via email (mailto fallback)
        sendOrder(orderData);

        // Clear cart
        cart = [];
        updateCartUI();
        saveCartToStorage();
    }

    function showConfirmation(order) {
        confirmationDetails.innerHTML = `
            <p><strong>N° de commande :</strong> ${order.orderNumber}</p>
            <p><strong>Client :</strong> ${order.client.prenom} ${order.client.nom}</p>
            <p><strong>Telephone :</strong> ${order.client.tel}</p>
            <p><strong>Mode :</strong> ${order.livraison.mode === 'livraison' ? 'Livraison' : 'Retrait sur place'}</p>
            ${order.livraison.mode === 'livraison' ? `<p><strong>Adresse :</strong> ${order.client.adresse}, ${order.client.cp} ${order.client.ville}</p>` : ''}
            <p><strong>Date :</strong> ${formatDateFR(order.livraison.date)} a ${order.livraison.heure}</p>
            <hr style="margin:10px 0;border-color:#ddd;">
            ${order.items.map(i => `<p>${i.qty}x ${i.name} - ${formatPrice(i.subtotal)}</p>`).join('')}
            <hr style="margin:10px 0;border-color:#ddd;">
            <p><strong>Total : ${formatPrice(order.total)}</strong></p>
        `;
        confirmationModal.classList.add('active');
    }

    function sendOrder(order) {
        const subject = encodeURIComponent(`Nouvelle commande #${order.orderNumber} - Sur Le Pouce`);
        const itemsList = order.items.map(i => `  ${i.qty}x ${i.name} - ${formatPrice(i.subtotal)}`).join('\n');
        const body = encodeURIComponent(
            `NOUVELLE COMMANDE #${order.orderNumber}\n` +
            `Date: ${order.orderDate}\n\n` +
            `CLIENT:\n` +
            `Nom: ${order.client.prenom} ${order.client.nom}\n` +
            `Email: ${order.client.email}\n` +
            `Tel: ${order.client.tel}\n` +
            `Adresse: ${order.client.adresse}, ${order.client.cp} ${order.client.ville}\n\n` +
            `LIVRAISON:\n` +
            `Mode: ${order.livraison.mode}\n` +
            `Date: ${formatDateFR(order.livraison.date)} a ${order.livraison.heure}\n\n` +
            `COMMANDE:\n${itemsList}\n\n` +
            `TOTAL: ${formatPrice(order.total)}\n\n` +
            `Notes: ${order.notes || 'Aucune'}`
        );

        // Open mailto as fallback - in production, use a backend API
        window.open(`mailto:contact@surlepouceml.fr?subject=${subject}&body=${body}`, '_blank');
    }

    // ---- Contact Form ----
    function handleContact(e) {
        e.preventDefault();
        const nom = document.getElementById('devis-nom').value;
        const email = document.getElementById('devis-email').value;
        const tel = document.getElementById('devis-tel').value;
        const event = document.getElementById('devis-event').value;
        const personnes = document.getElementById('devis-personnes').value;
        const message = document.getElementById('devis-message').value;

        const subject = encodeURIComponent(`Demande de devis - ${event} - Sur Le Pouce`);
        const body = encodeURIComponent(
            `DEMANDE DE DEVIS\n\n` +
            `Nom: ${nom}\nEmail: ${email}\nTel: ${tel}\n` +
            `Evenement: ${event}\nNombre de personnes: ${personnes}\n\n` +
            `Message:\n${message}`
        );

        window.open(`mailto:contact@surlepouceml.fr?subject=${subject}&body=${body}`, '_blank');
        showToast('Demande de devis envoyee !');
        contactForm.reset();
    }

    // ---- Utilities ----
    function formatPrice(price) {
        return price.toFixed(2).replace('.', ',') + ' \u20AC';
    }

    function formatDateFR(dateStr) {
        const d = new Date(dateStr);
        return d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    }

    function generateOrderNumber() {
        const now = new Date();
        return 'SLP' + now.getFullYear().toString().slice(2) +
            String(now.getMonth() + 1).padStart(2, '0') +
            String(now.getDate()).padStart(2, '0') +
            String(now.getHours()).padStart(2, '0') +
            String(now.getMinutes()).padStart(2, '0') +
            String(Math.floor(Math.random() * 100)).padStart(2, '0');
    }

    function setMinDate() {
        const dateInput = document.getElementById('delivery-date');
        if (dateInput) {
            const tomorrow = new Date();
            tomorrow.setDate(tomorrow.getDate() + 1);
            dateInput.min = tomorrow.toISOString().split('T')[0];
        }
    }

    function showToast(message) {
        let toast = document.querySelector('.toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.className = 'toast';
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2500);
    }

    function saveCartToStorage() {
        try {
            localStorage.setItem('slp_cart', JSON.stringify(cart));
        } catch (e) { /* ignore */ }
    }

    function loadCartFromStorage() {
        try {
            const saved = localStorage.getItem('slp_cart');
            if (saved) {
                cart = JSON.parse(saved);
                updateCartUI();
            }
        } catch (e) { /* ignore */ }
    }

    // ---- Event Bindings ----
    function bindEvents() {
        // Cart
        cartIcon.addEventListener('click', openCart);
        cartOverlay.addEventListener('click', closeCart);
        cartClose.addEventListener('click', closeCart);
        btnCheckout.addEventListener('click', openCheckout);

        // Checkout modal
        modalClose.addEventListener('click', closeCheckout);
        checkoutForm.addEventListener('submit', handleCheckout);

        // Contact form
        contactForm.addEventListener('submit', handleContact);

        // Mobile menu
        menuToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });

        // Close mobile menu on link click
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => navLinks.classList.remove('active'));
        });

        // Category tabs
        bindCategoryTabs();

        // Close modals on escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeCart();
                closeCheckout();
            }
        });

        // Smooth scroll offset for fixed header
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    e.preventDefault();
                    const offset = 100;
                    const top = target.getBoundingClientRect().top + window.pageYOffset - offset;
                    window.scrollTo({ top, behavior: 'smooth' });
                }
            });
        });
    }

    // ---- Start ----
    document.addEventListener('DOMContentLoaded', init);
})();
