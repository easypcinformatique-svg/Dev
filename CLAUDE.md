# Règles de délégation

Le modèle principal est Haiku (rapide, économique). Il orchestre et délègue selon la difficulté de chaque étape plutôt que de tout faire lui-même.

## Sous-agents

| Sous-agent | Modèle | À utiliser pour |
|---|---|---|
| `simple` | Haiku | Recherche de fichiers, lecture, petites modifications mécaniques, formatage, questions factuelles courtes |
| `execution` | Sonnet | Implémentation de code, modifications sur plusieurs fichiers, lancement de commandes et de tests, une fois l'approche décidée |
| `raisonnement` | Opus | Décisions d'architecture, débogage difficile, revues critiques, analyses complexes en plusieurs étapes |

## Règles

1. Tâche simple et sans ambiguïté : la faire directement ou la confier à `simple`.
2. Tâche d'implémentation ou nécessitant des commandes et des tests : déléguer à `execution`.
3. Problème flou, difficile, ou avec des compromis à arbitrer : déléguer d'abord à `raisonnement` pour obtenir une approche, puis à `execution` pour l'appliquer.
4. En cas de doute entre deux niveaux, choisir le niveau le plus bas, puis escalader si le résultat est insuffisant ou si l'agent signale une difficulté.
5. Une même demande peut être découpée : chaque étape va au sous-agent qui lui correspond.
6. Avant une décision importante ou de déclarer une tâche terminée, consulter `/advisor`.
7. Dans le compte rendu final, indiquer quel sous-agent a traité chaque étape.
