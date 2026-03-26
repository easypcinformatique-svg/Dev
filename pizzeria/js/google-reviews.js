/* ========================================
   Google Places API - Avis automatiques
   ========================================

   CONFIGURATION :
   1. Allez sur https://console.cloud.google.com/
   2. Creez un projet (ou selectionnez un existant)
   3. Activez "Places API" et "Maps JavaScript API"
   4. Creez une cle API (Identifiants > Creer des identifiants > Cle API)
   5. Restreignez la cle :
      - Sites web HTTP referents : votre domaine (ex: pizzanapolicarpentras.fr/*)
      - APIs : Places API + Maps JavaScript API
   6. Remplacez VOTRE_CLE_API dans index.html par votre cle

   L'API Google retourne max 5 avis les plus pertinents.
   Les avis statiques restent en fallback si l'API echoue.
   ======================================== */

(function () {
    'use strict';

    // Place ID de Pizza Napoli Carpentras
    // Pour trouver votre Place ID : https://developers.google.com/maps/documentation/places/web-service/place-id
    var PLACE_ID = 'ChIJ6-i2vRmKtRIRwMwe1UNYRZY';

    // Filtre : note minimum des avis a afficher (5 = uniquement 5 etoiles)
    var MIN_RATING = 5;

    function initGoogleReviews() {
        // Verifier que l'API Google est chargee
        if (typeof google === 'undefined' || !google.maps || !google.maps.places) {
            return; // Fallback sur avis statiques
        }

        // Creer un element invisible pour le service Places
        var mapDiv = document.createElement('div');
        mapDiv.style.display = 'none';
        document.body.appendChild(mapDiv);

        var service = new google.maps.places.PlacesService(mapDiv);

        service.getDetails({
            placeId: PLACE_ID,
            fields: ['reviews', 'rating', 'user_ratings_total']
        }, function (place, status) {
            if (status !== google.maps.places.PlacesServiceStatus.OK || !place) {
                return; // Fallback sur avis statiques
            }

            // Mettre a jour le badge de note
            updateRatingBadge(place.rating, place.user_ratings_total);

            // Filtrer les avis 5 etoiles
            var reviews = (place.reviews || []).filter(function (r) {
                return r.rating >= MIN_RATING;
            });

            // Si on a des avis 5 etoiles, mettre a jour le carousel
            if (reviews.length > 0) {
                updateCarousel(reviews);
            }
        });
    }

    function updateRatingBadge(rating, totalReviews) {
        var ratingNumber = document.querySelector('.rating-number');
        var starsDisplay = document.querySelector('.stars-display');
        var ratingCount = document.querySelector('.google-rating-count');

        if (ratingNumber) {
            ratingNumber.textContent = rating.toFixed(1);
        }

        if (starsDisplay) {
            var fullStars = Math.floor(rating);
            var hasHalf = (rating - fullStars) >= 0.3;
            var stars = '';
            for (var i = 0; i < 5; i++) {
                if (i < fullStars) {
                    stars += '\u2605'; // etoile pleine
                } else if (i === fullStars && hasHalf) {
                    stars += '\u2605'; // on arrondit vers le haut
                } else {
                    stars += '\u2606'; // etoile vide
                }
            }
            starsDisplay.textContent = stars;
        }

        if (ratingCount && totalReviews) {
            ratingCount.innerHTML = 'Base sur <strong>' + totalReviews + ' avis</strong> Google verifies';
        }
    }

    function generateStars(rating) {
        var stars = '';
        for (var i = 0; i < rating; i++) {
            stars += '\u2605';
        }
        return stars;
    }

    function getInitial(name) {
        return name ? name.charAt(0).toUpperCase() : '?';
    }

    function updateCarousel(reviews) {
        var track = document.querySelector('.avis-carousel-track');
        if (!track) return;

        // Vider le carousel
        track.innerHTML = '';

        // Ajouter les avis Google
        reviews.forEach(function (review) {
            var card = document.createElement('div');
            card.classList.add('avis-card');

            var authorName = review.author_name || 'Client Google';

            card.innerHTML =
                '<div class="avis-stars">' + generateStars(review.rating) + '</div>' +
                '<p class="avis-text">"' + escapeHtml(review.text) + '"</p>' +
                '<div class="avis-author">' +
                    (review.profile_photo_url
                        ? '<img class="avis-avatar-img" src="' + review.profile_photo_url + '" alt="' + escapeHtml(authorName) + '" width="45" height="45">'
                        : '<div class="avis-avatar">' + getInitial(authorName) + '</div>') +
                    '<div>' +
                        '<strong>' + escapeHtml(authorName) + '</strong>' +
                        '<span>' + review.relative_time_description + '</span>' +
                    '</div>' +
                '</div>';

            track.appendChild(card);
        });

        // Reinitialiser le carousel (declencher un resize pour recalculer)
        window.dispatchEvent(new Event('resize'));
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    // Exposer la fonction pour le callback Google Maps
    window.initGoogleReviews = initGoogleReviews;
})();
