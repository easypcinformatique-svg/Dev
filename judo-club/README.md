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
| `images/*.jpg`, `images/logo.png` | Logo et photos repris du site actuel du club (Google Sites) : hero, Raoul Laï, Nicolas Biodore, Yves, dojo, championnat FSGT 2026, article de presse |
| `images/og-image.jpg` | Image de partage réseaux sociaux (1200 × 630, JPEG — Facebook et WhatsApp ne savent pas afficher un SVG) |
| `favicon.svg`, `site.webmanifest`, `robots.txt`, `sitemap.xml` | Fichiers techniques |
| `_headers` | En-têtes de sécurité et cache pour Netlify / Cloudflare Pages |
| `.htaccess` | Équivalent Apache (OVH, o2switch, Infomaniak) : HTTPS forcé, cache, 404 |
| `CNAME` | Domaine servi par GitHub Pages : `jccadeneaux-ojm.fr` |
| `.nojekyll` | Désactive Jekyll sur GitHub Pages (sinon les fichiers commençant par `_` sont ignorés) |
| `DEPLOIEMENT.md` | Procédure complète de mise en ligne : dépôt, Pages, DNS, HTTPS |

## Mise en ligne

Aucune compilation : le dossier se dépose tel quel à la racine d'un hébergement.

La cible retenue est **GitHub Pages sur le domaine `jccadeneaux-ojm.fr`**, via un
dépôt dédié `easypcinformatique-svg/jccadeneaux-ojm` (celui de `Dev` héberge déjà
un autre site Pages, et un dépôt ne peut en servir qu'un).
→ **[`DEPLOIEMENT.md`](DEPLOIEMENT.md)** détaille chaque étape : création du
dépôt, activation de Pages, enregistrements DNS, HTTPS, retour arrière.

`Dev` reste la source de vérité : `.github/workflows/deploy-judo-club.yml`
republie `judo-club/` à chaque push sur `master`.

Sur un hébergement classique, un seul des deux fichiers `_headers` / `.htaccess`
sert selon l'hébergeur, l'autre est ignoré sans effet. **GitHub Pages ignore les
deux** : les en-têtes de sécurité qu'ils déclarent n'y sont pas appliqués
(cf. « Limites connues » dans `DEPLOIEMENT.md`).

Test en local :

```bash
python3 -m http.server 8080   # puis http://localhost:8080
```

## À compléter avant la mise en ligne

Ces valeurs sont des **placeholders** ; le contenu factuel du club doit les remplacer.

1. **Domaine** — remplacer `jccadeneaux-ojm.fr` partout (`index.html`, pages
   annexes, `robots.txt`, `sitemap.xml`, `site.webmanifest`).
2. **Téléphone** — 06 63 67 12 83 et 06 61 14 14 61, repris du site actuel
   du club (bloc contact, barre mobile, JSON-LD).
3. **E-mail** — `contact@judoclubcadeneaux.fr`, repris du site actuel
   (`index.html`, `js/main.js` constante `CLUB_EMAIL`, pages légales).
4. **Tarifs** — 180 / 230 / 250 € sont des exemples, repérables par
   l'attribut `data-price`. Les remises et aides listées sont à confirmer.
5. **Horaires** — repris du planning officiel du club (saison 2026/2027) :
   baby judo mercredi 17h30 ; enfants mardi et vendredi 18h ; ados lundi et
   jeudi 18h ; juniors/seniors lundi et jeudi 19h30 ; techniques et katas
   mercredi et vendredi 19h30 ; self-défense mardi 20h. Modifier uniquement les
   `<li class="slot">` du planning : le prochain cours, le jour courant et le
   sélecteur de groupe se recalculent à partir de là.
6. **Gym seniors** — la carte existe sans horaire : préciser le créneau.
7. **Le sensei** — la section présente Raoul Laï, 6e dan (fait public, cité
   parmi les grands champions historiques du judo provençal). Les lignes
   « Titres » et « Parcours » du bloc `.palmares` sont à compléter avec le
   club (titre, niveau, année) ; la photo remplace le pictogramme dans
   `.sensei__frame`.
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
