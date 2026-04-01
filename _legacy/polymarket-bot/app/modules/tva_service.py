"""Module de calcul et reporting TVA.

Gère :
- Le calcul de la TVA déductible par période
- Le résumé pour la déclaration de TVA
- L'export des données
"""

from datetime import date

from sqlalchemy import func

from app.models import Facture, db


class TVAService:
    """Service de calcul TVA pour la déclaration."""

    # Taux de TVA en France
    TAUX_TVA = {
        "normal": 20.0,
        "intermediaire": 10.0,
        "reduit": 5.5,
        "super_reduit": 2.1,
    }

    def resume_periode(self, periode: str) -> dict:
        """Calcule le résumé TVA pour une période donnée.

        Args:
            periode: Format "YYYY-MM" (ex: "2024-03")

        Returns:
            Dict avec le résumé TVA
        """
        factures = Facture.query.filter(
            Facture.periode_tva == periode,
            Facture.statut.in_(["validee", "payee"]),
        ).all()

        # Regrouper par taux de TVA
        par_taux = {}
        total_ht = 0.0
        total_tva = 0.0
        total_ttc = 0.0

        for f in factures:
            taux = f.taux_tva or 20.0
            taux_key = str(taux)

            if taux_key not in par_taux:
                par_taux[taux_key] = {
                    "taux": taux,
                    "base_ht": 0.0,
                    "montant_tva": 0.0,
                    "nb_factures": 0,
                }

            par_taux[taux_key]["base_ht"] += f.montant_ht or 0
            par_taux[taux_key]["montant_tva"] += f.montant_tva or 0
            par_taux[taux_key]["nb_factures"] += 1

            total_ht += f.montant_ht or 0
            total_tva += f.montant_tva or 0
            total_ttc += f.montant_ttc or 0

        return {
            "periode": periode,
            "par_taux": par_taux,
            "total_ht": round(total_ht, 2),
            "total_tva": round(total_tva, 2),
            "total_ttc": round(total_ttc, 2),
            "nb_factures": len(factures),
            "nb_a_verifier": Facture.query.filter(
                Facture.periode_tva == periode, Facture.statut == "a_verifier"
            ).count(),
        }

    def resume_annuel(self, annee: int) -> dict:
        """Calcule le résumé TVA annuel.

        Args:
            annee: Année (ex: 2024)

        Returns:
            Dict avec le résumé annuel
        """
        mois = []
        total_ht = 0.0
        total_tva = 0.0

        for m in range(1, 13):
            periode = f"{annee}-{m:02d}"
            resume = self.resume_periode(periode)
            mois.append(resume)
            total_ht += resume["total_ht"]
            total_tva += resume["total_tva"]

        return {
            "annee": annee,
            "mois": mois,
            "total_ht": round(total_ht, 2),
            "total_tva": round(total_tva, 2),
            "total_ttc": round(total_ht + total_tva, 2),
        }

    def factures_non_classees(self) -> list:
        """Retourne les factures sans période TVA assignée."""
        return Facture.query.filter(
            Facture.periode_tva.is_(None),
            Facture.statut != "archivee",
        ).all()

    def statistiques_fournisseurs(self, periode: str = None) -> list:
        """Statistiques par fournisseur pour une période.

        Args:
            periode: Format "YYYY-MM" (optionnel, toutes périodes si None)

        Returns:
            Liste de dicts avec stats par fournisseur
        """
        query = db.session.query(
            Facture.fournisseur_nom,
            func.count(Facture.id).label("nb_factures"),
            func.sum(Facture.montant_ht).label("total_ht"),
            func.sum(Facture.montant_tva).label("total_tva"),
            func.sum(Facture.montant_ttc).label("total_ttc"),
        ).filter(Facture.statut.in_(["validee", "payee"]))

        if periode:
            query = query.filter(Facture.periode_tva == periode)

        query = query.group_by(Facture.fournisseur_nom)
        results = query.all()

        return [
            {
                "fournisseur": r.fournisseur_nom,
                "nb_factures": r.nb_factures,
                "total_ht": round(r.total_ht or 0, 2),
                "total_tva": round(r.total_tva or 0, 2),
                "total_ttc": round(r.total_ttc or 0, 2),
            }
            for r in results
        ]

    def export_csv(self, periode: str) -> str:
        """Exporte les factures d'une période en CSV.

        Args:
            periode: Format "YYYY-MM"

        Returns:
            Contenu CSV
        """
        factures = Facture.query.filter(
            Facture.periode_tva == periode,
        ).order_by(Facture.date_facture).all()

        lignes = [
            "Numéro;Fournisseur;Date;Montant HT;TVA;Taux TVA;Montant TTC;Statut"
        ]

        for f in factures:
            date_str = f.date_facture.strftime("%d/%m/%Y") if f.date_facture else ""
            lignes.append(
                f"{f.numero or ''};{f.fournisseur_nom or ''};"
                f"{date_str};{f.montant_ht:.2f};{f.montant_tva:.2f};"
                f"{f.taux_tva:.1f};{f.montant_ttc:.2f};{f.statut}"
            )

        return "\n".join(lignes)
