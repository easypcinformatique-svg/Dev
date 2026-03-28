/* ============================================
   ELCR — main.js
   JavaScript vanilla — zero dependance
   ============================================ */

document.addEventListener('DOMContentLoaded', function () {

  /* 1. HEADER SCROLL — class .scrolled quand scrollY > 50 + floating CTA visibility */
  const header = document.querySelector('.header');
  const floatingCta = document.getElementById('floating-cta');
  var hero = document.querySelector('.hero');
  if (header) {
    window.addEventListener('scroll', function () {
      var scrollY = window.scrollY || window.pageYOffset;
      if (scrollY > 50) {
        header.classList.add('scrolled');
      } else {
        header.classList.remove('scrolled');
      }
      // Hide floating CTA when hero is visible
      if (floatingCta && hero) {
        if (scrollY < hero.offsetHeight - 100) {
          floatingCta.classList.add('hidden');
        } else {
          floatingCta.classList.remove('hidden');
        }
      }
    }, { passive: true });

    // Initial state: hide if hero visible
    if (floatingCta && hero) {
      floatingCta.classList.add('hidden');
    }
  }

  /* 2. HAMBURGER — toggle overlay mobile */
  const hamburger = document.querySelector('.hamburger');
  const mobileNav = document.querySelector('.mobile-nav');
  if (hamburger && mobileNav) {
    hamburger.addEventListener('click', function () {
      hamburger.classList.toggle('open');
      mobileNav.classList.toggle('open');
      document.body.style.overflow = mobileNav.classList.contains('open') ? 'hidden' : '';
    });

    // Fermer au clic sur un lien
    mobileNav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        hamburger.classList.remove('open');
        mobileNav.classList.remove('open');
        document.body.style.overflow = '';
      });
    });
  }

  /* 3. SMOOTH SCROLL — gestion du decalage header fixe */
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      const target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        const headerHeight = header ? header.offsetHeight : 0;
        const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - headerHeight;
        window.scrollTo({ top: targetPosition, behavior: 'smooth' });
      }
    });
  });

  /* 4. LIGHTBOX vanilla */
  const lightbox = document.querySelector('.lightbox');
  const lightboxImg = document.querySelector('.lightbox__img');
  const lightboxClose = document.querySelector('.lightbox__close');
  const lightboxPrev = document.querySelector('.lightbox__nav--prev');
  const lightboxNext = document.querySelector('.lightbox__nav--next');
  let lightboxImages = [];
  let lightboxIndex = 0;

  function openLightbox(images, index) {
    lightboxImages = images;
    lightboxIndex = index;
    if (lightbox && lightboxImg) {
      lightboxImg.src = lightboxImages[lightboxIndex];
      lightboxImg.alt = 'Realisation ELCR - Photo ' + (lightboxIndex + 1);
      lightbox.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  }

  function closeLightbox() {
    if (lightbox) {
      lightbox.classList.remove('active');
      document.body.style.overflow = '';
    }
  }

  function navigateLightbox(direction) {
    if (lightboxImages.length === 0) return;
    lightboxIndex = (lightboxIndex + direction + lightboxImages.length) % lightboxImages.length;
    if (lightboxImg) {
      lightboxImg.src = lightboxImages[lightboxIndex];
      lightboxImg.alt = 'Realisation ELCR - Photo ' + (lightboxIndex + 1);
    }
  }

  // Bind lightbox events
  if (lightboxClose) lightboxClose.addEventListener('click', closeLightbox);
  if (lightboxPrev) lightboxPrev.addEventListener('click', function () { navigateLightbox(-1); });
  if (lightboxNext) lightboxNext.addEventListener('click', function () { navigateLightbox(1); });

  if (lightbox) {
    lightbox.addEventListener('click', function (e) {
      if (e.target === lightbox) closeLightbox();
    });
  }

  // Keyboard navigation
  document.addEventListener('keydown', function (e) {
    if (!lightbox || !lightbox.classList.contains('active')) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowLeft') navigateLightbox(-1);
    if (e.key === 'ArrowRight') navigateLightbox(1);
  });

  // Bind photo items to lightbox
  const photoItems = document.querySelectorAll('.photo-item');
  if (photoItems.length > 0) {
    photoItems.forEach(function (item, index) {
      item.addEventListener('click', function () {
        const visibleItems = Array.from(document.querySelectorAll('.photo-item:not(.fade-out)'));
        const images = visibleItems.map(function (el) {
          return el.querySelector('img').src;
        });
        const visibleIndex = visibleItems.indexOf(item);
        openLightbox(images, visibleIndex >= 0 ? visibleIndex : 0);
      });
    });
  }

  /* 5. FILTRE GALERIE */
  const filterBtns = document.querySelectorAll('.filter-btn');
  if (filterBtns.length > 0) {
    filterBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        // Active state
        filterBtns.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');

        const category = btn.getAttribute('data-filter');

        photoItems.forEach(function (item) {
          const itemCategory = item.getAttribute('data-category');
          if (category === 'all' || itemCategory === category) {
            item.classList.remove('fade-out');
            item.classList.add('fade-in');
            item.style.display = '';
          } else {
            item.classList.remove('fade-in');
            item.classList.add('fade-out');
            // Delay display none for animation
            setTimeout(function () {
              if (item.classList.contains('fade-out')) {
                item.style.display = 'none';
              }
            }, 300);
          }
        });
      });
    });
  }

  /* 6. FORMULAIRE DEVIS — validation + envoi Formspree */
  const form = document.getElementById('form-devis');
  if (form) {
    const phoneRegex = /^(?:(?:\+|00)33|0)\s*[1-9](?:[\s.\-]*\d{2}){4}$/;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const successMsg = document.querySelector('.form-success');
    const errorMsg = document.querySelector('.form-error');

    // Real-time validation
    function validateField(field) {
      let valid = true;
      const value = field.value.trim();

      if (field.required && !value) {
        valid = false;
      } else if (field.type === 'email' && value && !emailRegex.test(value)) {
        valid = false;
      } else if (field.type === 'tel' && value && !phoneRegex.test(value)) {
        valid = false;
      }

      if (!valid) {
        field.classList.add('error');
      } else {
        field.classList.remove('error');
      }
      return valid;
    }

    // Add real-time validation listeners
    form.querySelectorAll('input, select, textarea').forEach(function (field) {
      field.addEventListener('blur', function () { validateField(field); });
      field.addEventListener('input', function () {
        if (field.classList.contains('error')) validateField(field);
      });
    });

    // Check at least one checkbox selected
    function validateCheckboxes() {
      const checkboxes = form.querySelectorAll('input[name="travaux"]:checked');
      const group = form.querySelector('.checkbox-group');
      if (checkboxes.length === 0) {
        if (group) group.classList.add('error');
        return false;
      }
      if (group) group.classList.remove('error');
      return true;
    }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      let isValid = true;

      // Validate all required fields
      form.querySelectorAll('[required]').forEach(function (field) {
        if (!validateField(field)) isValid = false;
      });

      if (!validateCheckboxes()) isValid = false;

      if (!isValid) return;

      // Submit via fetch
      const formData = new FormData(form);

      fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: { 'Accept': 'application/json' }
      })
        .then(function (response) {
          if (response.ok) {
            form.reset();
            if (successMsg) successMsg.style.display = 'block';
            if (errorMsg) errorMsg.style.display = 'none';
            // Update textarea counter
            var counter = document.getElementById('textarea-counter');
            if (counter) counter.textContent = '0/300 caractères';
          } else {
            throw new Error('Erreur serveur');
          }
        })
        .catch(function () {
          if (errorMsg) errorMsg.style.display = 'block';
          if (successMsg) successMsg.style.display = 'none';
        });
    });
  }

  /* 7. COMPTEUR TEXTAREA */
  var textarea = document.getElementById('description-projet');
  var counter = document.getElementById('textarea-counter');
  if (textarea && counter) {
    textarea.addEventListener('input', function () {
      var len = textarea.value.length;
      counter.textContent = len + '/300 caractères';
    });
  }

  /* 8. INTERSECTION OBSERVER — animations scroll */
  var animElements = document.querySelectorAll('.animate-on-scroll');
  if (animElements.length > 0 && 'IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-in');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    animElements.forEach(function (el) { observer.observe(el); });
  }

  /* 9. COMPTEUR ANIME — chiffres qui défilent */
  var counterElements = document.querySelectorAll('.chiffre-item__number[data-target]');
  if (counterElements.length > 0 && 'IntersectionObserver' in window) {
    var counterObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          var el = entry.target;
          var target = parseInt(el.getAttribute('data-target'), 10);
          var suffix = el.getAttribute('data-suffix') || '';
          var duration = 2000;
          var startTime = null;

          function animate(timestamp) {
            if (!startTime) startTime = timestamp;
            var progress = Math.min((timestamp - startTime) / duration, 1);
            var eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
            var current = Math.floor(eased * target);
            el.textContent = current + suffix;
            if (progress < 1) {
              requestAnimationFrame(animate);
            } else {
              el.textContent = target + suffix;
            }
          }
          requestAnimationFrame(animate);
          counterObserver.unobserve(el);
        }
      });
    }, { threshold: 0.3 });

    counterElements.forEach(function (el) { counterObserver.observe(el); });
  }

  /* 10. AVANT/APRES — slider comparaison */
  var baSliders = document.querySelectorAll('.ba-slider');
  baSliders.forEach(function (slider) {
    var handle = slider.querySelector('.ba-slider__handle');
    var afterImg = slider.querySelector('.ba-slider__after');
    var isDragging = false;

    function updatePosition(x) {
      var rect = slider.getBoundingClientRect();
      var pos = Math.max(0, Math.min(x - rect.left, rect.width));
      var percent = (pos / rect.width) * 100;
      afterImg.style.clipPath = 'inset(0 0 0 ' + percent + '%)';
      handle.style.left = percent + '%';
    }

    if (handle) {
      handle.addEventListener('mousedown', function () { isDragging = true; });
      handle.addEventListener('touchstart', function () { isDragging = true; }, { passive: true });

      document.addEventListener('mousemove', function (e) {
        if (isDragging) { e.preventDefault(); updatePosition(e.clientX); }
      });
      document.addEventListener('touchmove', function (e) {
        if (isDragging) { updatePosition(e.touches[0].clientX); }
      }, { passive: true });

      document.addEventListener('mouseup', function () { isDragging = false; });
      document.addEventListener('touchend', function () { isDragging = false; });

      slider.addEventListener('click', function (e) { updatePosition(e.clientX); });
    }
  });

  /* FAQ accordion */
  var faqItems = document.querySelectorAll('.faq-item__question');
  faqItems.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var item = btn.closest('.faq-item');
      var answer = item.querySelector('.faq-item__answer');
      var isOpen = item.classList.contains('open');

      // Close all
      document.querySelectorAll('.faq-item').forEach(function (faq) {
        faq.classList.remove('open');
        faq.querySelector('.faq-item__answer').style.maxHeight = null;
      });

      if (!isOpen) {
        item.classList.add('open');
        answer.style.maxHeight = answer.scrollHeight + 'px';
      }
    });
  });

});
