# Guide Complet : Publier une Application sur Google Play Store

## Table des Matieres

1. [Prerequisites](#1-prerequisites)
2. [Creer un compte Google Play Developer](#2-creer-un-compte-google-play-developer)
3. [Preparer l'application](#3-preparer-lapplication)
4. [Configurer la fiche Google Play Store](#4-configurer-la-fiche-google-play-store)
5. [Generer le fichier de release (APK / AAB)](#5-generer-le-fichier-de-release-apk--aab)
6. [Signer l'application](#6-signer-lapplication)
7. [Telecharger l'application sur Google Play Console](#7-telecharger-lapplication-sur-google-play-console)
8. [Configurer les tests (Alpha / Beta / Production)](#8-configurer-les-tests-alpha--beta--production)
9. [Soumettre pour examen](#9-soumettre-pour-examen)
10. [Post-publication et maintenance](#10-post-publication-et-maintenance)

---

## 1. Prerequisites

Avant de commencer, assurez-vous d'avoir :

| Element | Description |
|---------|-------------|
| **Compte Google** | Un compte Gmail valide |
| **Frais d'inscription** | 25 USD (paiement unique, a vie) |
| **Application fonctionnelle** | Votre app testee et prete a la mise en production |
| **Android Studio** | Derniere version installee |
| **Materiel graphique** | Icones, captures d'ecran, banniere promotionnelle |
| **Politique de confidentialite** | URL vers votre politique de confidentialite en ligne |

---

## 2. Creer un compte Google Play Developer

### Etape 2.1 : Inscription

1. Rendez-vous sur [Google Play Console](https://play.google.com/console/signup)
2. Connectez-vous avec votre compte Google
3. Acceptez le **Contrat de distribution pour les developpeurs**
4. Payez les **25 USD** de frais d'inscription (paiement unique)
5. Remplissez les informations de votre profil developpeur :
   - Nom du developpeur (visible publiquement)
   - Adresse e-mail de contact
   - Numero de telephone
   - Adresse physique (obligatoire depuis 2023)

### Etape 2.2 : Verification d'identite

Depuis 2023, Google exige une **verification d'identite** :

- **Compte personnel** : Piece d'identite + selfie de verification
- **Compte organisation** : Numero D-U-N-S ou documents d'entreprise

> **Delai** : La verification peut prendre de **48 heures a 2 semaines**.

---

## 3. Preparer l'application

### 3.1 Configuration du fichier `build.gradle`

```groovy
android {
    namespace "com.votreentreprise.votreapp"
    compileSdk 34

    defaultConfig {
        applicationId "com.votreentreprise.votreapp"
        minSdk 24
        targetSdk 34
        versionCode 1
        versionName "1.0.0"
    }
}
```

#### Points importants :

| Parametre | Regles |
|-----------|--------|
| `applicationId` | Doit etre **unique** sur tout le Play Store. Format reverse domain : `com.entreprise.app` |
| `versionCode` | Entier qui **doit augmenter** a chaque mise a jour |
| `versionName` | Version lisible par l'utilisateur (ex: `1.0.0`) |
| `minSdk` | SDK Android minimum supporte (24 = Android 7.0) |
| `targetSdk` | Doit cibler le dernier SDK requis par Google (actuellement SDK 34) |

### 3.2 Permissions Android

Verifiez le fichier `AndroidManifest.xml` :

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <!-- Ne demandez QUE les permissions necessaires -->
    <uses-permission android:name="android.permission.INTERNET" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:theme="@style/AppTheme">
        <!-- ... -->
    </application>
</manifest>
```

> **Regle d'or** : Ne demandez que les permissions **strictement necessaires**. Google rejette les applications qui demandent des permissions excessives.

### 3.3 Cas specifique : Application Web (PWA / TWA)

Si votre application est une **application web** (comme PizzaCaisse avec React), vous avez plusieurs options pour la publier sur Google Play :

#### Option A : Trusted Web Activity (TWA)

La TWA permet d'encapsuler votre application web dans une coquille Android native.

```bash
# Installer Bubblewrap (outil Google pour creer des TWA)
npm install -g @nicepkg/gp-publish
npm install -g @nicepkg/gp-publish
npx @nicepkg/gp-publish init
```

Ou utilisez **Bubblewrap** :

```bash
npm i -g @nicepkg/gp-publish
npx bubblewrap init --manifest https://votre-app.com/manifest.json
npx bubblewrap build
```

#### Option B : Capacitor (Ionic)

```bash
# Installer Capacitor
npm install @capacitor/core @capacitor/cli
npx cap init

# Ajouter la plateforme Android
npx cap add android

# Synchroniser le code web
npx cap sync

# Ouvrir dans Android Studio
npx cap open android
```

#### Option C : React Native / Expo (reecriture)

Pour une experience native complete, reecrire avec React Native ou Expo.

---

## 4. Configurer la fiche Google Play Store

### 4.1 Informations de base

Dans la Google Play Console, creez une nouvelle application et remplissez :

| Champ | Description | Exemple |
|-------|-------------|---------|
| **Nom de l'application** | Max 30 caracteres | `PizzaCaisse - Caisse POS` |
| **Description courte** | Max 80 caracteres | `Logiciel de caisse pour pizzerias et restaurants` |
| **Description complete** | Max 4000 caracteres | Description detaillee avec fonctionnalites |
| **Categorie** | Categorie du Play Store | `Professionnel` ou `Outils` |
| **Langue par defaut** | Langue principale | `Francais (France)` |

### 4.2 Elements graphiques obligatoires

| Element | Dimensions | Format |
|---------|-----------|--------|
| **Icone de l'application** | 512 x 512 px | PNG 32 bits (avec alpha) |
| **Banniere** | 1024 x 500 px | JPG ou PNG 24 bits |
| **Captures d'ecran telephone** | Min 2 (max 8) - 16:9 ou 9:16 | JPG ou PNG, min 320px, max 3840px |
| **Captures d'ecran tablette 7"** | Optionnel mais recommande | Memes specs |
| **Captures d'ecran tablette 10"** | Optionnel mais recommande | Memes specs |
| **Video promotionnelle** | Optionnel | URL YouTube |

> **Conseil** : Utilisez des **captures d'ecran avec des encadrements de telephone** (mockups) et du texte explicatif pour un meilleur impact visuel. Des outils comme Figma, Canva, ou [AppMockUp](https://app-mockup.com/) peuvent aider.

### 4.3 Classification du contenu

Vous devrez remplir le **questionnaire de classification IARC** :

1. Allez dans **Politique** > **Classification du contenu**
2. Repondez au questionnaire (type de contenu, violence, achats in-app, etc.)
3. Google attribuera automatiquement une classification (PEGI, ESRB, etc.)

### 4.4 Politique de confidentialite

- **Obligatoire** pour toutes les applications
- Doit etre hebergee sur une URL accessible publiquement
- Doit decrire quelles donnees sont collectees et comment elles sont utilisees
- Doit etre conforme au **RGPD** (si vous ciblez l'Europe)

### 4.5 Section Securite des donnees

Depuis 2022, Google exige une **declaration de securite des donnees** :

- Quelles donnees sont collectees (nom, email, localisation, etc.)
- Si les donnees sont partagees avec des tiers
- Les pratiques de securite (chiffrement, suppression des donnees)

---

## 5. Generer le fichier de release (APK / AAB)

### 5.1 Format AAB (recommande)

Depuis **aout 2021**, Google exige le format **Android App Bundle (.aab)** pour les nouvelles applications.

#### Avec Android Studio :

1. **Build** > **Generate Signed Bundle / APK**
2. Selectionnez **Android App Bundle**
3. Suivez l'assistant de signature (voir section 6)
4. Choisissez **release** comme variante de build
5. Le fichier `.aab` sera genere dans `app/build/outputs/bundle/release/`

#### En ligne de commande :

```bash
# Nettoyer le projet
./gradlew clean

# Generer le bundle de release
./gradlew bundleRelease
```

### 5.2 Format APK (legacy)

```bash
./gradlew assembleRelease
```

> Le fichier sera dans `app/build/outputs/apk/release/`

---

## 6. Signer l'application

### 6.1 Creer un keystore

```bash
keytool -genkey -v \
  -keystore mon-app-release-key.jks \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -alias mon-alias-de-cle
```

> **CRITIQUE** : Sauvegardez votre keystore et ses mots de passe en lieu sur. Si vous les perdez, vous ne pourrez **JAMAIS** mettre a jour votre application.

### 6.2 Configurer la signature dans `build.gradle`

```groovy
android {
    signingConfigs {
        release {
            storeFile file("mon-app-release-key.jks")
            storePassword System.getenv("KEYSTORE_PASSWORD")
            keyAlias "mon-alias-de-cle"
            keyPassword System.getenv("KEY_PASSWORD")
        }
    }

    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}
```

> **Securite** : Ne codez **jamais** les mots de passe en dur dans `build.gradle`. Utilisez des variables d'environnement ou un fichier `local.properties` (non versionne).

### 6.3 Google Play App Signing (recommande)

Google propose de gerer la cle de signature pour vous :

1. Dans Google Play Console > **Configuration** > **Integrite de l'application**
2. Activez **Play App Signing**
3. Avantages :
   - Google protege votre cle de signature
   - Possibilite de reinitialiser la cle d'upload si perdue
   - Optimisation automatique de la taille de l'APK

---

## 7. Telecharger l'application sur Google Play Console

### 7.1 Creer une release

1. Connectez-vous a [Google Play Console](https://play.google.com/console)
2. Selectionnez votre application
3. Allez dans **Production** > **Creer une release**
4. Telechargez votre fichier `.aab` (ou `.apk`)
5. Ajoutez les **notes de version** (changelog) en francais et autres langues

### 7.2 Notes de version (exemple)

```
Quoi de neuf dans la version 1.0.0 :

- Lancement initial de PizzaCaisse
- Gestion complete des commandes (sur place, a emporter, livraison)
- Interface de caisse intuitive et rapide
- Ecran cuisine en temps reel
- Suivi des livraisons avec attribution aux livreurs
- Commande en ligne avec paiement Stripe
- Tableaux de bord et statistiques detaillees
```

---

## 8. Configurer les tests (Alpha / Beta / Production)

Google Play propose **3 canaux de test** avant la production :

### 8.1 Test interne (recommande pour commencer)

| Parametre | Details |
|-----------|---------|
| **Nombre de testeurs** | Jusqu'a 100 |
| **Delai de mise a disposition** | Quelques minutes |
| **Examen Google** | Non requis |
| **Usage** | Tests internes de l'equipe |

### 8.2 Test ferme (Alpha)

| Parametre | Details |
|-----------|---------|
| **Nombre de testeurs** | Illimite (par email ou Google Groups) |
| **Delai de mise a disposition** | Quelques heures |
| **Examen Google** | Oui |
| **Usage** | Beta privee avec des utilisateurs selectionnes |

### 8.3 Test ouvert (Beta)

| Parametre | Details |
|-----------|---------|
| **Nombre de testeurs** | Illimite (tout le monde peut s'inscrire) |
| **Delai de mise a disposition** | Quelques heures |
| **Examen Google** | Oui |
| **Usage** | Beta publique avant le lancement officiel |

### 8.4 Workflow recommande

```
Test interne  -->  Test ferme (Alpha)  -->  Test ouvert (Beta)  -->  Production
   (equipe)        (testeurs de confiance)    (public limite)        (tout le monde)
```

> **Conseil** : Commencez **toujours** par le test interne. Cela vous permet de verifier que tout fonctionne sur le Play Store sans passer par l'examen Google.

---

## 9. Soumettre pour examen

### 9.1 Checklist pre-soumission

Avant de soumettre, verifiez :

- [ ] **Fiche Store** : Toutes les informations remplies (titre, description, captures)
- [ ] **Classification du contenu** : Questionnaire IARC complete
- [ ] **Politique de confidentialite** : URL valide et accessible
- [ ] **Section securite des donnees** : Declaration completee
- [ ] **Prix et distribution** : Gratuit ou payant, pays de distribution selectionnes
- [ ] **Ciblage par public** : Declarer si l'app est destinee aux enfants
- [ ] **Application signee** : Fichier AAB signe et uploade
- [ ] **Notes de version** : Changelog rempli
- [ ] **Coordonnees** : Email et telephone de contact renseignes
- [ ] **Publicites** : Declarer si l'app contient des publicites

### 9.2 Processus d'examen

1. Cliquez sur **Examiner la release** puis **Demarrer le deploiement en production**
2. Google examine votre application (verification manuelle et automatique)
3. **Delai d'examen** :
   - **Nouveau compte** : 1 a 7 jours (parfois plus)
   - **Compte existant** : Quelques heures a 3 jours
   - **Mise a jour** : Quelques heures a 1 jour

### 9.3 Motifs de rejet courants

| Motif | Solution |
|-------|----------|
| Politique de confidentialite manquante | Ajoutez une URL valide |
| Permissions excessives | Ne demandez que les permissions necessaires |
| Contenu trompeur | Assurez-vous que les captures correspondent a l'app |
| Bugs critiques | Testez sur plusieurs appareils |
| Violation de propriete intellectuelle | N'utilisez pas de marques deposees |
| Fonctionnalite de paiement non conforme | Utilisez le systeme de facturation Google Play pour les achats in-app |
| Ciblage enfants incorrect | Declarez correctement le public cible |

---

## 10. Post-publication et maintenance

### 10.1 Suivi des performances

Dans Google Play Console, surveillez :

- **Tableau de bord** : Installations, desinstallations, revenus
- **Notes et avis** : Repondez aux avis des utilisateurs
- **Android Vitals** : Taux de crash, ANR (Application Not Responding)
- **Rapports pre-lancement** : Tests automatiques sur appareils Firebase

### 10.2 Mises a jour regulieres

```bash
# Pour chaque mise a jour :
# 1. Incrementer versionCode dans build.gradle
# 2. Mettre a jour versionName
# 3. Generer un nouveau bundle signe
# 4. Uploader sur Google Play Console
# 5. Ajouter les notes de version
# 6. Deployer progressivement (rollout)
```

### 10.3 Deploiement progressif (Staged Rollout)

Google permet un deploiement progressif :

| Pourcentage | Usage |
|-------------|-------|
| **1%** | Test initial en production reelle |
| **5-10%** | Verification des metriques |
| **25-50%** | Extension progressive |
| **100%** | Deploiement complet |

> Cela permet de detecter les bugs en production avant de toucher tous les utilisateurs.

### 10.4 Conformite continue

- **Mise a jour du targetSdk** : Google exige de cibler les dernieres versions du SDK
- **Politique Play Store** : Surveillez les changements de politique de Google
- **Declaration des donnees** : Mettez a jour la section securite des donnees si vous changez vos pratiques

---

## Resume des etapes cles

```
1. Creer un compte Google Play Developer (25 USD)
        |
2. Verification d'identite (48h - 2 semaines)
        |
3. Preparer l'application (build.gradle, signature, permissions)
        |
4. Configurer la fiche Store (titre, description, captures, icone)
        |
5. Remplir les declarations (confidentialite, contenu, donnees)
        |
6. Generer le bundle signe (.aab)
        |
7. Uploader sur Google Play Console
        |
8. Tester (test interne -> ferme -> ouvert)
        |
9. Soumettre pour examen Google
        |
10. Publication ! (deploiement progressif recommande)
        |
11. Maintenance continue (mises a jour, avis, metriques)
```

---

## Ressources utiles

- [Documentation officielle Google Play Console](https://support.google.com/googleplay/android-developer)
- [Checklist de lancement Android](https://developer.android.com/distribute/best-practices/launch/launch-checklist)
- [Politique du programme pour les developpeurs](https://play.google.com/about/developer-content-policy/)
- [Guide des elements graphiques](https://developer.android.com/distribute/best-practices/launch/store-listing)
- [Android App Bundle](https://developer.android.com/guide/app-bundle)
- [Play App Signing](https://developer.android.com/studio/publish/app-signing)

---

> **Document cree le 12 avril 2026** | Guide pour PizzaCaisse et applications Android en general
