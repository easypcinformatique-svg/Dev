# Bot Telegram « questions à Karen » – installation (10 minutes)

## 1. Créer le bot (Telegram, 2 min)
1. Dans Telegram, ouvrez **@BotFather** et envoyez `/newbot`.
2. Nom : `AMKS Compta` ; identifiant : par ex. `amks_compta_bot` (doit finir par `bot`).
3. BotFather répond avec un **jeton** (ex. `123456:ABC…`). Gardez-le pour l'étape 3, **ne le partagez avec personne**.

## 2. Créer le script (Google, 3 min)
1. Ouvrez le Google Sheet « Journal import mails AMKS AUTOS » > **Extensions > Apps Script**
   (ou un nouveau projet sur script.google.com, avec le même compte Google).
2. Cliquez **+ > Script**, nommez-le `BotTelegram`, collez tout le contenu de `bot_telegram_karen.gs`, enregistrez.
3. **Paramètres du projet** (roue dentée) : fuseau horaire **(GMT+01:00) Paris**.

## 3. Mettre le jeton (1 min)
**Paramètres du projet > Propriétés du script > Ajouter** :
- Propriété : `TG_TOKEN`
- Valeur : le jeton donné par BotFather

## 4. Lancer (2 min)
1. Dans l'éditeur, choisissez la fonction **`installer`** et cliquez **Exécuter**.
2. Acceptez les autorisations (Sheet, Drive, accès Internet, déclencheurs).
3. Le journal affiche : `Bot @amks_compta_bot installé. … envoyez : /moi 1234`.

## 5. Brancher Robert et Karen (2 min)
1. **Robert** ouvre le bot dans Telegram et envoie `/moi 1234` (le code affiché).
2. **Karen** ouvre le bot et appuie sur **Démarrer**.
3. Robert reçoit « Est-ce Karen ? » et appuie sur **Oui, c'est Karen**.
4. Premier envoi le lendemain à 9 h, ou tout de suite avec `/envoyer`.

## Fonctionnement
- **9 h** : 3 questions « Priorités » (les plus lourdes en TVA) et 5 factures KAMS (boutons AMKS / KAMS).
- Karen **appuie longuement sur la question > Répondre**, et écrit ou envoie photo / PDF.
  Boutons « Je ne sais pas » et « Plus tard ». `/suite` pour la question suivante.
- Le bot écrit la réponse dans `Priorités` (colonnes K et L) ou `Factures KAMS 2024` (K et L),
  et range les pièces dans le dossier Drive **« Réponses Karen (Telegram) »**.
- **Robert est prévenu** quand : Karen ne sait pas, réponse trop courte, pièce attendue mais absente,
  pas de réponse 4 jours après un rappel, ou erreur du bot. Bilan chaque soir à 18 h.
- Commandes de Robert : `/etat`, `/envoyer`, `/pause`, `/reprise`.
- Arrêter le bot : exécuter la fonction `desinstaller`.

Réglages en haut du script : `PAR_JOUR`, `KAMS_PAR_JOUR`, `HEURE_ENVOI`, `HEURE_RELANCE`, `RELANCE_H`.
