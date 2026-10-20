# Suivi des alertes — Z quotidien L'Addition

Extrait, jour par jour, les 4 indicateurs d'anomalie des mails
« L'Addition - Votre Z quotidien » (`noreply@laddition.com`) pour
PIZZA NAPOLI CARPENTRAS.

## Indicateurs suivis

1. Corrections **avant** envoi en cuisine
2. Corrections **après** envoi en cuisine
3. Annulations cuisine **après** ticket de caisse / fermeture de commande
4. **Offerts**, rapportés au CA TTC de la soirée

## Utilisation

Déposer un fichier `.txt` par journée dans `data/` (copier-coller brut du mail,
le nom du fichier est libre : la date est lue dans le corps), puis :

```bash
python3 parse_z.py
```

Produit `z_daily.csv` (séparateur `;`, ouvrable dans Excel) et
`rapport_z.html` (tableau + tuiles de synthèse, lisible en thème clair et sombre).

## Seuils d'alerte

Définis en haut de `parse_z.py`, en % du CA TTC :

| Indicateur | Seuil |
|---|---|
| Corrections avant cuisine | 5 % |
| Corrections après cuisine | 2 % |
| Annulations après ticket | 2 % |
| Offerts | 3 % |

## Limites connues

- Le Z ne donne **pas** le nombre de tickets : il est reconstruit par
  `CA TTC / ticket moyen`. Valeur approchée.
- Les couverts ne sont pas saisis en caisse (`Couvert(s) : 0.00`), donc le
  panier moyen du Z est inexploitable.
- Le détail des ventes ne montre que les articles **entièrement** offerts
  (TTC à 0,00). Les offerts partiels n'y figurent pas : seul l'« Export des
  annulations » du mail les détaille, et son lien n'est valable que **24 h**.
