# Sur Le Pouce ML — Site E-commerce

Site de commande en ligne pour **Sur Le Pouce ML**, traiteur d'Arménie et de Méditerranée à Marseille Château-Gombert.

## Structure

```
surlepouceml/
├── index.html        # Page unique complète
├── css/style.css     # Thème Luxury Mediterranean
├── js/products.js    # Catalogue produits (32 articles)
├── js/app.js         # Panier, checkout 4 étapes, animations
└── README.md
```

## Fonctionnalités

- Catalogue filtrable par catégorie (7 catégories)
- Panier latéral avec persistance localStorage
- Checkout en 4 étapes (récap → infos → confirmation → succès)
- Minimum de commande 10 € enforced
- Formulaire de devis traiteur (slider personnes, budget)
- Animations au scroll (IntersectionObserver)
- Google Maps intégré
- Schema.org JSON-LD (SEO)
- 100% responsive mobile-first

## Remplacer les images Unsplash par de vraies photos

Dans `js/products.js`, chaque produit a une propriété `img`. Remplacez l'URL Unsplash par le chemin de votre photo :

```js
// Avant
img: "https://images.unsplash.com/photo-xxx?w=600"

// Après (photo locale)
img: "images/chawarma-poulet.jpg"
```

Taille recommandée : 600×400px, format WebP ou JPEG optimisé.

## Connecter un service d'envoi de formulaires

### Option 1 : Formspree (gratuit, sans backend)

1. Créez un compte sur [formspree.io](https://formspree.io)
2. Créez un formulaire et récupérez l'endpoint (ex: `https://formspree.io/f/xABCDEFG`)
3. Dans `js/app.js`, modifiez la fonction `handleDevis` :

```js
function handleDevis(e) {
    e.preventDefault();
    fetch('https://formspree.io/f/VOTRE_ID', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            nom: $('devis-nom').value,
            email: $('devis-email').value,
            // ... autres champs
        })
    }).then(() => {
        form.style.display = 'none';
        success.hidden = false;
    });
}
```

### Option 2 : EmailJS (envoi email direct)

1. Compte sur [emailjs.com](https://www.emailjs.com)
2. Ajoutez le script dans `index.html` : `<script src="https://cdn.jsdelivr.net/npm/@emailjs/browser@3/dist/email.min.js"></script>`
3. Utilisez `emailjs.send('service_id', 'template_id', templateParams)` dans les handlers

## Intégrer Stripe pour le paiement en ligne

1. Créez un compte [Stripe](https://stripe.com)
2. Ajoutez Stripe.js : `<script src="https://js.stripe.com/v3/"></script>`
3. Dans la fonction `confirmOrder`, au lieu de sauvegarder en localStorage, appelez votre backend :

```js
// Créer une session Stripe Checkout
const response = await fetch('/api/create-checkout-session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items: cart, client: orderData })
});
const { url } = await response.json();
window.location = url;  // Redirige vers Stripe
```

4. Backend Node.js minimal nécessaire pour créer la session Stripe (ou utilisez Stripe Payment Links pour une solution sans backend).

## Déployer

### GitHub Pages (5 minutes)

1. Poussez le code sur GitHub
2. Settings → Pages → Source : branch `gh-pages` (ou `main`)
3. Le site est en ligne sur `https://votre-user.github.io/repo/surlepouceml/`

### Netlify (3 minutes)

1. Glissez-déposez le dossier `surlepouceml/` sur [app.netlify.com/drop](https://app.netlify.com/drop)
2. C'est en ligne instantanément avec HTTPS

### Render (5 minutes)

1. Créez un **Static Site** sur [render.com](https://render.com)
2. Connectez le repo GitHub
3. **Publish Directory** : `surlepouceml`
4. Deploy !

## Licence

Projet privé — ML SNACK / Sur Le Pouce ML — Marseille 13013
