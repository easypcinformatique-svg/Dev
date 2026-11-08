# Agent IA – AKMS AUTOS

Assistant conversationnel pour le garage **AKMS AUTOS** (vente de véhicules d'occasion, entretien et réparation). Il s'intègre au site web avec une seule ligne de code et répond aux clients 24 h/24.

## Ce que fait l'agent

| Besoin client | Ce que fait l'assistant |
|---|---|
| « Vous êtes ouverts samedi ? », « Combien coûte une vidange ? » | Répond à partir de `config/garage.json` (horaires, adresse, prix indicatifs) |
| « Je cherche un diesel automatique à moins de 18 000 € » | Cherche dans le stock `data/vehicules.json` et présente les véhicules |
| « Je peux venir l'essayer ? », « RDV pour mes freins » | Propose des créneaux libres (horaires, durée de la prestation, nombre de postes) et enregistre le RDV « à confirmer » |
| « Combien vous reprenez ma 308 ? », devis, financement, rappel | Collecte les infos et transmet une demande à l'équipe |

Règles intégrées : aucune invention de prix ou de disponibilité, pas de prix ferme de reprise, pas de diagnostic définitif (avec un conseil de sécurité pour les pannes dangereuses), récapitulatif et accord du client avant tout enregistrement, aucune donnée bancaire demandée.

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
```

Les données sont stockées dans SQLite (`data/akms.db`, ou `/data/akms.db` sous Docker).

## Technique

- `agent.py` : boucle d'agent Claude (modèle `claude-opus-5-5` par défaut, effort `medium`), mémoire de conversation par session (2 h), repli automatique côté serveur en cas de refus (`fallbacks: "default"`).
- `tools.py` : les 6 outils métier (schémas stricts) : `infos_garage`, `rechercher_vehicules`, `details_vehicule`, `creneaux_disponibles`, `prendre_rendez_vous`, `enregistrer_demande`.
- `server.py` : API FastAPI (`POST /api/chat`, `POST /api/reset`, `/admin/*`), limitation à 20 messages/min par IP.
- `static/widget.js` : widget de chat autonome, sans dépendance.

Tests (sans appel à l'API) :

```bash
python -m pytest -q tests
```

## Pistes suivantes

- Brancher le stock sur l'export de votre logiciel ou de Leboncoin/La Centrale au lieu du JSON.
- Notifier le garage par email ou SMS à chaque nouveau RDV ou demande.
- Ajouter le canal WhatsApp (le dépôt contient déjà une intégration WhatsApp Business côté pizzeria, réutilisable).
