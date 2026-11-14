# Site AKMS Autos · Nikoghossian Père & Fils

Site du garage AMKS Autos (carrosserie, peinture, mécanique), 115 boulevard de la Millière, Marseille 11e.
Site statique : HTML, CSS et JavaScript sans dépendance ni étape de compilation. Il s'héberge tel quel (GitHub Pages, Netlify, OVH…).

## Pages

| Fichier | Rôle |
|---|---|
| `index.html` | Site public : services, forfaits, sinistres, outil d'échéances du véhicule, occasions, demande de devis ou de RDV, FAQ, contact |
| `mentions-legales.html` | Mentions légales et données personnelles (remplies depuis `js/config.js`) |
| `gerance.html` | Espace gérance : tableau des échéances de l'entreprise. Non référencé (`noindex`). **Ne contient aucune donnée** : on importe le plan d'actions par copier-coller depuis Google Sheets, et tout reste dans le navigateur de la personne qui l'utilise |

## Fonctions dynamiques

- Statut « Ouvert / Fermé » en direct, calculé depuis les horaires.
- Plaque d'immatriculation mise en forme pendant la saisie (format SIV AB-123-CD).
- Demande en 3 étapes : besoin, véhicule, créneau. Les créneaux suivent les horaires et les fermetures. Le message final s'envoie par WhatsApp ou par e-mail, et le RDV s'ajoute à l'agenda (.ics).
- Outil client : prochain contrôle technique (4 ans, puis tous les 2 ans) et prochaine révision, avec export agenda et rappel à J-7.
- Occasions : liste lue dans `data/vehicules.json`, avec filtres. Liste vide : le site propose la recherche sur mesure.
- Espace gérance : retards, échéances de la semaine, statuts modifiables, échéances récurrentes, export agenda (rappels J-7 et J-1), copie vers le tableur.

## Modifier le contenu

- **Coordonnées, horaires, fermetures, forfaits** : `js/config.js`. Les valeurs marquées « À CONFIRMER » sont à vérifier avant la mise en ligne.
- **Véhicules à vendre** : ajouter des objets dans `data/vehicules.json` (modèle dans le champ `exemple`). Photos dans `img/`.
- **Domaine** : remplacer `https://akms-autos.fr/` dans `index.html`, `robots.txt` et `sitemap.xml`.

## Tester en local

```bash
cd amks-autos && python3 -m http.server 8000
```

Puis ouvrir http://localhost:8000.

## Confidentialité

Ce dépôt est public. Ne jamais y placer de données de l'entreprise (comptabilité, TVA, relevés, courriers). L'espace gérance est fait pour que ces données restent hors du dépôt.
