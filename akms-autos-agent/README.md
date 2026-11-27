# Agent IA – AKMS AUTOS

Deux assistants IA pour le garage **AKMS AUTOS** (vente de véhicules d'occasion, entretien et réparation) :

1. **Assistant clients** : sur le site web (une ligne de code), il répond aux clients 24 h/24, présente le stock, prend les rendez-vous et collecte les demandes.
2. **Assistant de gestion** : page réservée à l'équipe (`/gestion`, protégée par code d'accès), pour piloter le garage en langage naturel.

## Ce que fait l'assistant clients

| Besoin client | Ce que fait l'assistant |
|---|---|
| « Vous êtes ouverts samedi ? », « Combien coûte une vidange ? » | Répond à partir de `config/garage.json` (horaires, adresse, prix indicatifs) |
| « Je cherche un diesel automatique à moins de 18 000 € » | Cherche dans le stock `data/vehicules.json` et présente les véhicules |
| « Je peux venir l'essayer ? », « RDV pour mes freins » | Propose des créneaux libres (horaires, durée de la prestation, nombre de postes) et enregistre le RDV « à confirmer » |
| « Combien vous reprenez ma 308 ? », devis, financement, rappel | Collecte les infos et transmet une demande à l'équipe |

Règles intégrées : aucune invention de prix ou de disponibilité, pas de prix ferme de reprise, pas de diagnostic définitif (avec un conseil de sécurité pour les pannes dangereuses), récapitulatif et accord du client avant tout enregistrement, aucune donnée bancaire demandée.

## Ce que fait l'assistant de gestion

Ouvrir `https://VOTRE-SERVEUR/gestion` et saisir le code d'accès (`AKMS_ADMIN_TOKEN`). Exemples de demandes :

| Domaine | Exemples |
|---|---|
| Tableau de bord | « Bilan de la semaine », « Combien de ventes ce mois-ci ? » (RDV par statut, demandes en attente, CA, remises, marge, valeur et ancienneté du stock) |
| Planning | « Planning de demain », « Confirme le RDV 12 », « Déplace le RDV 7 à jeudi 14 h », « Crée un RDV freinage samedi 9 h pour M. Martin 06… » |
| Demandes clients | « Quelles demandes de reprise sont à traiter ? », « Demande 5 : rappelé, offre 6 500 €, passe en cours » |
| Stock et ventes | « Ajoute une Clio 2019 TCe 90, 48 000 km, 11 900 €, achetée 9 000 € », « Baisse la 208 à 14 490 € », « Vends AK-003 à 16 500 € à M. Durand », « Quels véhicules sont en stock depuis plus de 60 jours ? » |
| Infos du garage | « Samedi on ferme désormais », « Nouveau numéro : 04… », « Vidange à partir de 95 € » |

Garde-fous :
- l'assistant récapitule et demande confirmation avant les ventes, les changements d'horaires et toute modification ambiguë ;
- chaque modification est inscrite au journal (`/admin/journal`) ;
- le prix d'achat et la marge restent internes et ne sont jamais montrés aux clients ;
- un véhicule vendu disparaît automatiquement de l'assistant clients, et les changements d'horaires ou de prix s'y appliquent aussitôt.

## Avant la mise en ligne

1. **Compléter `config/garage.json`** : remplacer tous les `[A COMPLETER]` (adresse, téléphone, email, site) et vérifier les horaires, les prestations et les prix.
2. **Remplacer `data/vehicules.json`** par le vrai stock : les 7 véhicules fournis sont des **exemples** (`"_exemple": true`). Mettre `"disponible": false` pour un véhicule vendu. Les deux fichiers sont relus à chaque message, sans redémarrage.
3. Copier `.env.example` en `.env` et renseigner `ANTHROPIC_API_KEY` et `AKMS_ADMIN_TOKEN`.

## Lancer

```bash
cd akms-autos-agent
pip install -r requirements.txt
export $(grep -v '^#' .env | xargs)
uvicorn server:app --port 8080
```

Ouvrir http://localhost:8080 : page de démonstration avec le chat ouvert.

Avec Docker :

```bash
docker build -t akms-agent akms-autos-agent
docker run -p 8080:8080 --env-file akms-autos-agent/.env -v akms-data:/data akms-agent
```

## Intégrer sur le site du garage

```html
<script src="https://VOTRE-SERVEUR/widget.js" defer></script>
```

Options : `data-couleur="#c8102e"` (couleur de la marque), `data-ouvert="true"` (ouvert au chargement), `data-api="https://..."` (si l'API est sur un autre domaine que le script). Ajoutez le domaine du site dans `AKMS_ALLOWED_ORIGINS`.

## Consulter les rendez-vous et demandes

```bash
curl -H "Authorization: Bearer $AKMS_ADMIN_TOKEN" https://VOTRE-SERVEUR/admin/rendez-vous
curl -H "Authorization: Bearer $AKMS_ADMIN_TOKEN" https://VOTRE-SERVEUR/admin/demandes
curl -H "Authorization: Bearer $AKMS_ADMIN_TOKEN" https://VOTRE-SERVEUR/admin/ventes
curl -H "Authorization: Bearer $AKMS_ADMIN_TOKEN" https://VOTRE-SERVEUR/admin/journal
```

Les données sont stockées dans SQLite (`data/akms.db`, ou `/data/akms.db` sous Docker).

## Technique

- `agent.py` : boucle d'agent Claude (modèle `claude-opus-5-5` par défaut, effort `medium`), mémoire de conversation par session (2 h), repli automatique côté serveur en cas de refus (`fallbacks: "default"`).
- `tools.py` : les 6 outils de l'assistant clients (schémas stricts) : `infos_garage`, `rechercher_vehicules`, `details_vehicule`, `creneaux_disponibles`, `prendre_rendez_vous`, `enregistrer_demande`.
- `gestion_tools.py` : les 12 outils de gestion (tableau de bord, planning, RDV, demandes, stock, ventes, infos, prestations). Les fichiers JSON sont réécrits de façon atomique.
- `server.py` : API FastAPI (`POST /api/chat`, `POST /api/gestion/chat` protégé par jeton, `/admin/*`), limitation à 20 messages/min par IP.
- `static/gestion.html` : interface de l'équipe (tableaux et listes mis en forme).
- `static/widget.js` : widget de chat autonome, sans dépendance.

Tests (sans appel à l'API) :

```bash
python -m pytest -q tests
```

## Pistes suivantes

- Facturation et devis PDF, suivi des paiements, export comptable.

- Brancher le stock sur l'export de votre logiciel ou de Leboncoin/La Centrale au lieu du JSON.
- Notifier le garage par email ou SMS à chaque nouveau RDV ou demande.
- Ajouter le canal WhatsApp (le dépôt contient déjà une intégration WhatsApp Business côté pizzeria, réutilisable).
