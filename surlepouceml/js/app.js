/* ═══════════════════════════════════════
   Sur Le Pouce ML — Application
   Part 1: Init, Products, Cart
   ═══════════════════════════════════════ */
(function(){
'use strict';

let cart = [];
let currentCat = 'all';

// ── DOM refs ──
const $ = id => document.getElementById(id);
const productsGrid = $('products-grid');
const filterBar = $('filter-bar');
const cartBadge = $('cart-badge');
const cartToggle = $('cart-toggle');
const cartOverlay = $('cart-overlay');
const cartDrawer = $('cart-drawer');
const cartDrawerClose = $('cart-drawer-close');
const cartDrawerBody = $('cart-drawer-body');
const cartDrawerFooter = $('cart-drawer-footer');
const cartEmpty = $('cart-empty');
const cartSubtotalVal = $('cart-subtotal-val');
const btnCheckout = $('btn-checkout');
const btnContinue = $('btn-continue');
const cartEmptyBrowse = $('cart-empty-browse');
const checkoutOverlay = $('checkout-overlay');
const checkoutClose = $('checkout-close');
const menuBurger = $('menu-burger');
const navLinks = $('nav-links');
const mobileOverlay = $('mobile-overlay');
const toast = $('toast');
const intro = $('intro');

// ── Format price ──
function fmtPrice(n) { return n.toFixed(2).replace('.',',') + ' €'; }

// ── Init ──
function init() {
    loadCart();
    renderProducts('all');
    bindEvents();
    initScrollAnimations();
    setMinDate();
    lucide.createIcons();
    // Launch intro cinematic
    startIntro();
}

// ═══════════════════════════════════════
// CINÉMATIQUE INTRO
// ═══════════════════════════════════════
function startIntro() {
    const steps = [
        $('intro-step-1'),
        $('intro-step-2'),
        $('intro-step-3'),
    ];
    const slides = document.querySelectorAll('.intro-slide');
    let currentStep = 0;
    let slideIndex = 0;
    let introTimer = null;
    let slideTimer = null;

    // Slideshow rotation
    function nextSlide() {
        slides[slideIndex].classList.remove('active');
        slideIndex = (slideIndex + 1) % slides.length;
        slides[slideIndex].classList.add('active');
    }
    slideTimer = setInterval(nextSlide, 4000);

    // Step transitions
    function nextStep() {
        if (currentStep < steps.length - 1) {
            steps[currentStep].classList.remove('active');
            steps[currentStep].classList.add('exit');
            currentStep++;
            // Reset animations by re-adding the step
            steps[currentStep].classList.add('active');
        }
    }

    // Timeline: step1 (3.5s) → step2 (3.5s) → step3 (3s) → close
    introTimer = setTimeout(() => {
        nextStep(); // → step 2
        introTimer = setTimeout(() => {
            nextStep(); // → step 3 (logo)
            introTimer = setTimeout(() => {
                closeIntro();
            }, 3500);
        }, 3500);
    }, 3500);

    // Skip button
    $('intro-skip').addEventListener('click', () => {
        clearTimeout(introTimer);
        clearInterval(slideTimer);
        closeIntro();
    });

    function closeIntro() {
        clearInterval(slideTimer);
        intro.classList.add('hidden');
        document.body.style.overflow = '';
        // Remove from DOM after animation
        setTimeout(() => { if (intro.parentNode) intro.parentNode.removeChild(intro); }, 1000);
    }

    // Block scroll during intro
    document.body.style.overflow = 'hidden';
}

// ── Render Products ──
function renderProducts(cat) {
    currentCat = cat;
    const items = cat === 'all' ? PRODUCTS : PRODUCTS.filter(p => p.cat === cat);
    productsGrid.innerHTML = items.map((p, i) => `
        <div class="product-card animate-on-scroll" style="transition-delay:${(i % 6) * 80}ms" data-cat="${p.cat}">
            <div class="product-card-img">
                <img src="${p.img}" alt="${p.name}" loading="lazy">
                ${p.badge ? `<span class="product-badge badge-${p.badgeType}">${p.badge}</span>` : ''}
            </div>
            <div class="product-card-body">
                <h3 class="product-card-name">${p.name}</h3>
                <p class="product-card-desc">${p.desc}</p>
                <div class="product-card-footer">
                    <span class="product-card-price">${fmtPrice(p.price)}</span>
                    <button class="btn-add" onclick="SLP.addToCart(${p.id})" aria-label="Ajouter ${p.name} au panier">
                        <i data-lucide="plus" class="icon-sm"></i> Ajouter
                    </button>
                </div>
            </div>
        </div>
    `).join('');
    lucide.createIcons();
    // Re-observe new cards
    requestAnimationFrame(() => {
        document.querySelectorAll('.product-card.animate-on-scroll').forEach(el => {
            scrollObserver.observe(el);
        });
    });
}

// ── Cart Logic ──
function addToCart(id) {
    const product = PRODUCTS.find(p => p.id === id);
    if (!product) return;
    const existing = cart.find(c => c.id === id);
    if (existing) { existing.qty++; }
    else { cart.push({ ...product, qty: 1 }); }
    saveCart();
    updateCartUI();
    showToast(product.name + ' ajouté au panier');
    // Animate badge
    cartBadge.style.transform = 'scale(1.4)';
    setTimeout(() => { cartBadge.style.transform = 'scale(1)'; }, 300);
}

function removeFromCart(id) {
    cart = cart.filter(c => c.id !== id);
    saveCart();
    updateCartUI();
}

function updateQty(id, delta) {
    const item = cart.find(c => c.id === id);
    if (!item) return;
    item.qty += delta;
    if (item.qty <= 0) { removeFromCart(id); return; }
    saveCart();
    updateCartUI();
}

function getTotal() { return cart.reduce((s, c) => s + c.price * c.qty, 0); }
function getCount() { return cart.reduce((s, c) => s + c.qty, 0); }

function updateCartUI() {
    const count = getCount();
    cartBadge.textContent = count;
    if (cart.length === 0) {
        cartEmpty.hidden = false;
        cartDrawerFooter.hidden = true;
        cartDrawerBody.querySelectorAll('.cart-item').forEach(el => el.remove());
        return;
    }
    cartEmpty.hidden = true;
    cartDrawerFooter.hidden = false;
    cartSubtotalVal.textContent = fmtPrice(getTotal());
    // Render items
    const existingItems = cartDrawerBody.querySelectorAll('.cart-item');
    existingItems.forEach(el => el.remove());
    cart.forEach(item => {
        const div = document.createElement('div');
        div.className = 'cart-item';
        div.innerHTML = `
            <div class="cart-item-img"><img src="${item.img}" alt="${item.name}" loading="lazy"></div>
            <div class="cart-item-info">
                <div class="cart-item-name">${item.name}</div>
                <div class="cart-item-price">${fmtPrice(item.price)}</div>
            </div>
            <div class="cart-item-qty">
                <button class="qty-btn" onclick="SLP.updateQty(${item.id},-1)" aria-label="Diminuer quantité">−</button>
                <span>${item.qty}</span>
                <button class="qty-btn" onclick="SLP.updateQty(${item.id},1)" aria-label="Augmenter quantité">+</button>
            </div>
            <button class="cart-item-remove" onclick="SLP.removeFromCart(${item.id})" aria-label="Supprimer ${item.name}">
                <i data-lucide="trash-2" class="icon-sm"></i>
            </button>
        `;
        cartDrawerBody.appendChild(div);
    });
    lucide.createIcons();
}

// ── Cart drawer ──
function openCart() {
    cartDrawer.classList.add('active');
    cartOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}
function closeCart() {
    cartDrawer.classList.remove('active');
    cartOverlay.classList.remove('active');
    document.body.style.overflow = '';
}

// ── Storage ──
function saveCart() {
    try { localStorage.setItem('slp_cart', JSON.stringify(cart)); } catch(e) {}
}
function loadCart() {
    try {
        const d = localStorage.getItem('slp_cart');
        if (d) { cart = JSON.parse(d); updateCartUI(); }
    } catch(e) {}
}

// ── Toast ──
function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2500);
}

// ── Scroll animations ──
let scrollObserver;
function initScrollAnimations() {
    scrollObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                scrollObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    document.querySelectorAll('.animate-on-scroll').forEach(el => scrollObserver.observe(el));
}

// ── Min date ──
function setMinDate() {
    const dateInput = $('c-date');
    const devisDate = $('devis-date');
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    // Skip to Monday if weekend
    while (tomorrow.getDay() === 0 || tomorrow.getDay() === 6) {
        tomorrow.setDate(tomorrow.getDate() + 1);
    }
    const minStr = tomorrow.toISOString().split('T')[0];
    if (dateInput) dateInput.min = minStr;
    if (devisDate) devisDate.min = minStr;
}

// ── Expose globals ──
window.SLP = { addToCart, removeFromCart, updateQty };

// ── Bind events ──
function bindEvents() {
    // Cart
    cartToggle.addEventListener('click', openCart);
    cartOverlay.addEventListener('click', closeCart);
    cartDrawerClose.addEventListener('click', closeCart);
    btnContinue.addEventListener('click', closeCart);
    cartEmptyBrowse.addEventListener('click', () => {
        closeCart();
        document.getElementById('carte').scrollIntoView({behavior:'smooth'});
    });

    // Mobile menu
    menuBurger.addEventListener('click', () => {
        navLinks.classList.toggle('active');
        mobileOverlay.classList.toggle('active');
    });
    mobileOverlay.addEventListener('click', () => {
        navLinks.classList.remove('active');
        mobileOverlay.classList.remove('active');
    });
    navLinks.querySelectorAll('a').forEach(a => {
        a.addEventListener('click', () => {
            navLinks.classList.remove('active');
            mobileOverlay.classList.remove('active');
        });
    });

    // Filters
    filterBar.querySelectorAll('.filter-pill').forEach(btn => {
        btn.addEventListener('click', () => {
            filterBar.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderProducts(btn.dataset.cat);
        });
    });

    // Smooth scroll with offset
    document.querySelectorAll('a[href^="#"]').forEach(a => {
        a.addEventListener('click', e => {
            const target = document.querySelector(a.getAttribute('href'));
            if (target) {
                e.preventDefault();
                const top = target.getBoundingClientRect().top + window.pageYOffset - 100;
                window.scrollTo({ top, behavior: 'smooth' });
            }
        });
    });

    // Escape key
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') { closeCart(); closeCheckout(); }
    });

    // Checkout
    btnCheckout.addEventListener('click', openCheckout);
    checkoutClose.addEventListener('click', closeCheckout);
    $('btn-to-step2').addEventListener('click', goToStep2);
    $('btn-to-step3').addEventListener('click', goToStep3);
    $('btn-back-1').addEventListener('click', () => goToStep(1));
    $('btn-back-2').addEventListener('click', () => goToStep(2));
    $('btn-confirm').addEventListener('click', confirmOrder);
    $('btn-back-carte').addEventListener('click', () => {
        closeCheckout();
        document.getElementById('carte').scrollIntoView({behavior:'smooth'});
    });

    // Delivery mode toggle
    $('c-mode').addEventListener('change', function() {
        const fields = $('delivery-fields');
        const heureGroup = $('c-heure-group');
        if (this.value === 'retrait') {
            fields.style.display = 'none';
            heureGroup.style.display = 'none';
        } else {
            fields.style.display = '';
            heureGroup.style.display = '';
        }
    });

    // Devis form
    $('devis-form-el').addEventListener('submit', handleDevis);
    $('devis-personnes').addEventListener('input', function() {
        $('devis-personnes-val').textContent = this.value;
    });
}

// ═══════════════════════════════════════
// CHECKOUT LOGIC — 4 Steps
// ═══════════════════════════════════════

function openCheckout() {
    closeCart();
    renderCheckoutStep1();
    goToStep(1);
    checkoutOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeCheckout() {
    checkoutOverlay.classList.remove('active');
    document.body.style.overflow = '';
}

function goToStep(n) {
    document.querySelectorAll('.checkout-page').forEach(p => p.classList.remove('active'));
    $('checkout-page-' + n).classList.add('active');
    // Update step indicators
    document.querySelectorAll('.checkout-step').forEach(s => {
        const sn = parseInt(s.dataset.step);
        s.classList.remove('active','done');
        if (sn === n) s.classList.add('active');
        else if (sn < n) s.classList.add('done');
    });
    $('checkout-steps').style.display = n === 4 ? 'none' : '';
}

function renderCheckoutStep1() {
    const container = $('checkout-items');
    container.innerHTML = cart.map(item => `
        <div class="checkout-item">
            <div class="checkout-item-img"><img src="${item.img}" alt="${item.name}" loading="lazy"></div>
            <div class="checkout-item-info">
                <div class="checkout-item-name">${item.name}</div>
                <div class="checkout-item-meta">${fmtPrice(item.price)} × ${item.qty}</div>
            </div>
            <div class="checkout-item-qty">
                <button class="qty-btn" onclick="SLP.checkoutQty(${item.id},-1)" aria-label="Diminuer">−</button>
                <span>${item.qty}</span>
                <button class="qty-btn" onclick="SLP.checkoutQty(${item.id},1)" aria-label="Augmenter">+</button>
            </div>
            <span class="checkout-item-sub">${fmtPrice(item.price * item.qty)}</span>
        </div>
    `).join('');
    $('checkout-total-1').innerHTML = `Total : <strong>${fmtPrice(getTotal())}</strong>`;
    $('checkout-min-warn').hidden = getTotal() >= 10;
    lucide.createIcons();
}

window.SLP.checkoutQty = function(id, delta) {
    updateQty(id, delta);
    if (cart.length === 0) { closeCheckout(); return; }
    renderCheckoutStep1();
};

function goToStep2() {
    if (getTotal() < 10) {
        $('checkout-min-warn').hidden = false;
        return;
    }
    goToStep(2);
}

function goToStep3() {
    if (!validateStep2()) return;
    renderStep3();
    goToStep(3);
}

function validateStep2() {
    let valid = true;
    const mode = $('c-mode').value;
    const fields = [
        { id:'c-nom', err:'err-nom', msg:'Nom requis' },
        { id:'c-prenom', err:'err-prenom', msg:'Prénom requis' },
        { id:'c-email', err:'err-email', msg:'Email requis', type:'email' },
        { id:'c-tel', err:'err-tel', msg:'Téléphone requis' },
        { id:'c-date', err:'err-date', msg:'Date requise' },
    ];
    if (mode === 'livraison') {
        fields.push(
            { id:'c-adresse', err:'err-adresse', msg:'Adresse requise' },
            { id:'c-cp', err:'err-cp', msg:'Code postal requis' },
            { id:'c-ville', err:'err-ville', msg:'Ville requise' },
            { id:'c-heure', err:'err-heure', msg:'Créneau requis' },
        );
    }
    fields.forEach(f => {
        const el = $(f.id);
        const errEl = $(f.err);
        if (!el || !errEl) return;
        el.classList.remove('error');
        errEl.textContent = '';
        if (!el.value.trim()) {
            el.classList.add('error');
            errEl.textContent = f.msg;
            valid = false;
        } else if (f.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(el.value)) {
            el.classList.add('error');
            errEl.textContent = 'Email invalide';
            valid = false;
        }
    });
    return valid;
}

function renderStep3() {
    const mode = $('c-mode').value;
    let html = `
        <p><strong>Client :</strong> ${$('c-prenom').value} ${$('c-nom').value}</p>
        <p><strong>Email :</strong> ${$('c-email').value}</p>
        <p><strong>Téléphone :</strong> ${$('c-tel').value}</p>
        <p><strong>Mode :</strong> ${mode === 'livraison' ? 'Livraison' : 'Retrait sur place'}</p>
    `;
    if (mode === 'livraison') {
        html += `<p><strong>Adresse :</strong> ${$('c-adresse').value}, ${$('c-cp').value} ${$('c-ville').value}</p>`;
        html += `<p><strong>Créneau :</strong> ${$('c-heure').value}</p>`;
    }
    html += `<p><strong>Date :</strong> ${formatDateFR($('c-date').value)}</p>`;
    if ($('c-instructions').value.trim()) {
        html += `<p><strong>Instructions :</strong> ${$('c-instructions').value}</p>`;
    }
    html += '<hr>';
    cart.forEach(item => {
        html += `<p>${item.qty}× ${item.name} — ${fmtPrice(item.price * item.qty)}</p>`;
    });
    html += `<hr><p style="font-size:1.1rem"><strong>Total : ${fmtPrice(getTotal())}</strong></p>`;
    $('confirm-recap').innerHTML = html;
}

function confirmOrder() {
    const cgv = $('c-cgv');
    const errCgv = $('err-cgv');
    cgv.classList.remove('error');
    errCgv.textContent = '';
    if (!cgv.checked) {
        errCgv.textContent = 'Vous devez accepter les CGV';
        return;
    }
    const mode = $('c-mode').value;
    const order = {
        id: '#SLP' + Date.now(),
        timestamp: new Date().toISOString(),
        client: {
            nom: $('c-nom').value,
            prenom: $('c-prenom').value,
            email: $('c-email').value,
            telephone: $('c-tel').value,
        },
        items: cart.map(c => ({ nom: c.name, prix: c.price, quantite: c.qty })),
        total: getTotal(),
        mode: mode,
        adresse: mode === 'livraison' ? `${$('c-adresse').value}, ${$('c-cp').value} ${$('c-ville').value}` : null,
        heure: mode === 'livraison' ? $('c-heure').value : null,
        instructions: $('c-instructions').value || '',
    };
    // Save to localStorage
    try {
        const orders = JSON.parse(localStorage.getItem('slp_orders') || '[]');
        orders.push(order);
        localStorage.setItem('slp_orders', JSON.stringify(orders));
    } catch(e) {}
    console.log('Commande confirmée:', order);
    // Show success
    $('success-order-id').textContent = order.id;
    goToStep(4);
    // Clear cart
    cart = [];
    saveCart();
    updateCartUI();
}

function formatDateFR(str) {
    const d = new Date(str);
    return d.toLocaleDateString('fr-FR', { weekday:'long', day:'numeric', month:'long', year:'numeric' });
}

// ── Devis form ──
function handleDevis(e) {
    e.preventDefault();
    const form = $('devis-form-el');
    const success = $('devis-success');
    // Log devis data
    console.log('Demande de devis:', {
        nom: $('devis-nom').value,
        email: $('devis-email').value,
        tel: $('devis-tel').value,
        event: $('devis-event').value,
        personnes: $('devis-personnes').value,
        date: $('devis-date').value,
        budget: $('devis-budget').value,
        message: $('devis-message').value,
    });
    form.style.display = 'none';
    success.hidden = false;
    showToast('Demande de devis envoyée !');
}

// ── Start ──
document.addEventListener('DOMContentLoaded', init);

})();
