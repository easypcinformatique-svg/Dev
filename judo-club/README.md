# Judo Club Cadeneaux OJM — site vitrine

Site statique (HTML / CSS / JavaScript, sans dépendance ni build) pour le
**Judo Club Cadeneaux OJM** — Olympic Judo Méditerranée, complexe sportif des
Bouroumettes, Les Cadeneaux, 13170 Les Pennes-Mirabeau.

Source d'information de départ : la page Facebook du club et la fiche du club
sur le site de la Fédération Française de Judo.

## Contenu

| Fichier | Rôle |
|---|---|
| `index.html` | Page unique : hero, club, cours, planning filtrable, tarifs, ceintures, code moral, encadrement, galerie, actualités, inscription, FAQ, contact |
| `blog/judo-enfant-pennes-mirabeau.html` | Article SEO local « inscrire son enfant au judo » |
| `mentions-legales.html` | Mentions légales (champs à compléter) |
| `politique-confidentialite.html` | RGPD : données collectées, durées, droits |
| `404.html` | Page d'erreur |
| `css/style.css` | Feuille de style unique (design tokens, responsive, print, `prefers-reduced-motion`) |
| `js/main.js` | Menu mobile, scrollspy, filtres planning, lightbox, validation du formulaire |
| `images/*.svg` | Visuels de remplacement, à remplacer par les photos du club |
| `robots.txt`, `sitemap.xml`, `site.webmanifest`, `favicon.svg` | Fichiers techniques |

## Mise en ligne

Aucune compilation. Déposer le dossier sur n'importe quel hébergement statique
(Netlify, GitHub Pages, OVH, Infomaniak…) et servir `index.html` à la racine.
Vérifier que `404.html` est bien déclaré comme page d'erreur de l'hébergeur.

Test en local :

```bash
python3 -m http.server 8080   # puis http://localhost:8080
```

## À compléter avant la mise en ligne

Ces valeurs sont des **placeholders** ; le contenu factuel du club doit les remplacer.

1. **Domaine** — remplacer `judocadeneaux-ojm.fr` partout (`index.html`, pages
   annexes, `robots.txt`, `sitemap.xml`, `site.webmanifest`).
2. **Téléphone** — `06 XX XX XX XX` dans `index.html` (bloc contact) et
   `+33600000000` dans le JSON-LD.
3. **E-mail** — `contact@judocadeneaux-ojm.fr` (`index.html`, `js/main.js`,
   pages légales).
4. **Tarifs** — les montants 180 / 230 / 250 € sont des exemples, marqués par
   l'attribut `data-price` pour les retrouver rapidement.
5. **Horaires** — repris des annuaires fédéraux (éveil le mardi 17h-18h ;
   judo éducatif lundi, mercredi, vendredi 17h30-19h ; compétition/adultes
   19h-21h). À confirmer avec le professeur avant publication.
6. **Ju-jitsu** — la fiche fédérale mentionne la discipline sans créneau
   dédié : préciser le créneau réel ou retirer la carte correspondante.
7. **Encadrement** — noms, grades et diplômes réels des professeurs.
8. **Actualités** — les trois dates sont des exemples de rendez-vous de saison.
9. **Photos** — remplacer les SVG de `images/` par des photos JPG/WebP
   (mêmes noms de fichier, ou mettre à jour les `src`). Prévoir une image
   `og-image.jpg` de 1200 × 630 px pour les partages sur les réseaux.
10. **Coordonnées GPS** — `43.4017 / 5.3452` est une position approximative des
    Cadeneaux : ajuster le `geo.position`, le JSON-LD et le `marker` de la carte
    OpenStreetMap sur l'entrée exacte du dojo.
11. **Mentions légales** — RNA de l'association, siège social, directeur de la
    publication et hébergeur.

## Formulaire de contact

Sans configuration, le formulaire valide les champs puis ouvre la messagerie du
visiteur avec un message pré-rempli (aucun serveur nécessaire).

Pour un envoi automatique, ajouter un endpoint sur la balise `<form>` :

```html
<form class="form" id="contact-form" data-endpoint="https://formspree.io/f/xxxxxxx" novalidate>
```

Le script poste alors un JSON (`prenom`, `nom`, `email`, `tel`, `groupe`,
`message`) et affiche un message de confirmation ou de repli.

## Accessibilité et performance

- Navigation clavier complète, lien d'évitement, `aria-expanded` sur le menu,
  lightbox focusable et fermable par `Échap`.
- Animations désactivées si `prefers-reduced-motion: reduce`.
- Images en `loading="lazy"` avec `width`/`height` pour éviter les décalages.
- Aucune librairie tierce : seules les polices Google et la carte OpenStreetMap
  sont chargées depuis l'extérieur (mentionné dans la page confidentialité).

## SEO

- Balises title/description/OG/Twitter et données structurées JSON-LD
  (`SportsClub` + `FAQPage`).
- Balises géographiques pour le référencement local (FR-13).
- `sitemap.xml` et `robots.txt` à mettre à jour à chaque nouvelle page.
