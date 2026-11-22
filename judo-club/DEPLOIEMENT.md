# Mise en ligne sur jccadeneaux-ojm.fr

Le site est statique (aucune compilation, aucune dependance) : GitHub Pages le
sert tel quel. Ce document decrit la mise en ligne de bout en bout.

---

## 1. Pourquoi un depot dedie

Le site part dans un nouveau depot **`easypcinformatique-svg/jccadeneaux-ojm`**,
et non depuis `Dev`, pour trois raisons :

1. **Un depot = un seul site Pages.** Celui de `Dev` est deja pris : les
   workflows `deploy-calculator.yml` et `deploy-auction-scanner.yml` y publient
   deja. Ajouter le judo ecraserait l'un des deux.
2. **Un domaine personnalise s'applique au site Pages entier**, pas a un
   sous-dossier. `jccadeneaux-ojm.fr` sur `Dev` servirait le dernier projet
   deploye, pas le judo.
3. **L'apex doit servir la racine.** Sur un depot dedie le site repond sur
   `https://jccadeneaux-ojm.fr/` ; depuis `Dev` il repondrait sous
   `/Dev/judo-club/`, ce qui casse le `sitemap.xml`, les URL canoniques et le
   referencement.

`Dev` reste la source de verite : le workflow `.github/workflows/deploy-judo-club.yml`
recopie `judo-club/` vers le depot de publication a chaque push sur `master`.

---

## 2. Creer le depot de publication

Depot **public** (Pages est gratuit sur les depots publics ; sur un depot prive
il exige un abonnement payant) :

- Nom : `jccadeneaux-ojm`
- Description : `Site du Judo Club Cadeneaux O.J.M. — jccadeneaux-ojm.fr`
- Sans README, sans .gitignore, sans licence (le premier push fournit tout)

Premier envoi, depuis la racine du monorepo :

```bash
cd judo-club
git init -b main
git add -A
git commit -m "Mise en ligne initiale du site du Judo Club Cadeneaux OJM"
git remote add origin https://github.com/easypcinformatique-svg/jccadeneaux-ojm.git
git push -u origin main
rm -rf .git          # le monorepo Dev reste la source de verite
```

---

## 3. Activer GitHub Pages

Depot `jccadeneaux-ojm` > **Settings > Pages** :

- **Source** : `Deploy from a branch`
- **Branch** : `main`, dossier `/ (root)`

Le site repond sous deux a trois minutes sur
`https://easypcinformatique-svg.github.io/jccadeneaux-ojm/`.
**Verifier cette adresse avant de toucher au DNS** : elle valide que le site
fonctionne, sans risquer de couper le site actuel.

> Les liens internes sont tous relatifs (une seule exception, `/sitemap.xml`),
> donc l'apercu `.github.io` s'affiche correctement malgre le sous-chemin.

---

## 4. Le DNS

Le fichier `CNAME` a la racine contient deja `jccadeneaux-ojm.fr`. Il reste a
faire pointer le domaine chez le bureau d'enregistrement du club.

**Avant tout : le domaine sert aujourd'hui le site Google Sites.** Des que les
enregistrements changent, l'ancien site devient inaccessible. Deux precautions :

- Abaisser le TTL a 300 secondes **24 h avant** la bascule, pour pouvoir revenir
  en arriere en cinq minutes si besoin.
- Retirer le domaine personnalise cote Google Sites *apres* la bascule, pas
  avant.

Supprimer les enregistrements A / AAAA / CNAME existants sur `@` et `www`, puis
creer :

| Type  | Nom   | Valeur                             |
|-------|-------|------------------------------------|
| A     | `@`   | `185.199.108.153`                  |
| A     | `@`   | `185.199.109.153`                  |
| A     | `@`   | `185.199.110.153`                  |
| A     | `@`   | `185.199.111.153`                  |
| AAAA  | `@`   | `2606:50c0:8000::153`              |
| AAAA  | `@`   | `2606:50c0:8001::153`              |
| AAAA  | `@`   | `2606:50c0:8002::153`              |
| AAAA  | `@`   | `2606:50c0:8003::153`              |
| CNAME | `www` | `easypcinformatique-svg.github.io.` |

Les quatre A (et quatre AAAA) ne sont pas un choix : ce sont les quatre points
d'entree de GitHub, tous les quatre necessaires. Le CNAME de `www` vise le
compte, **sans** le nom du depot.

Controle de la propagation :

```bash
dig +short jccadeneaux-ojm.fr
dig +short www.jccadeneaux-ojm.fr
```

---

## 5. Raccorder le domaine et activer HTTPS

Une fois le DNS propage (de quelques minutes a 24 h) :

1. **Settings > Pages > Custom domain** : saisir `jccadeneaux-ojm.fr`, puis
   *Save*. GitHub verifie les enregistrements ; le controle echoue tant que la
   propagation n'est pas faite, c'est normal, il suffit de reessayer.
2. Attendre que **Enforce HTTPS** devienne cochable — GitHub commande d'abord un
   certificat Let's Encrypt, ce qui prend generalement moins d'une heure. Cocher
   la case.
3. Optionnel mais recommande : **Settings > Pages > Verified domains** au niveau
   du compte, pour empecher qu'un tiers rattache le domaine a un autre depot.

Le site est alors en ligne sur `https://jccadeneaux-ojm.fr/`, `www` redirigeant
vers l'apex.

---

## 6. Publication continue

Une fois en place, plus rien de manuel : toute modification de `judo-club/`
poussee sur `master` est republiee par
`.github/workflows/deploy-judo-club.yml`.

Le workflow a besoin d'un secret, **`JUDO_DEPLOY_TOKEN`** :

1. GitHub > Settings (compte) > Developer settings > Personal access tokens >
   **Fine-grained tokens** > *Generate new token*
2. Repository access : **Only select repositories** > `jccadeneaux-ojm`
3. Permissions > Repository permissions > **Contents : Read and write**
4. Copier le token, puis depot `Dev` > Settings > Secrets and variables >
   Actions > *New repository secret*, nom `JUDO_DEPLOY_TOKEN`

Sans ce secret le workflow ne casse pas : il s'arrete avec un avertissement.

Avant de recopier quoi que ce soit, il verifie la presence de `index.html`,
`CNAME` et `.nojekyll`, le contenu du `CNAME`, et que toutes les images
referencees dans les pages existent reellement.

---

## 7. Limites connues

- **`_headers` et `.htaccess` sont ignores par GitHub Pages.** Ces deux fichiers
  visent respectivement Netlify et Apache. En consequence, les en-tetes de
  securite qu'ils declarent (CSP, `X-Frame-Options`, `Referrer-Policy`) **ne
  sont pas appliques**. Pages n'offre aucun moyen de definir des en-tetes
  personnalises. Si ces en-tetes comptent, il faut soit passer par Netlify ou
  Cloudflare Pages (qui lisent `_headers`), soit placer Cloudflare devant le
  site. Les fichiers sont conserves tels quels pour ce cas.
- **Pas de traitement serveur.** Le formulaire d'inscription passe par un
  service externe (Formspree) ; c'est deja le cas.
- **`404.html` fonctionne** nativement sur Pages, rien a configurer.
- **`.nojekyll`** desactive le moteur Jekyll : sans lui, Pages ignorerait les
  fichiers et dossiers commencant par `_`.

---

## 8. Retour en arriere

Restaurer les enregistrements DNS d'origine (d'ou l'interet du TTL abaisse) et
remettre le domaine personnalise cote Google Sites. Le depot de publication peut
rester en place sans nuire.
