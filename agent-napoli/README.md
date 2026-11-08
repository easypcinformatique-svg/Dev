# Agent Pizza Napoli — phase 1 (administratif)

Chaque matin à 9h, l'agent passe sur la boîte **carpentraspizzanapoli@gmail.com**
et envoie aux deux gérants un rapport par mail.

## Ce qu'il fait

| Tâche | Ce que fait l'agent | Ce qui reste aux gérants |
| --- | --- | --- |
| Z de caisse L'Addition | Lit le mail du Z et le ticket Z en PDF (livraison / à emporter, moyens de paiement, nombre de tickets), télécharge les exports dans Drive `Pizza Napoli/Caisse/AAAA-MM/`, inscrit les chiffres dans le tableur | Clôturer le service chaque soir |
| Contrôles de caisse | Alerte si annulations > 3 % du CA, offerts > 5 %, corrections élevées, Z manquant, CA en baisse, ticket moyen en baisse, pizza non vendue depuis 14 jours, record | Vérifier les alertes |
| Tri de Gmail | Range chaque mail dans **vos libellés existants** (Ticket Z, Factures, HYGIENES…), sans jamais en créer, et résume les mails importants. Seul « Agent/Traité » est ajouté, pour ne pas relire un mail | Lire le rapport |
| Réponses | Prépare un **brouillon** de réponse dans le fil Gmail | Relire, compléter les `[À COMPLÉTER]`, envoyer |
| Factures | Lit les PDF et photos, les range dans `Pizza Napoli/Factures/AAAA-MM/`, les inscrit dans le tableur, repère les doublons | Payer, puis écrire « payée » dans la colonne Statut du tableur |
| Échéances de paiement | Les signale à J-7 dans le rapport, en alerte à J-1 et en retard | Payer |
| Obligations légales | Les place dans Google Agenda avec rappels à J-7 et J-1 | Les saisir une fois dans l'onglet « Obligations » |
| Relevé de compte | Lit le relevé déposé dans Drive `Pizza Napoli/Banque/À traiter` (PDF, CSV ou Excel), passe à « payée » les factures retrouvées sur le relevé, liste les débits sans facture, compare les remises CB aux paiements CB des tickets Z, range le relevé et le rapprochement dans le dossier Cegid | Déposer le relevé chaque début de mois, retrouver les pièces manquantes |
| Comptable (Cegid) | Le 1er du mois, prépare dans Drive le dossier `Pizza Napoli/Comptable/AAAA-MM à déposer sur Cegid` : copie des factures du mois et deux CSV (factures, ventes) | Glisser le dossier sur Cegid |

**L'agent n'envoie jamais rien à l'extérieur** : le seul mail qu'il envoie lui-même
est le rapport aux gérants. Il ne dépose rien sur Cegid et n'a aucun accès bancaire.

### Déposer une facture papier

- soit une photo envoyée à carpentraspizzanapoli@gmail.com avec **« FACTURE »** dans l'objet ;
- soit une photo ou un scan déposé dans Drive `Pizza Napoli/Factures/À traiter` (appli Google Drive du téléphone, bouton « + » puis « Numériser »).

### Déposer le relevé de compte (avant la TVA)

Chaque début de mois, télécharge le relevé du mois écoulé depuis la banque en ligne
(PDF, ou export CSV / Excel) et dépose-le dans Drive `Pizza Napoli/Banque/À traiter`.
Tant qu'il n'est pas arrivé, le rapport de 9h le rappelle. Au passage suivant, l'agent :

- vérifie que les opérations lues retombent sur le solde final (sinon il le signale) ;
- passe à « payée » chaque facture dont le montant correspond à un débit (même montant,
  débit entre 7 jours avant et 90 jours après la facture ; à montant égal, le nom du
  fournisseur dans le libellé départage) ;
- liste les débits sans facture : ce sont les pièces à retrouver avant la déclaration de TVA ;
- compare les remises CB du relevé aux paiements par carte des tickets Z du mois ;
- range le relevé dans `Banque/AAAA-MM` et l'ajoute, avec `rapprochement_AAAA-MM.csv`,
  au dossier Cegid du mois.

### Saisir les obligations légales

Onglet **Obligations** du tableur « Pizza Napoli — Agent » (créé au premier passage) :

| Libellé | Échéance | Récurrence | Notes |
| --- | --- | --- | --- |
| Déclaration de TVA (CA3) | 19/11/2026 | mensuelle | impots.gouv.fr, espace professionnel |
| Cotisations URSSAF | 05/12/2026 | mensuelle | |
| Assurance multirisque | 01/03/2027 | annuelle | Contrat n° … |
| Formation hygiène HACCP (Paul) | 15/06/2027 | unique | |

Récurrence : `unique`, `mensuelle`, `trimestrielle`, `semestrielle` ou `annuelle`.
Date au format JJ/MM/AAAA. L'agent remplit lui-même la colonne « Agenda ».

## Installation (une seule fois)

### 1. Clé Claude

1. Sur [console.anthropic.com](https://console.anthropic.com), crée une clé API.
2. Dans **Limits**, fixe une limite de dépense mensuelle (par exemple 20 $).

### 2. Accès Google au compte de la pizzeria

1. Sur [console.cloud.google.com](https://console.cloud.google.com), connecté avec carpentraspizzanapoli@gmail.com, crée un projet « Agent Pizza Napoli ».
2. **APIs et services > Bibliothèque** : active Gmail API, Google Drive API, Google Sheets API et Google Calendar API.
3. **Écran de consentement OAuth** : type « Externe », ajoute carpentraspizzanapoli@gmail.com comme utilisateur, puis clique sur **Publier l'application**. Sans cette publication, Google coupe l'accès au bout de 7 jours.
4. **Identifiants > Créer > ID client OAuth**, type « Application de bureau ». Télécharge le fichier JSON.
5. Sur ton ordinateur :

   ```bash
   pip install google-auth-oauthlib
   ```

   ```bash
   python autoriser_google.py client_secret_XXXX.json
   ```

   Connecte-toi avec carpentraspizzanapoli@gmail.com. Google affiche « application non validée » : clique sur « Paramètres avancés », puis « Accéder à Agent Pizza Napoli ». Le script affiche trois valeurs.

### 3. Réglages GitHub

Dans le dépôt : **Settings > Secrets and variables > Actions**.

Secrets (onglet *Secrets*) :

| Nom | Valeur |
| --- | --- |
| `ANTHROPIC_API_KEY` | la clé de l'étape 1 |
| `GOOGLE_CLIENT_ID` | affiché par le script |
| `GOOGLE_CLIENT_SECRET` | affiché par le script |
| `GOOGLE_REFRESH_TOKEN` | affiché par le script |

Variables (onglet *Variables*) :

| Nom | Exemple | Rôle |
| --- | --- | --- |
| `GERANTS_EMAILS` | `toi@gmail.com,associe@gmail.com` | destinataires du rapport |
| `JOURS_FERMES` | `0` | jours sans Z attendu (0 = lundi … 6 = dimanche) |
| `JOURS_HISTORIQUE` | `30` | au tout premier passage, profondeur de tri ; remettre `3` ensuite |
| `LIBELLE_Z` / `LIBELLE_FACTURES` | `Ticket Z` / `Factures` | vos libellés pour les Z et les factures, s'ils portent un autre nom |
| `AGENT_NAPOLI_ACTIF` | `true` | **interrupteur** : tout autre valeur arrête l'agent |

### 4. Essai à blanc

1. Mets `AGENT_NAPOLI_ACTIF` à `true`.
2. Onglet **Actions > Agent Pizza Napoli (rapport de 9h) > Run workflow**, mode `essai`.
3. L'agent lit tout mais ne modifie rien : ni libellé, ni brouillon, ni fichier, ni tableur. Il envoie seulement le rapport aux gérants, avec « [ESSAI] » dans l'objet. Les appels à Claude, eux, ont bien lieu.

Si le rapport est correct, il n'y a plus rien à faire : le passage de 9h tourne tout seul.

## Arrêter l'agent

Variable `AGENT_NAPOLI_ACTIF` à `false`. Effet immédiat, plus aucun passage.

## Journal

Chaque action est inscrite dans l'onglet **Journal** du tableur.

Le dépôt GitHub est public, donc les logs des passages (onglet Actions) sont visibles
par tous. L'agent n'y écrit que le type d'action (« mails triés », « Z enregistré »),
jamais d'objet de mail, de nom de fournisseur ni de montant. En cas d'erreur, seul
l'emplacement dans le code est affiché.

## Coûts estimés (approximatifs)

- GitHub Actions : gratuit à ce volume (un passage de quelques minutes par jour).
- Claude (modèle `claude-opus-5-5`, effort réduit) : de l'ordre de 5 à 15 € par mois pour
  30 à 80 factures et 10 à 40 mails par jour. À vérifier sur la console Anthropic après
  un mois. Pour réduire encore, la variable `AGENT_MODELE` permet de choisir un modèle plus léger.

## Pour les développeurs

```bash
pip install -r requirements-dev.txt
```

```bash
python -m pytest -q
```

```bash
python -m agent_napoli --z tests/fixtures/z_2026-10-17.html "L'Addition - Votre Z quotidien (PIZZA NAPOLI CARPENTRAS | 2026-10-17)"
```

Modules : `z_laddition` (lecture du Z, contrôles), `caisse` (archivage, historique),
`tri_mails`, `factures`, `obligations`, `comptable`, `rapport`, `ia` (appels Claude),
`google_api` (Gmail, Drive, Sheets, Agenda), `__main__` (passage quotidien).
