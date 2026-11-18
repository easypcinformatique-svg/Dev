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

## La page de prospection

`annuaire-prospection-paca.html` réunit les organismes publics de la région dans
une seule liste, avec un filtre par type et par département, et le bouton de
copie des adresses. Elle est **assemblée à partir des deux annuaires**, qu'elle
relit plutôt que de dupliquer : une mise à jour hebdomadaire s'y propage à la
régénération suivante.

| Type | Nombre | Avec une adresse |
|------|--------|------------------|
| Communes | 97 | 89 |
| EPCI à fiscalité propre | 52 | 50 |
| Entreprises publiques locales | 110 | 25 |
| Syndicats (SIVU, SIVOM, SMF, SMO, PETR) | 190 | 0 |
| Départements | 6 | 1 |
| Région Sud | 1 | 0 |
| Bailleurs sociaux | 17 | 0 |
| Associations de 50 salariés et plus | 508 | 0 |

Les syndicats viennent de BANATIC, qui ne publie **ni adresse e-mail ni
téléphone** : ils arrivent avec leur nom, leur type, leur président, leur
commune de siège et la population desservie, mais sans contact direct. C'est une
limite de la source, pas une collecte incomplète.

47 syndicats sont écartés parce qu'ils desservent moins de 5 000 habitants avec
moins de 5 membres — des SIVU d'école ou d'eau entre deux communes, dont les
emprunts se comptent en dizaines de milliers d'euros. Les seuils sont les
constantes `SEUIL_POPULATION` et `SEUIL_MEMBRES` de `build_prospection.py`.

Les associations viennent de SIRENE, par l'API Recherche d'entreprises
(`collecte_associations_paca.py`). Trois choix de périmètre :

- **le siège doit être en PACA**. Le filtre régional de l'API retient toute
  association ayant un établissement dans la région : 269 sièges hors région
  (réseaux nationaux, le plus souvent parisiens) sont écartés, leur décideur
  n'étant pas sur place ;
- **50 salariés et plus**, d'après la tranche d'effectif de l'unité légale. Elle
  date de l'année affichée entre parenthèses (N-2 en général) : un ordre de
  grandeur, pas un effectif à jour. Le seuil est le second argument du script ;
- **le secteur est déduit du code NAF** et figure dans le type
  (« Association · Médico-social et social »). Le filtre par type propose une
  entrée « tous » par famille.

Ni SIRENE ni le Répertoire national des associations ne publient d'adresse
e-mail ou de téléphone : comme les syndicats, les associations arrivent sans
contact direct. Le lien « Fiche officielle » ouvre leur page de l'Annuaire des
entreprises (dirigeants déclarés, établissements, comptes publiés).

```bash
python3 annuaires/collecte_associations_paca.py /tmp/associations.json 50
python3 annuaires/build_prospection.py --associations /tmp/associations.json
```

Les familles dont la source n'est pas passée en argument sont reprises de la
page existante : régénérer les seules associations ne retire rien d'autre.

## Compléments de contacts

`enrichit_contacts.py` rebalaye les sources officielles et écrit
`contacts_complementaires.json`, que `build_prospection.py` applique à chaque
régénération sans jamais écraser une valeur déjà présente. Au 17/11/2026 la page
passe de 165 à 362 adresses e-mail et à 640 téléphones, sur 981 organismes.

| Source | Apporte | Rapprochement |
|--------|---------|---------------|
| BANATIC officiel (`banatic.interieur.gouv.fr`, export national) | courriel, téléphone, site des syndicats | nom et département |
| Annuaire de l'éducation | courriel, téléphone, site des associations gestionnaires d'établissements | SIREN |
| FINESS | téléphone des associations sanitaires et médico-sociales | SIREN |
| Site de l'organisme | courriel | site donné par une source, ou confirmé par le SIREN |

La phrase plus haut selon laquelle BANATIC ne publie ni e-mail ni téléphone vaut
pour la copie OpenDataSoft d'origine : l'export officiel porte ces colonnes, mais
toutes ne sont pas remplies (63 syndicats sur 190 ont un courriel).

`--cherche-sites` essaie des noms de domaine plausibles pour les organismes sans
site connu et ne retient un site que s'il affiche le SIREN de l'organisme.
Le Répertoire national des associations, qui porte un champ site web, n'est pas
téléchargeable par script (protection anti-robot du ministère).

```bash
python3 annuaires/enrichit_contacts.py CACHE --cherche-sites
python3 annuaires/build_prospection.py --associations CACHE/associations.json
```

## Balayage approfondi et dirigeants

`fouille_profonde.py` reprend chaque organisme sans adresse : il cherche son
site (sources, Wikidata, noms de domaine confirmés par le SIREN ou par le nom et
le code postal), puis lit les pages de contact et de mentions légales en
restituant les adresses masquées. Deux sources officielles complètent :

- les **avis du BOAMP** des deux dernières années, où l'acheteur publie son
  adresse de contact, rapprochée par SIRET. Le BOAMP écrit certains départements
  sans zéro initial (« 6 » pour « 06 ») : les deux graphies sont interrogées ;
- le **Journal officiel des associations**, dont les annonces portent le site
  déclaré par l'association (champ `siteweb`), rapproché par numéro RNA ou SIREN.

Les grands bailleurs sociaux et la plupart des grandes collectivités ne publient
aucune adresse : leur site ne propose qu'un formulaire.

La colonne « Dirigeants » vient de `dirigeants.json`, assemblé par
`assemble_dirigeants.py` : président et directeur général d'après le Registre
national des entreprises (`collecte_dirigeants.py`), présidents des syndicats et
des EPCI d'après BANATIC, maires d'après l'annuaire des maires. Les directeurs
financiers ne sont pas des mandataires sociaux : ils ne figurent que lorsque le
site de l'organisme publie son équipe de direction. Aucun nom ni aucune adresse
ne vient d'un réseau social, et aucune adresse n'est construite à partir d'un
nom.

Compléments de la colonne « Dirigeants » : `fonctions_sites.py` relève sur le
site de chaque organisme les noms qu'il publie (président, directeur général,
directeur, directeur financier, à défaut directeur de la publication), marqués
« (site) » dans la page ; les départements et la Région viennent de l'annuaire
de l'administration (président et directeur général des services). Un nom relevé
sur un site n'est pas repris pour une commune ni quand plusieurs organismes
partagent ce site. Le champ `president` de l'annuaire des Epl est rempli depuis
`dirigeants.json`.

## Clients

Une case « Client » en tête de ligne barre l'organisme. Elle est enregistrée
avec les commentaires, dans le navigateur, et suit la même sauvegarde. Le filtre
« Masquer les clients » ne laisse que les prospects.

## Commentaires

La page de prospection a une colonne « Commentaire », enregistrée dans le
navigateur (`localStorage`). Les commentaires ne sont donc ni publiés ni
partagés, et ne suivent pas d'un appareil à l'autre : « Sauvegarder mes
commentaires » en fait un fichier JSON que « Importer » recharge ailleurs. Ils
figurent dans les exports CSV et Excel.

Le bouton de copie déduplique : deux organismes partageant une adresse ne la
produisent qu'une fois, ce qui explique l'écart entre les 165 adresses
renseignées et les 163 copiées.

Un constat traverse tout le fichier : **plus l'organisme est gros, moins il
publie d'adresse**. Les quatre plus grandes villes, cinq départements sur six et
la Région renvoient vers un formulaire — dont le lien figure alors à la place de
l'adresse. Le filtre « seulement avec une adresse » permet de ne voir que ce qui
est directement adressable.

Les syndicats et bailleurs sociaux viennent de BANATIC, qui n'est pas exposé par
l'annuaire de l'administration ; le générateur les intègre dès que le fichier
est fourni en `--banatic`.

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

Le bouton « Copier les e-mails » place dans le presse-papier les adresses des
communes **actuellement affichées**, séparées par `; ` — le séparateur qu'attendent
Outlook, Thunderbird et Gmail dans un champ destinataires. Filtrer par
département avant de cliquer donne donc la liste de ce seul département. Le
message annonce combien de communes affichées n'ont pas d'adresse, pour que la
liste ne paraisse pas incomplète par erreur ; si le navigateur refuse la copie,
le texte s'affiche à sélectionner.

Sept communes ne publient aucun courriel dans l'annuaire officiel, dont les
quatre plus peuplées — Marseille, Nice, Toulon, Aix-en-Provence — qui passent
toutes par un formulaire. Vérifié sur leurs propres sites et non sur le seul
annuaire : Gignac-la-Nerthe, Roquebrune-Cap-Martin et Istres n'affichent bien
qu'un formulaire de contact. Avec Monaco, cela fait huit entrées dont le champ
`email` est vide ; le champ `contact` porte alors le formulaire de contact de
l'annuaire officiel, ou à défaut le site de la mairie, et la page affiche
« Formulaire de contact » à la place de l'adresse. Les 97 entrées ont donc une
voie de contact, sans qu'aucune adresse ait été devinée.
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
- **annuaire des maires** : exactement neuf clés, dans l'ordre `ville`, `pop`,
  `dept`, `region`, `maire`, `adresse`, `tel`, `email`, `contact`.
  `update-maires.yml` réécrit chaque entrée à partir de cette liste : une clé
  ajoutée ici sans l'être là-bas serait perdue à la première mise à jour. Les
  deux listes doivent rester identiques ;
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
