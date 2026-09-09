/* =========================================================
   Judo Club Cadeneaux OJM — scripts du site
   Vanilla JS, sans dependance. Le planning HTML est la seule
   source de verite : le script lit les creneaux (data-day,
   data-start, data-end, data-filter) pour tout le reste.
   ========================================================= */
(function () {
    'use strict';

    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var $ = function (sel, root) { return (root || document).querySelector(sel); };
    var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
    var DAYS = ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'];
    var CLUB_EMAIL = 'contact@judocadeneaux-ojm.fr';

    /* ---------- 1. Header, bouton retour en haut, barre mobile ---------- */
    var header = $('#header');
    var toTop = $('#to-top');
    var stickyCta = $('#sticky-cta');
    var hero = $('#accueil');

    function onScroll() {
        var y = window.pageYOffset || document.documentElement.scrollTop;
        if (header) header.classList.toggle('is-scrolled', y > 40);
        if (toTop) toTop.classList.toggle('is-visible', y > 600);
        if (stickyCta && hero) {
            var past = y > hero.offsetTop + hero.offsetHeight - 80;
            var nearContact = $('#contact') && y > $('#contact').offsetTop - 200;
            var show = past && !nearContact;
            stickyCta.classList.toggle('is-visible', show);
            stickyCta.setAttribute('aria-hidden', String(!show));
        }
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

    /* ---------- 3. Lien de navigation actif ---------- */
    var navLinks = $$('.nav-link');
    var sections = navLinks
        .map(function (link) { var h = link.getAttribute('href'); return h.charAt(0) === '#' ? document.getElementById(h.slice(1)) : null; })
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

    /* ---------- 5. Lecture du planning ---------- */
    function toMinutes(hhmm) {
        var p = hhmm.split(':');
        return parseInt(p[0], 10) * 60 + parseInt(p[1], 10);
    }
    function fmt(hhmm) { return hhmm.replace(':', 'h'); }

    var slots = $$('.slot').map(function (el) {
        var day = el.closest('[data-day]');
        return {
            el: el,
            day: day ? parseInt(day.dataset.day, 10) : null,
            dayEl: day,
            start: el.dataset.start || '',
            end: el.dataset.end || '',
            filter: el.dataset.filter || '',
            name: ($('.slot__name', el) || {}).textContent || '',
            ages: (($('.slot__age', el) || {}).textContent || '').split('·')[0].trim()
        };
    });

    /* Jour courant + cours en cours */
    var now = new Date();
    var today = now.getDay();
    var nowMin = now.getHours() * 60 + now.getMinutes();

    $$('[data-day]').forEach(function (dayEl) {
        if (parseInt(dayEl.dataset.day, 10) === today) {
            dayEl.classList.add('is-today');
            var badge = $('.day__today', dayEl);
            if (badge) badge.hidden = false;
        }
    });
    slots.forEach(function (s) {
        if (s.day === today && s.start && s.end && nowMin >= toMinutes(s.start) && nowMin < toMinutes(s.end)) {
            s.el.classList.add('is-now');
        }
    });

    /* Prochain cours (carte du hero) */
    var nextBox = $('#next-class');
    if (nextBox && slots.length) {
        var ordered = slots.filter(function (s) { return s.day !== null && s.start; }).map(function (s) {
            var delta = (s.day - today + 7) % 7;
            var startMin = toMinutes(s.start), endMin = toMinutes(s.end || s.start);
            var live = delta === 0 && nowMin >= startMin && nowMin < endMin;
            if (delta === 0 && nowMin >= endMin) delta = 7;
            return { s: s, key: delta * 1440 + startMin, live: live };
        }).sort(function (a, b) { return a.key - b.key; });

        var next = ordered[0];
        if (next) {
            var whenEl = $('[data-next-when]', nextBox);
            var whatEl = $('[data-next-what]', nextBox);
            var delta = (next.s.day - today + 7) % 7;
            var dayLabel = next.live ? 'En ce moment' : (delta === 0 ? "Aujourd'hui" : (delta === 1 ? 'Demain' : DAYS[next.s.day]));
            whenEl.textContent = dayLabel + ' · ' + fmt(next.s.start);
            whatEl.textContent = next.s.name + ' · ' + next.s.ages;
            nextBox.classList.toggle('next-class--live', next.live);
            if (next.live) $('.next-class__label', nextBox).textContent = 'Cours en cours';
        }
    }

    /* ---------- 6. Filtres du planning ---------- */
    var filters = $$('.filter');
    var days = $$('[data-day]');

    function applyFilter(value) {
        slots.forEach(function (s) { s.el.hidden = !(value === 'all' || s.filter === value); });
        days.forEach(function (day) {
            var visible = $$('.slot', day).some(function (el) { return !el.hidden; });
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

    var printBtn = $('#print-planning');
    if (printBtn) printBtn.addEventListener('click', function () { window.print(); });

    /* ---------- 7. Selecteur "Quel cours pour mon enfant ?" ---------- */
    var finder = $('#finder');
    var finderResult = $('#finder-result');

    // Categories d'age de France Judo : l'age est calcule sur l'annee civile de la saison.
    var CATEGORIES = [
        { max: 3, name: null },
        { max: 5, name: 'Éveil judo', group: 'eveil', label: 'Éveil judo (4-5 ans)' },
        { max: 7, name: 'Mini-poussin', group: 'jeunes', label: 'Judo éducatif jeunes' },
        { max: 9, name: 'Poussin', group: 'jeunes', label: 'Judo éducatif jeunes' },
        { max: 11, name: 'Benjamin', group: 'jeunes', label: 'Judo éducatif jeunes' },
        { max: 13, name: 'Minime', group: 'jeunes', label: 'Judo éducatif jeunes' },
        { max: 16, name: 'Cadet', group: 'competition', label: 'Judo compétition & adultes' },
        { max: 19, name: 'Junior', group: 'competition', label: 'Judo compétition & adultes' },
        { max: 999, name: 'Senior', group: 'competition', label: 'Judo compétition & adultes' }
    ];

    function seasonYear() {
        var d = new Date();
        // La saison sportive court de septembre a juin : a partir de juillet on raisonne sur la saison suivante.
        return d.getMonth() >= 6 ? d.getFullYear() + 1 : d.getFullYear();
    }

    function escapeHtml(str) {
        return String(str).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    if (finder && finderResult) {
        var yearInput = $('#birth-year', finder);
        yearInput.max = String(new Date().getFullYear());

        finder.addEventListener('submit', function (e) {
            e.preventDefault();
            var year = parseInt(yearInput.value, 10);
            var thisYear = new Date().getFullYear();

            if (!year || year < 1930 || year > thisYear) {
                finderResult.innerHTML = '<p class="cat">Année invalide</p><h3>Indiquez une année de naissance à quatre chiffres</h3>';
                finderResult.hidden = false;
                return;
            }

            var age = seasonYear() - year;
            var cat = CATEGORIES.filter(function (c) { return age <= c.max; })[0];

            if (!cat.name) {
                finderResult.innerHTML =
                    '<p class="cat">Encore un peu de patience</p>' +
                    '<h3>L\'éveil judo commence à 4 ans</h3>' +
                    '<p>Le judoka aura ' + age + ' an' + (age > 1 ? 's' : '') + ' sur la saison. Revenez nous voir dès ses 4 ans, la place l\'attend.</p>';
                finderResult.hidden = false;
                return;
            }

            var lines = slots.filter(function (s) { return s.filter === cat.group; }).map(function (s) {
                return '<li>' + DAYS[s.day] + ' ' + fmt(s.start) + ' → ' + fmt(s.end) + '</li>';
            });

            finderResult.innerHTML =
                '<p class="cat">Catégorie ' + escapeHtml(cat.name) + ' · ' + age + ' ans sur la saison</p>' +
                '<h3>' + escapeHtml(cat.label) + '</h3>' +
                '<p>Ses créneaux au dojo des Bouroumettes&nbsp;:</p>' +
                '<ul>' + lines.join('') + '</ul>' +
                '<a class="btn btn--primary btn--sm" href="#inscription">Réserver le cours d\'essai</a>';
            finderResult.hidden = false;
        });
    }

    /* ---------- 8. Galerie / lightbox ---------- */
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

    /* ---------- 9. Formulaire de contact ---------- */
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
            showError(field, 'Votre message est un peu court (10 caractères minimum).');
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
                    status.textContent = 'Merci ' + data.prenom + ' ! Votre demande est bien partie, le club vous répond sous 48 h.';
                    status.hidden = false;
                    form.reset();
                }).catch(function () {
                    status.className = 'form-status form-status--info';
                    status.textContent = "L'envoi automatique a échoué. Écrivez-nous directement à " + CLUB_EMAIL + '.';
                    status.hidden = false;
                });
                return;
            }

            // Sans backend : ouverture du client mail avec le message pre-rempli.
            var subject = 'Demande de cours d\'essai — ' + data.groupe;
            var body = [
                'Prénom : ' + data.prenom,
                'Nom : ' + data.nom,
                'E-mail : ' + data.email,
                'Téléphone : ' + (data.tel || 'non renseigné'),
                'Cours concerné : ' + data.groupe,
                '',
                data.message
            ].join('\n');

            window.location.href = 'mailto:' + CLUB_EMAIL
                + '?subject=' + encodeURIComponent(subject)
                + '&body=' + encodeURIComponent(body);

            status.className = 'form-status form-status--info';
            status.textContent = 'Votre messagerie vient de s\'ouvrir avec le message pré-rempli : il ne reste qu\'à l\'envoyer.';
            status.hidden = false;
        });
    }

    /* ---------- 10. Annee courante ---------- */
    var year = $('#year');
    if (year) year.textContent = String(new Date().getFullYear());
})();
