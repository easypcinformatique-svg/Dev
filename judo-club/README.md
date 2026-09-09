# Judo Club Cadeneaux OJM — site vitrine

Site statique (HTML / CSS / JavaScript, sans dépendance ni build) pour le
**Judo Club Cadeneaux OJM** — Olympic Judo Méditerranée, complexe sportif des
Bouroumettes, Les Cadeneaux, 13170 Les Pennes-Mirabeau.

Sources de départ : la page Facebook du club et sa fiche sur le site de la
Fédération Française de Judo (adresse, disciplines, horaires).

## Contenu

| Fichier | Rôle |
|---|---|
| `index.html` | Page principale : accueil avec « prochain cours » calculé, club, cours, sélecteur de groupe par année de naissance, planning filtrable (jour courant mis en avant), tarifs, pourquoi le judo, ceintures, code moral, encadrement, équipement, actualités, inscription, FAQ, contact + carte |
| `blog/judo-enfant-pennes-mirabeau.html` | Guide parents : inscrire son enfant au judo |
| `blog/judo-adulte-debutant.html` | Guide : commencer le judo à l'âge adulte |
| `blog/ju-jitsu-self-defense-pennes-mirabeau.html` | Guide : ju-jitsu et self-défense |
| `mentions-legales.html`, `politique-confidentialite.html` | Obligations légales et RGPD (champs à compléter) |
| `404.html` | Page d'erreur |
| `css/style.css` | Feuille unique : design tokens, composants, responsive, impression, `prefers-reduced-motion` |
| `js/main.js` | Menu mobile, scrollspy, prochain cours, jour courant, filtres, sélecteur de groupe, lightbox, formulaire |
| `images/picto/*.svg` | Pictogrammes de l'identité visuelle (style olympique) |
| `images/og-image.svg` | Image de partage réseaux sociaux (1200 × 630) |
| `favicon.svg`, `site.webmanifest`, `robots.txt`, `sitemap.xml` | Fichiers techniques |
| `_headers` | En-têtes de sécurité et cache pour Netlify / Cloudflare Pages |
| `.htaccess` | Équivalent Apache (OVH, o2switch, Infomaniak) : HTTPS forcé, cache, 404 |

## Mise en ligne

Aucune compilation. Déposer le dossier à la racine de l'hébergement.
Un seul des deux fichiers `_headers` / `.htaccess` sert selon l'hébergeur ;
l'autre est ignoré sans effet.

Test en local :

```bash
python3 -m http.server 8080   # puis http://localhost:8080
```

## À compléter avant la mise en ligne

Ces valeurs sont des **placeholders** ; le contenu factuel du club doit les remplacer.

1. **Domaine** — remplacer `judocadeneaux-ojm.fr` partout (`index.html`, pages
   annexes, `robots.txt`, `sitemap.xml`, `site.webmanifest`).
2. **Téléphone** — `06 XX XX XX XX` et `+33600000000` (`index.html` : bloc
   contact, barre mobile, JSON-LD).
3. **E-mail** — `contact@judocadeneaux-ojm.fr` (`index.html`, `js/main.js`
   constante `CLUB_EMAIL`, pages légales).
4. **Tarifs** — 180 / 230 / 250 € sont des exemples, repérables par
   l'attribut `data-price`. Les remises et aides listées sont à confirmer.
5. **Horaires** — repris des annuaires fédéraux : éveil mardi 17h-18h ; judo
   éducatif lundi, mercredi, vendredi 17h30-19h ; compétition/adultes 19h-21h.
   Modifier uniquement les `<li class="slot">` du planning : le prochain cours,
   le jour courant et le sélecteur de groupe se recalculent à partir de là.
6. **Ju-jitsu** — la fiche fédérale mentionne la discipline sans créneau
   dédié : préciser le créneau réel ou retirer la carte.
7. **Encadrement** — noms, grades et diplômes réels des professeurs. Pour
   ajouter des photos, remplacer le `<img>` de chaque `.coach__photo`.
8. **Actualités** — les trois dates sont des exemples de rendez-vous de saison.
9. **Galerie** — la section est prête, en commentaire dans `index.html`.
   Déposer les photos dans `images/galerie/` puis retirer le commentaire.
10. **Coordonnées GPS** — `43.4017 / 5.3452` est une position approximative
    des Cadeneaux : ajuster `geo.position`, le JSON-LD et le `marker` de la
    carte sur l'entrée exacte du dojo.
11. **Mentions légales** — RNA, siège social, directeur de publication,
    hébergeur.
12. **Catégories d'âge** — le sélecteur applique les catégories France Judo
    par année civile (`CATEGORIES` dans `js/main.js`). Vérifier chaque saison
    que les bornes fédérales n'ont pas changé.

## Formulaire de contact

Sans configuration, le formulaire valide les champs puis ouvre la messagerie
du visiteur avec un message pré-rempli (aucun serveur nécessaire).

Pour un envoi automatique, ajouter un endpoint sur la balise `<form>` :

```html
<form class="form" id="contact-form" data-endpoint="https://formspree.io/f/xxxxxxx" novalidate>
```

Le script poste alors un JSON (`prenom`, `nom`, `email`, `tel`, `groupe`,
`message`). Si un autre service que Formspree est utilisé, l'ajouter aussi
dans la ligne `connect-src` de `_headers`.

## Accessibilité et performance

- Navigation clavier complète, lien d'évitement, `aria-expanded` sur le menu,
  lightbox fermable par `Échap`, résultats du sélecteur annoncés (`aria-live`).
- Animations désactivées si `prefers-reduced-motion: reduce`.
- Images SVG légères avec `width`/`height` déclarés, pas de décalage de mise
  en page.
- Aucune librairie tierce : seules les polices Google et la carte
  OpenStreetMap sont chargées depuis l'extérieur.
- Feuille d'impression : le bouton « Imprimer le planning » ne sort que les
  horaires.

## SEO

- Balises title/description/OG/Twitter, données structurées `SportsClub`,
  `FAQPage`, `Article` et `BreadcrumbList` sur les guides.
- Balises géographiques (FR-13) et zone desservie dans le JSON-LD.
- `sitemap.xml` et `robots.txt` à mettre à jour à chaque nouvelle page.
