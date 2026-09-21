# Les deux annuaires

Deux pages autonomes publiées sur la branche `gh-pages`, toutes deux limitées à
**Provence-Alpes-Côte d'Azur** :

| Page | URL publique | Contenu | Mise à jour |
|------|--------------|---------|-------------|
| `annuaire-maires-france.html` | `/Dev/annuaire-maires-france.html` | 96 communes PACA de plus de 10 000 hab. + Monaco | `update-maires.yml` — lundi 06 h UTC |
| `annuaire-sem-spl-syndicats.html` | `/Dev/annuaire-sem-spl-syndicats.html` | 110 entreprises publiques locales de PACA | `update-sem-spl-sm.yml` — mercredi 07 h UTC |

Les deux offrent le même filtre par département, avec une entrée « toute la
région PACA ». Monaco n'est pas en PACA — c'est un État souverain frontalier du
06 — et figure à part dans le filtre de l'annuaire des maires.

Le seuil de population de l'annuaire des maires est la constante `SEUIL` de
`build_maires_paca.py`, que `codes_paca.py` importe : le changer d'un côté
suffit, et les deux scripts ne peuvent pas diverger.

## Sources

Toutes officielles, aucune donnée générée :

- **Populations** — INSEE, populations de référence 2023, authentifiées par le
  décret du 26 décembre 2025, en vigueur au 1er janvier 2026.
  Deux pièges de ce fichier, tous deux traités par le générateur :
  sa feuille « Communes » éclate Paris, Lyon et Marseille en arrondissements
  municipaux et **ne contient pas** les communes elles-mêmes (Marseille est
  reconstituée par la somme de ses arrondissements) ; et l'article élidé y est
  suivi d'une espace — « L' Isle-sur-la-Sorgue » — sur 81 communes, graphie que
  le RNE n'emploie pas et qui empêcherait donc toute mise à jour de
  celles-là.
- **Maires** — Répertoire National des Élus, audité contre les résultats
  officiels du second tour des municipales 2026.
- **Coordonnées des mairies** — Annuaire de l'administration (DILA),
  `api-lannuaire.service-public.fr`.
- **Monaco** — recensement IMSEE 2023 (38 367 habitants) et site officiel de la
  Mairie. Aucun courriel n'est publié sur sa page de contact : le champ reste
  vide plutôt que d'emprunter celui d'un annuaire tiers.
- **Entreprises publiques locales** — export de l'annuaire des Epl
  (`Export_Annuaire_23022026.xlsx`), filtré sur la région.

## Où vivent les données

`gh-pages` fait autorité : c'est la copie que les workflows hebdomadaires
lisent, enrichissent et repoussent. Les copies de `master` servent de semence et
de sauvegarde — elles sont en retard sur la production dès la première mise à
jour réussie.

`publish-annuaires.yml` restaure sur `gh-pages` ce qui y manque, sans jamais
écraser la version en ligne (sauf appel manuel avec `force: true`). Il tourne
chaque lundi à 05 h UTC, avant les deux mises à jour, en filet de sécurité : le
14/04/2026, un déploiement a recréé `gh-pages` à vide et emporté les deux pages,
laissant les sites en 404 et les mises à jour en échec pendant cinq mois.

## Format des données — à ne pas reformater

Les deux pages portent leurs données dans un tableau `let DATA = [ … ];` que les
workflows relisent et réécrivent. Les contraintes sont donc strictes :

- **une entrée par ligne** — les regex des workflows utilisent `.*?`, qui ne
  franchit pas un saut de ligne ;
- **annuaire des maires** : exactement huit clés, dans l'ordre `ville`, `pop`,
  `dept`, `region`, `maire`, `adresse`, `tel`, `email`. `update-maires.yml`
  réécrit chaque entrée à partir de cette liste : toute clé ajoutée serait
  perdue à la première mise à jour ;
- **annuaire des Epl** : `nom` en tête, `siren` en dernier, `adresse`, `tel` et
  `president` entre les deux. Ce workflow-là ne réécrit que les entrées qu'il
  modifie, donc les clés supplémentaires y survivent ;
- **pas de guillemet double ni d'antislash** dans les valeurs : les regex
  capturent avec `[^"]*` et `json.loads` refuse `\'`. Les apostrophes passent
  telles quelles, les guillemets doubles sont convertis à la génération.

## Regénérer

```bash
pip install openpyxl
bash annuaires/fetch_sources.sh          # sources officielles -> annuaires/cache/
python3 annuaires/build_maires_paca.py   # annuaire des maires
python3 annuaires/build_sem_spl.py       # annuaire des Epl
```

`build_maires_paca.py` ne remplace que le bloc `DATA` de la page ; la mise en
page, les filtres et les exports vivent dans le fichier HTML lui-même.
`build_sem_spl.py`, lui, régénère toute la page depuis
`annuaires/template_sem_spl.html`.

Pour repartir d'un export Epl plus récent : déposer le nouveau `.xlsx` à la
racine, ajuster `EXPORT` et `__EXPORT_DATE__` dans `build_sem_spl.py`,
regénérer, puis publier avec `publish-annuaires.yml` en `force: true` — ce qui
écrase les dirigeants et contacts collectés depuis ; les workflows les
recollecteront.
