/* ========================================
   Pizza Napoli Carpentras - Main JS
   ======================================== */

document.addEventListener('DOMContentLoaded', function () {

    // --- Navbar scroll effect ---
    const navbar = document.getElementById('navbar');
    window.addEventListener('scroll', function () {
        navbar.classList.toggle('scrolled', window.scrollY > 50);
    });

    // --- Mobile menu toggle ---
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');

    navToggle.addEventListener('click', function () {
        navMenu.classList.toggle('active');
        navToggle.classList.toggle('active');
    });

    // Close menu on link click
    document.querySelectorAll('.nav-link').forEach(function (link) {
        link.addEventListener('click', function () {
            navMenu.classList.remove('active');
            navToggle.classList.remove('active');
        });
    });

    // --- Menu tabs ---
    const tabs = document.querySelectorAll('.menu-tab');
    const contents = document.querySelectorAll('.menu-content');

    tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            var target = this.getAttribute('data-tab');

            tabs.forEach(function (t) { t.classList.remove('active'); });
            contents.forEach(function (c) { c.classList.remove('active'); });

            this.classList.add('active');
            document.getElementById('tab-' + target).classList.add('active');
        });
    });

    // --- Smooth scroll for anchor links ---
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            var href = this.getAttribute('href');
            if (href === '#') return;
            e.preventDefault();
            var target = document.querySelector(href);
            if (target) {
                var offset = navbar.offsetHeight + 10;
                var top = target.getBoundingClientRect().top + window.pageYOffset - offset;
                window.scrollTo({ top: top, behavior: 'smooth' });
            }
        });
    });

    // --- Scroll fade-in animations ---
    var fadeEls = document.querySelectorAll(
        '.feature-card, .menu-item, .specialite-card, .avis-card, .gallery-item, .about-content, .about-image, .contact-item, .contact-form-wrapper'
    );

    fadeEls.forEach(function (el) {
        el.classList.add('fade-in');
    });

    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    fadeEls.forEach(function (el) {
        observer.observe(el);
    });

    // --- Contact form ---
    var form = document.getElementById('contact-form');
    if (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var btn = form.querySelector('button[type="submit"]');
            var originalText = btn.textContent;
            btn.textContent = 'Message envoye !';
            btn.style.background = '#27ae60';
            btn.disabled = true;

            setTimeout(function () {
                btn.textContent = originalText;
                btn.style.background = '';
                btn.disabled = false;
                form.reset();
            }, 3000);
        });
    }

    // --- Avis Carousel ---
    var carousel = document.getElementById('avis-carousel');
    if (carousel) {
        var track = carousel.querySelector('.avis-carousel-track');
        var cards = track.querySelectorAll('.avis-card');
        var prevBtn = carousel.querySelector('.carousel-prev');
        var nextBtn = carousel.querySelector('.carousel-next');
        var dotsContainer = document.getElementById('carousel-dots');
        var currentIndex = 0;

        // Determine cards per view based on screen width
        function getCardsPerView() {
            if (window.innerWidth <= 768) return 1;
            if (window.innerWidth <= 1024) return 2;
            return 3;
        }

        var cardsPerView = getCardsPerView();
        var totalPages = Math.ceil(cards.length / cardsPerView);

        // Create dots
        function createDots() {
            dotsContainer.innerHTML = '';
            totalPages = Math.ceil(cards.length / cardsPerView);
            for (var i = 0; i < totalPages; i++) {
                var dot = document.createElement('span');
                dot.classList.add('carousel-dot');
                if (i === currentIndex) dot.classList.add('active');
                dot.setAttribute('data-index', i);
                dot.addEventListener('click', function () {
                    goToSlide(parseInt(this.getAttribute('data-index')));
                });
                dotsContainer.appendChild(dot);
            }
        }

        function goToSlide(index) {
            if (index < 0) index = totalPages - 1;
            if (index >= totalPages) index = 0;
            currentIndex = index;
            var cardWidth = cards[0].offsetWidth + 20; // card width + gap
            track.style.transform = 'translateX(-' + (currentIndex * cardsPerView * cardWidth) + 'px)';
            var dots = dotsContainer.querySelectorAll('.carousel-dot');
            dots.forEach(function (d) { d.classList.remove('active'); });
            if (dots[currentIndex]) dots[currentIndex].classList.add('active');
        }

        prevBtn.addEventListener('click', function () { goToSlide(currentIndex - 1); });
        nextBtn.addEventListener('click', function () { goToSlide(currentIndex + 1); });

        createDots();

        // Auto-play
        var autoPlay = setInterval(function () { goToSlide(currentIndex + 1); }, 5000);
        carousel.addEventListener('mouseenter', function () { clearInterval(autoPlay); });
        carousel.addEventListener('mouseleave', function () {
            autoPlay = setInterval(function () { goToSlide(currentIndex + 1); }, 5000);
        });

        // Responsive
        window.addEventListener('resize', function () {
            cardsPerView = getCardsPerView();
            currentIndex = 0;
            createDots();
            goToSlide(0);
        });
    }

    // --- Active nav link on scroll ---
    var sections = document.querySelectorAll('section[id]');
    window.addEventListener('scroll', function () {
        var scrollY = window.pageYOffset + 100;
        sections.forEach(function (section) {
            var top = section.offsetTop;
            var height = section.offsetHeight;
            var id = section.getAttribute('id');
            var link = document.querySelector('.nav-link[href="#' + id + '"]');
            if (link) {
                if (scrollY >= top && scrollY < top + height) {
                    document.querySelectorAll('.nav-link').forEach(function (l) {
                        l.classList.remove('active');
                    });
                    link.classList.add('active');
                }
            }
        });
    });
});
