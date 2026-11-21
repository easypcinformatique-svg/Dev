# Alerte loyers

Chaque mois, ce programme lit les virements reçus sur tes comptes bancaires, en lecture seule via
[Enable Banking](https://enablebanking.com). Il vérifie ensuite que chaque loyer est arrivé et
t'envoie le résultat **par e-mail** et **en notification sur ton téléphone** (application ntfy).

| Quand | Ce qui est envoyé |
|---|---|
| Le **10** du mois, vers 9h | Récapitulatif complet : ✅ reçu, ⚠️ partiel (avec le montant qui manque), ❌ rien reçu |
| Le **15** du mois, vers 9h | Rappel, **seulement** si un loyer manque encore |
| À tout moment | 🚨 si l'accès bancaire a expiré, ou 🔑 15 jours avant son expiration |

Le système gère aussi les deux cas suivants :

- **Loyer en plusieurs fois** : les virements du même payeur sont additionnés sur le mois.
- **CAF + complément** : un même bien peut avoir plusieurs payeurs.

> **Le dépôt est public.** Les noms des locataires, les montants et les accès ne sont jamais écrits
> dans le code : ils vivent dans les *secrets* GitHub. Les logs n'affichent que « 3/4 loyers reçus ».

---

## Mise en place (une seule fois)

### 1. Créer l'application Enable Banking

1. Crée un compte sur le [panneau de contrôle Enable Banking](https://enablebanking.com/cp/).
2. *Applications* → *Add a new application* :
   - Environnement : **Production**
   - Nom : `Alerte loyers`
   - Redirect URL : `https://enablebanking.com/`
   - Clé : choisis la génération dans le navigateur. Un fichier **`<identifiant>.pem`** se
     télécharge. Garde-le précieusement : c'est la clé privée.
3. Sur l'application créée, clique sur **Activate by linking accounts** et relie tes comptes
   **Crédit Mutuel** : le compte courant personnel et le compte SCI Immo Renov.
   L'application passe alors en mode *Restricted*. C'est normal : elle ne voit que tes propres comptes.

> ⚠️ D'après les conditions d'Enable Banking, la formule gratuite est réservée à l'usage personnel
> et exclut les comptes d'entreprise. Le compte **SCI Immo Renov** (loyer de la villa) peut donc
> être refusé ou demander un contrat payant. Les trois autres loyers arrivent sur ton compte
> personnel et ne sont pas concernés.

### 2. Autoriser l'accès à la banque

Sur un ordinateur qui a Python, dans ce dossier :

```bash
pip install -r requirements.txt
export EB_APP_ID="<identifiant de l'application>"
python connexion_banque.py --cle <identifiant>.pem banques --cherche mutuel
python connexion_banque.py --cle <identifiant>.pem debut --banque "<nom exact affiché>"
```

Ouvre le lien affiché et connecte-toi au Crédit Mutuel. À la fin, tu arrives sur une page
`https://enablebanking.com/?code=…` : copie toute l'adresse, puis lance :

```bash
python connexion_banque.py --cle <identifiant>.pem fin "<adresse copiée>"
```

Le script affiche l'**identifiant de session**, à mettre dans le secret `EB_SESSIONS`.
L'accès dure 180 jours au maximum. Tu recevras une alerte 🔑 15 jours avant la fin pour refaire
cette étape.

### 3. Notification sur le téléphone (ntfy)

1. Installe l'application **ntfy** (Play Store / App Store).
2. *+* → *Subscribe to topic* et choisis un nom long et impossible à deviner, par exemple
   `loyers-7f3k9q2x8m`. Ce nom sert de mot de passe : ne le partage pas.

### 4. Mot de passe d'application Gmail

1. La validation en deux étapes doit être activée sur ton compte Google.
2. Va sur <https://myaccount.google.com/apppasswords> et crée un mot de passe nommé
   `Alerte loyers`. Google affiche 16 lettres : c'est le secret `GMAIL_MOT_DE_PASSE_APPLI`.

### 5. Secrets GitHub

Sur GitHub, ouvre le dépôt puis *Settings* → *Secrets and variables* → *Actions* → *New repository secret* :

| Secret | Contenu |
|---|---|
| `EB_APP_ID` | Identifiant de l'application Enable Banking |
| `EB_CLE_PRIVEE` | Tout le contenu du fichier `.pem`, de `-----BEGIN` à `-----END…-----` |
| `EB_SESSIONS` | Identifiant(s) de session de l'étape 2, séparés par des virgules s'il y a plusieurs banques |
| `BAUX_JSON` | La liste de tes baux (voir ci-dessous) |
| `GMAIL_ADRESSE` | Ton adresse Gmail |
| `GMAIL_MOT_DE_PASSE_APPLI` | Le mot de passe d'application de l'étape 4 |
| `NTFY_SUJET` | Le nom du canal ntfy de l'étape 3 |
| `ALERTE_DESTINATAIRE` | *(facultatif)* une autre adresse qui doit recevoir l'e-mail |

Format de `BAUX_JSON` (même forme que [`baux.exemple.json`](baux.exemple.json)) :

```json
{"baux": [
  {"nom": "T2 SCI JGR", "montant": 800.00, "payeurs": ["NOM DU LOCATAIRE", "CAF"]}
]}
```

`payeurs` contient les mots cherchés dans le libellé du virement ou dans le nom de l'émetteur. La
recherche ignore les majuscules et les accents, et porte sur des mots entiers. Par défaut, un écart
de 1 € est toléré (`"tolerance": 1.00`).

### 6. Tester

*Actions* → *Alerte loyers* → *Run workflow*. Mets `2026-10` dans « Mois à vérifier » pour rejouer
octobre : tu dois recevoir l'e-mail et la notification.

---

## Fichiers

| Fichier | Rôle |
|---|---|
| `alerte_loyers.py` | Lit les comptes, rapproche, envoie e-mail + notification |
| `rapprochement.py` | Logique de rapprochement (sans réseau) |
| `enable_banking.py` | Client de l'API Enable Banking (lecture seule) |
| `connexion_banque.py` | Autorisation de l'accès bancaire (étape 2) |
| `test_rapprochement.py` | Tests : `python -m unittest -v` |
| `../.github/workflows/alerte-loyers.yml` | Planification le 10 et le 15 de chaque mois |
