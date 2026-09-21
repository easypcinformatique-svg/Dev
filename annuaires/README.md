# Les deux annuaires

Deux pages autonomes publiées sur la branche `gh-pages` :

| Page | URL publique | Mise à jour |
|------|--------------|-------------|
| `annuaire-maires-france.html` | `/Dev/annuaire-maires-france.html` | `update-maires.yml` — lundi 06 h UTC |
| `annuaire-sem-spl-syndicats.html` | `/Dev/annuaire-sem-spl-syndicats.html` | `update-sem-spl-sm.yml` — mercredi 07 h UTC |

## Où vivent les données

`gh-pages` fait autorité : c'est la copie que les workflows hebdomadaires
lisent, enrichissent et repoussent. Les copies de `master` servent de semence
et de sauvegarde — elles sont forcément en retard sur la production dès la
première mise à jour réussie.

`publish-annuaires.yml` restaure sur `gh-pages` ce qui y manque, sans jamais
écraser la version en ligne (sauf appel manuel avec `force: true`). Il tourne
chaque lundi à 05 h UTC, avant les deux mises à jour, en filet de sécurité :
le 14/04/2026, un déploiement a recréé `gh-pages` à vide et emporté les deux
pages, laissant les sites en 404 et les mises à jour en échec pendant cinq mois.

## Format des données — à ne pas reformater

Les deux pages portent leurs données dans un tableau `let DATA = [ … ];` que
les workflows relisent et réécrivent. Les contraintes sont donc strictes :

- **une entrée par ligne** — les regex des workflows utilisent `.*?`, qui ne
  franchit pas un saut de ligne ; deux entrées sur une même ligne casseraient
  l'appariement ;
- **ordre des clés** pour l'annuaire des Epl : `nom` en tête, `siren` en
  dernier, `adresse`, `tel` et `president` entre les deux ;
- **pas de guillemet double ni d'antislash** dans les valeurs : les regex
  capturent avec `[^"]*` et `json.loads` refuse `\'`. Les apostrophes passent
  telles quelles, les guillemets doubles sont convertis à la génération.

## Regénérer l'annuaire des Epl

`annuaire-sem-spl-syndicats.html` est généré depuis l'export de l'annuaire
des Epl (`Export_Annuaire_23022026.xlsx`, 1506 structures) :

```bash
pip install openpyxl
python3 annuaires/build_sem_spl.py
```

Pour repartir d'un export plus récent : déposer le nouveau `.xlsx` à la racine,
ajuster `EXPORT` et `__EXPORT_DATE__` dans `build_sem_spl.py`, regénérer, puis
publier avec `publish-annuaires.yml` en `force: true` — ce qui écrase les
dirigeants et contacts collectés depuis ; les workflows les recollecteront.

L'annuaire des maires, lui, n'a pas de générateur : il est né à la main et
n'est plus modifié que par `update-maires.yml`.
