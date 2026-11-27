# PORTAIL PL — INSTALLATION

Version prototype à déployer et tester avant usage réel. Créée pour 2 administrateurs (easypc.informatique@gmail.com et scognamiglio.julie@gmail.com) et 5 artisans. Base de données existante :
https://docs.google.com/spreadsheets/d/1yo7wxGTL28P_C0l7emcZRDn7Y-6XN7ljbNUOkW-DKAA/edit

Fichiers de ce dossier :

| Fichier | Projet Apps Script | Rôle |
|---|---|---|
| `Code_Admin.gs` | 1 — Administration | `Code.gs` de l'interface administrateur |
| `Index.html` | 1 — Administration | fichier HTML « Index » |
| `appsscript_admin.json` | 1 — Administration | manifeste (People API, web app « utilisateur accédant ») |
| `Code_Validation.gs` | 2 — Validation | `Code.gs` du service ALLOW/DENY |
| `appsscript_validation.json` | 2 — Validation | manifeste (web app « Moi » / « Tout le monde ») |

## 1. Ce qui existe déjà

- Google Sheets « Accès Portail PL — Autorisations artisans », avec les onglets « Artisans » et « Journal ».
- Julie a l'accès de modification.
- Les colonnes de l'onglet « Artisans » (ligne 1 = en-têtes, lignes 2 à 6 = 5 artisans) : A Nom · B Téléphone · C Début · D Fin · E De (HH:MM) · F À (HH:MM) · G Actif (OUI/NON) · H Note. L'application force B, E et F en texte brut ; si tu modifies le tableau à la main, garder des heures au format `08:00`.
- Le Galaxy Note9 avec SIM Free détecte les appels autorisés pour les propriétaires et commande le Shelly localement. **Ne pas modifier cette macro**.
- L'application d'administration et le service de validation fournis ici ne sont **pas encore publiés**.

## 2. Installer l'interface administrateur (projet 1)

1. Sur un ordinateur connecté au compte `easypc.informatique@gmail.com`, ouvrir le Google Sheets ci-dessus.
2. Menu **Extensions → Apps Script**. Donner au projet le nom « Portail PL — Administration ».
3. Remplacer le contenu de `Code.gs` par celui du fichier **Code_Admin.gs**.
4. Créer un fichier HTML intitulé exactement **Index**. Y coller le contenu de **Index.html**.
5. Dans les paramètres du projet, cocher « Afficher le fichier manifeste appsscript.json ».
6. Dans ce manifeste, coller **appsscript_admin.json**. Le service avancé `People` doit être activé ; le vérifier via **Services → + → People API v1** si nécessaire.
7. Enregistrer. Exécuter **getInitialState** depuis l'éditeur et autoriser Google Sheets, l'adresse e-mail et Google Contacts (lecture seule). Autoriser **primeContactsSearch** pour initialiser la recherche People.
8. Cliquer **Déployer → Nouveau déploiement → Application Web**. RÉGLAGES INDISPENSABLES :
   - **Exécuter en tant que** : *Utilisateur accédant à l'application* (pas « Moi »).
   - **Qui a accès** : *Toute personne possédant un compte Google* (connexion requise).
9. Copier le lien `/exec` vers ton téléphone et celui de Julie. Ouvrir dans Chrome ; chaque compte devra accepter ses propres autorisations d'accès à Google Sheets et aux contacts.
10. Sur Chrome Android : menu ⋮ → **Ajouter à l'écran d'accueil**.

**Confidentialité :** même si le déploiement est accessible à tout utilisateur Google, le script vérifie sur le serveur une liste fermée de **deux adresses e-mail** avant tout affichage, recherche, lecture ou modification. Une identité non disponible ou inconnue est refusée. Les contacts recherchés sont ceux du compte Google personnel connecté, pas nécessairement les mêmes pour toi et Julie. Les données d'autorisation sont communes.

## 3. Installer le service de validation des appels (projet 2)

1. Avec le compte **propriétaire** du Google Sheets, ouvrir https://script.google.com/home/projects et créer **un NOUVEAU projet indépendant** « Portail PL — Validation des appels » (ne pas utiliser le projet lié au tableau).
2. Coller **Code_Validation.gs** dans `Code.gs`.
3. Dans `appsscript.json`, coller **appsscript_validation.json** ; enregistrer.
4. Depuis l'éditeur, sélectionner la fonction **installerClePrivee**, appuyer sur **Exécuter**, autoriser le script. Copier localement la clé de 64 caractères affichée dans le journal d'exécution ; ne pas la copier dans le tableau et ne jamais la transmettre à ChatGPT.
5. **Déployer → Nouveau déploiement → Application Web** :
   - **Exécuter en tant que : Moi** (propriétaire du tableur).
   - **Qui a accès : Tout le monde** (appel machine-à-machine du Note9, sans compte Google).
6. Copier le lien HTTPS se terminant par `/exec` sur le Note9.

Ce point de terminaison est public mais ne renvoie que `ALLOW` ou `DENY` et exige la clé secrète dans le corps de la requête HTTPS. Il n'expose aucune donnée du tableau et ne commande aucun relais. L'API n'offre aucune commande d'ajout/suppression d'utilisateur, uniquement une validation à usage de la macro. Le risque de compromission d'une clé placée sur le téléphone n'est pas nul ; garder le Note9 verrouillé et à jour.

## 4. Ajouter une **nouvelle macro** « Accès artisans » dans MacroDroid

**Ne pas modifier la macro qui fonctionne pour toi et Julie.**

Déclencheur : **Appel entrant → Tout numéro**. La nouvelle macro concerne les artisans ; elle doit *obligatoirement* vérifier la réponse du serveur avant d'exécuter la commande Shelly.

Actions dans cet ordre :

1. Effacer la variable texte MacroDroid `REPONSE_ACCES` et la mettre à `DENY` avant chaque appel.
2. Action **Requête HTTP** vers le lien `/exec` de l'application de validation :
   - Méthode `POST`, type de contenu `application/json`.
   - Corps de la requête (remplacer `COLLER_CLE_PRIVEE_SUR_NOTE9` seulement sur le téléphone) :
     `{"token":"COLLER_CLE_PRIVEE_SUR_NOTE9","phone":"{call_number}"}`
   - Enregistrer la réponse texte dans la variable `REPONSE_ACCES`.
   - **Bloquer les actions suivantes jusqu'à la fin** de la requête et gérer un délai d'attente raisonnable (ex : 10 s). Si la requête échoue, laisser `DENY`.
3. Action de type **SI** : `REPONSE_ACCES` **est exactement égale à** `ALLOW` (pas `contient`).
4. **À l'intérieur de ce SI uniquement**, requête HTTP locale GET vers `http://192.168.1.31/rpc/Switch.Set?id=0&on=true&toggle_after=1`.
5. Fin SI. Tous les autres résultats, erreurs et expirations **ne font rien**.

Vérifier dans le journal MacroDroid que la réponse est exactement `ALLOW` pour un numéro actif et `DENY` pour les autres. La réponse ContentService de Google peut rediriger vers `script.googleusercontent.com` ; vérifier que MacroDroid suit la redirection HTTPS. Ne jamais tester la commande Switch.Set dans Chrome ou avec le portail non surveillé.

**Important :** dans MacroDroid, empêcher les exécutions simultanées de la macro artisans si l'option est proposée, et utiliser une variable locale ou réinitialisée à chaque appel pour éviter la réutilisation d'un ancien `ALLOW`. Le serveur impose un délai minimum de 25 secondes entre deux ouvertures d'un même numéro par cette macro.

## 5. Tests obligatoires avant activation

1. Ajouter un artisan dans l'application avec un vrai numéro, `Actif = NON`. Appel de l'artisan : réponse DENY, aucune ouverture.
2. Activer l'artisan dans l'application avec dates/horaires valides. Test **portail dégagé et sous surveillance** : autorisation attendue, impulsion de 1 seconde.
3. Mettre `Actif = NON` : nouvel appel refusé (attendre au moins 25 s entre deux essais).
4. Tester avant 08:00/après 20:00 avec un créneau de test temporaire et vérifier le refus.
5. Tester la date expirée, un numéro inconnu, un numéro masqué, le Wi-Fi coupé, Google Sheets indisponible, le téléphone verrouillé et le redémarrage du Note9.
6. Vérifier depuis le compte Julie que les changements sont bien partagés. Vérifier l'onglet « Journal ».
7. Vérifier les sécurités du portail : photocellules, absence de personne dans la trajectoire, fermeture automatique normale et arrêt en cas d'obstacle. Ne pas contourner les sécurités.

## Limites importantes

- Le numéro appelant est vulnérable à l'usurpation (caller-ID spoofing). Une reconnaissance par numéro seul ne constitue pas une authentification forte : considérer un code secondaire si l'accès est sensible.
- Le téléphone doit rester alimenté, relié au réseau mobile et au Wi-Fi local. Une défaillance Internet/Google doit entraîner un **refus**.
- L'interface d'administration est une Google Apps Script Web App ; elle recherche **Google Contacts via People API**, sans utiliser le sélecteur Android natif (indisponible de façon fiable dans le cadre HTML iframe Apps Script).
- L'application exige des étapes manuelles d'autorisation et de déploiement Google. Aucune URL de service final n'est disponible tant qu'elles ne sont pas réalisées.
- Pas de promesse de sécurité absolue : des tests réels et une revue de la configuration sont nécessaires avant usage non surveillé.
- Ne pas transmettre les secrets de l'API ni les numéros d'artisans dans des captures publiques.
