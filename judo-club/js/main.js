/* =========================================================
   Judo Club Cadeneaux OJM — scripts du site
   Vanilla JS, sans dependance.
   ========================================================= */
(function () {
    'use strict';

    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var $ = function (sel, root) { return (root || document).querySelector(sel); };
    var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };

    /* ---------- 1. Header : etat au scroll ---------- */
    var header = $('#header');
    var toTop = $('#to-top');

    function onScroll() {
        var y = window.pageYOffset || document.documentElement.scrollTop;
        if (header) header.classList.toggle('is-scrolled', y > 40);
        if (toTop) toTop.classList.toggle('is-visible', y > 600);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    if (toTop) {
        toTop.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
        });
    }

    /* ---------- 2. Menu mobile ---------- */
    var burger = $('#burger');
    var nav = $('#nav');

    function closeNav() {
        if (!nav || !burger) return;
        nav.classList.remove('is-open');
        burger.setAttribute('aria-expanded', 'false');
        burger.setAttribute('aria-label', 'Ouvrir le menu');
    }

    if (burger && nav) {
        burger.addEventListener('click', function () {
            var open = nav.classList.toggle('is-open');
            burger.setAttribute('aria-expanded', String(open));
            burger.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
        });
        $$('a', nav).forEach(function (link) { link.addEventListener('click', closeNav); });
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeNav(); });
        document.addEventListener('click', function (e) {
            if (!nav.contains(e.target) && !burger.contains(e.target)) closeNav();
        });
    }

    /* ---------- 3. Lien de navigation actif (scrollspy) ---------- */
    var navLinks = $$('.nav-link');
    var sections = navLinks
        .map(function (link) { return document.getElementById(link.getAttribute('href').slice(1)); })
        .filter(Boolean);

    if ('IntersectionObserver' in window && sections.length) {
        var spy = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                navLinks.forEach(function (link) {
                    link.classList.toggle('is-active', link.getAttribute('href') === '#' + entry.target.id);
                });
            });
        }, { rootMargin: '-45% 0px -50% 0px', threshold: 0 });
        sections.forEach(function (section) { spy.observe(section); });
    }

    /* ---------- 4. Apparition au defilement ---------- */
    var revealables = $$('.reveal');
    if (reduceMotion || !('IntersectionObserver' in window)) {
        revealables.forEach(function (el) { el.classList.add('is-visible'); });
    } else {
        var revealer = new IntersectionObserver(function (entries, obs) {
            entries.forEach(function (entry, i) {
                if (!entry.isIntersecting) return;
                setTimeout(function () { entry.target.classList.add('is-visible'); }, Math.min(i * 70, 350));
                obs.unobserve(entry.target);
            });
        }, { rootMargin: '0px 0px -60px 0px', threshold: 0.08 });
        revealables.forEach(function (el) { revealer.observe(el); });
    }

    /* ---------- 5. Filtres du planning ---------- */
    var filters = $$('.filter');
    var slots = $$('.slot');
    var days = $$('[data-day]');

    function applyFilter(value) {
        slots.forEach(function (slot) {
            slot.hidden = !(value === 'all' || slot.dataset.filter === value);
        });
        days.forEach(function (day) {
            var visible = $$('.slot', day).some(function (slot) { return !slot.hidden; });
            day.classList.toggle('day--empty', !visible);
        });
    }

    filters.forEach(function (btn) {
        btn.addEventListener('click', function () {
            filters.forEach(function (other) {
                var active = other === btn;
                other.classList.toggle('is-active', active);
                other.setAttribute('aria-pressed', String(active));
            });
            applyFilter(btn.dataset.filter);
        });
    });

    /* ---------- 6. Galerie / lightbox ---------- */
    var lightbox = $('#lightbox');
    var lightboxImg = $('#lightbox-img');
    var lightboxCaption = $('#lightbox-caption');
    var lightboxClose = $('#lightbox-close');
    var lastFocused = null;

    function openLightbox(figure) {
        if (!lightbox) return;
        var img = $('img', figure);
        var caption = $('figcaption', figure);
        lastFocused = document.activeElement;
        lightboxImg.src = img.getAttribute('src');
        lightboxImg.alt = img.getAttribute('alt') || '';
        lightboxCaption.textContent = caption ? caption.textContent : '';
        lightbox.hidden = false;
        document.body.style.overflow = 'hidden';
        lightboxClose.focus();
    }

    function closeLightbox() {
        if (!lightbox || lightbox.hidden) return;
        lightbox.hidden = true;
        lightboxImg.src = '';
        document.body.style.overflow = '';
        if (lastFocused) lastFocused.focus();
    }

    $$('.gallery__item').forEach(function (figure) {
        figure.addEventListener('click', function () { openLightbox(figure); });
        figure.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openLightbox(figure); }
        });
    });

    if (lightbox) {
        lightboxClose.addEventListener('click', closeLightbox);
        lightbox.addEventListener('click', function (e) { if (e.target === lightbox) closeLightbox(); });
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeLightbox(); });
    }

    /* ---------- 7. Formulaire de contact ---------- */
    var form = $('#contact-form');
    var status = $('#form-status');

    function showError(field, message) {
        var msg = document.querySelector('[data-error-for="' + field.id + '"]');
        field.setAttribute('aria-invalid', 'true');
        if (msg) { msg.textContent = message; msg.hidden = false; }
    }

    function clearError(field) {
        var msg = document.querySelector('[data-error-for="' + field.id + '"]');
        field.removeAttribute('aria-invalid');
        if (msg) { msg.hidden = true; msg.textContent = ''; }
    }

    function validate(field) {
        clearError(field);
        var value = (field.value || '').trim();

        if (field.type === 'checkbox') {
            if (field.required && !field.checked) { showError(field, 'Merci de cocher cette case pour continuer.'); return false; }
            return true;
        }
        if (field.required && !value) { showError(field, 'Ce champ est obligatoire.'); return false; }
        if (field.type === 'email' && value && !/^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i.test(value)) {
            showError(field, 'Merci de saisir une adresse e-mail valide.');
            return false;
        }
        if (field.id === 'message' && value.length < 10) {
            showError(field, 'Votre message est un peu court (10 caracteres minimum).');
            return false;
        }
        return true;
    }

    if (form) {
        var fields = $$('input, select, textarea', form).filter(function (f) { return f.type !== 'submit'; });

        fields.forEach(function (field) {
            field.addEventListener('blur', function () { validate(field); });
            field.addEventListener('input', function () { if (field.getAttribute('aria-invalid')) validate(field); });
        });

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var valid = true;
            fields.forEach(function (field) { if (!validate(field)) valid = false; });

            if (!valid) {
                var firstInvalid = $('[aria-invalid="true"]', form);
                if (firstInvalid) firstInvalid.focus();
                return;
            }

            var data = {
                prenom: form.prenom.value.trim(),
                nom: form.nom.value.trim(),
                email: form.email.value.trim(),
                tel: form.tel.value.trim(),
                groupe: form.groupe.value,
                message: form.message.value.trim()
            };

            var endpoint = form.dataset.endpoint;

            if (endpoint) {
                // Envoi via le service configure dans data-endpoint (Formspree, API du club, ...)
                fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                    body: JSON.stringify(data)
                }).then(function (res) {
                    if (!res.ok) throw new Error('HTTP ' + res.status);
                    status.className = 'form-status form-status--ok';
                    status.textContent = 'Merci ' + data.prenom + ' ! Votre demande est bien partie, le club vous repond sous 48 h.';
                    status.hidden = false;
                    form.reset();
                }).catch(function () {
                    status.className = 'form-status form-status--info';
                    status.textContent = "L'envoi automatique a echoue. Ecrivez-nous directement a contact@judocadeneaux-ojm.fr.";
                    status.hidden = false;
                });
                return;
            }

            // Sans backend : ouverture du client mail avec le message pre-rempli.
            var subject = 'Demande de cours d\'essai — ' + data.groupe;
            var body = [
                'Prenom : ' + data.prenom,
                'Nom : ' + data.nom,
                'E-mail : ' + data.email,
                'Telephone : ' + (data.tel || 'non renseigne'),
                'Cours concerne : ' + data.groupe,
                '',
                data.message
            ].join('\n');

            window.location.href = 'mailto:contact@judocadeneaux-ojm.fr'
                + '?subject=' + encodeURIComponent(subject)
                + '&body=' + encodeURIComponent(body);

            status.className = 'form-status form-status--info';
            status.textContent = 'Votre messagerie vient de s\'ouvrir avec le message pre-rempli : il ne reste qu\'a l\'envoyer.';
            status.hidden = false;
        });
    }

    /* ---------- 8. Annee courante ---------- */
    var year = $('#year');
    if (year) year.textContent = String(new Date().getFullYear());
})();
