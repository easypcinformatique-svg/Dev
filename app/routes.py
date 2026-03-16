"""Routes principales de l'application."""

import os
from datetime import date, datetime, timezone

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from werkzeug.utils import secure_filename

from app.models import Facture, Fournisseur, ParametreTVA, SyncLog, db
from app.modules.auth_google import (
    get_flow,
    is_authenticated,
    load_credentials,
    save_credentials,
)
from app.modules.tva_service import TVAService

main = Blueprint("main", __name__)


# --- Dashboard ---


@main.route("/")
def dashboard():
    """Page d'accueil avec tableau de bord."""
    aujourd_hui = date.today()
    periode_courante = aujourd_hui.strftime("%Y-%m")

    # Statistiques générales
    total_factures = Facture.query.count()
    a_verifier = Facture.query.filter_by(statut="a_verifier").count()
    validees = Facture.query.filter_by(statut="validee").count()

    # Résumé TVA du mois
    tva_service = TVAService()
    resume_tva = tva_service.resume_periode(periode_courante)

    # Dernières factures importées
    dernieres = Facture.query.order_by(Facture.created_at.desc()).limit(10).all()

    # Dernières synchronisations
    derniers_logs = SyncLog.query.order_by(SyncLog.started_at.desc()).limit(5).all()

    return render_template(
        "dashboard.html",
        total_factures=total_factures,
        a_verifier=a_verifier,
        validees=validees,
        resume_tva=resume_tva,
        dernieres=dernieres,
        derniers_logs=derniers_logs,
        periode_courante=periode_courante,
        google_connecte=is_authenticated(),
    )


# --- Factures ---


@main.route("/factures")
def liste_factures():
    """Liste de toutes les factures avec filtres."""
    statut = request.args.get("statut", "")
    periode = request.args.get("periode", "")
    fournisseur = request.args.get("fournisseur", "")
    source = request.args.get("source", "")

    query = Facture.query

    if statut:
        query = query.filter_by(statut=statut)
    if periode:
        query = query.filter_by(periode_tva=periode)
    if fournisseur:
        query = query.filter(Facture.fournisseur_nom.ilike(f"%{fournisseur}%"))
    if source:
        query = query.filter_by(source=source)

    factures = query.order_by(Facture.created_at.desc()).all()

    return render_template(
        "factures.html",
        factures=factures,
        filtres={"statut": statut, "periode": periode, "fournisseur": fournisseur, "source": source},
    )


@main.route("/factures/<int:facture_id>")
def detail_facture(facture_id):
    """Détail d'une facture."""
    facture = Facture.query.get_or_404(facture_id)
    fournisseurs = Fournisseur.query.order_by(Fournisseur.nom).all()
    return render_template(
        "facture_detail.html", facture=facture, fournisseurs=fournisseurs
    )


@main.route("/factures/<int:facture_id>/modifier", methods=["POST"])
def modifier_facture(facture_id):
    """Modifie une facture."""
    facture = Facture.query.get_or_404(facture_id)

    facture.numero = request.form.get("numero", facture.numero)
    facture.fournisseur_nom = request.form.get("fournisseur_nom", facture.fournisseur_nom)

    fournisseur_id = request.form.get("fournisseur_id")
    if fournisseur_id:
        facture.fournisseur_id = int(fournisseur_id)

    date_str = request.form.get("date_facture")
    if date_str:
        try:
            facture.date_facture = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    for champ in ["montant_ht", "montant_tva", "montant_ttc", "taux_tva"]:
        val = request.form.get(champ)
        if val:
            try:
                setattr(facture, champ, float(val.replace(",", ".")))
            except ValueError:
                pass

    facture.statut = request.form.get("statut", facture.statut)
    facture.periode_tva = request.form.get("periode_tva", facture.periode_tva)
    facture.notes = request.form.get("notes", facture.notes)

    db.session.commit()
    flash("Facture mise à jour avec succès.", "success")
    return redirect(url_for("main.detail_facture", facture_id=facture.id))


@main.route("/factures/<int:facture_id>/ocr", methods=["POST"])
def lancer_ocr(facture_id):
    """Lance l'OCR sur une facture."""
    facture = Facture.query.get_or_404(facture_id)

    if not facture.fichier_path or not os.path.exists(facture.fichier_path):
        flash("Fichier introuvable.", "error")
        return redirect(url_for("main.detail_facture", facture_id=facture.id))

    try:
        from app.modules.ocr_service import OCRService

        ocr = OCRService()
        resultat = ocr.traiter_facture(facture.fichier_path)
        donnees = resultat["donnees"]

        if donnees.get("numero_facture"):
            facture.numero = donnees["numero_facture"]
        if donnees.get("date"):
            facture.date_facture = donnees["date"]
        if donnees.get("montant_ht"):
            facture.montant_ht = donnees["montant_ht"]
        if donnees.get("montant_tva"):
            facture.montant_tva = donnees["montant_tva"]
        if donnees.get("montant_ttc"):
            facture.montant_ttc = donnees["montant_ttc"]
        if donnees.get("taux_tva"):
            facture.taux_tva = donnees["taux_tva"]

        facture.ocr_traite = True
        facture.ocr_confiance = donnees.get("confiance", 0)

        # Assigner période TVA auto si date présente
        if facture.date_facture:
            facture.periode_tva = facture.date_facture.strftime("%Y-%m")

        db.session.commit()
        flash(
            f"OCR terminé (confiance: {donnees.get('confiance', 0)}%). "
            "Vérifiez les données extraites.",
            "success",
        )
    except Exception as e:
        flash(f"Erreur OCR : {e}", "error")

    return redirect(url_for("main.detail_facture", facture_id=facture.id))


@main.route("/factures/upload", methods=["GET", "POST"])
def upload_facture():
    """Upload manuel d'une facture."""
    if request.method == "POST":
        if "fichier" not in request.files:
            flash("Aucun fichier sélectionné.", "error")
            return redirect(request.url)

        fichier = request.files["fichier"]
        if fichier.filename == "":
            flash("Aucun fichier sélectionné.", "error")
            return redirect(request.url)

        filename = secure_filename(fichier.filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in (".pdf", ".jpg", ".jpeg", ".png", ".tiff"):
            flash("Format non supporté. Utilisez PDF, JPG, PNG ou TIFF.", "error")
            return redirect(request.url)

        # Sauvegarder le fichier
        now = datetime.now(timezone.utc)
        upload_dir = os.path.join(
            current_app.config["UPLOAD_FOLDER"], "manual", now.strftime("%Y-%m")
        )
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)
        fichier.save(filepath)

        # Créer l'entrée en base
        facture = Facture(
            fournisseur_nom=request.form.get("fournisseur_nom", "À identifier"),
            source="upload",
            fichier_path=filepath,
            fichier_nom=filename,
            statut="a_verifier",
        )
        db.session.add(facture)
        db.session.commit()

        flash(f"Facture '{filename}' importée avec succès.", "success")
        return redirect(url_for("main.detail_facture", facture_id=facture.id))

    fournisseurs = Fournisseur.query.order_by(Fournisseur.nom).all()
    return render_template("upload.html", fournisseurs=fournisseurs)


@main.route("/factures/<int:facture_id>/fichier")
def voir_fichier(facture_id):
    """Affiche ou télécharge le fichier de la facture."""
    facture = Facture.query.get_or_404(facture_id)
    if not facture.fichier_path or not os.path.exists(facture.fichier_path):
        flash("Fichier introuvable.", "error")
        return redirect(url_for("main.detail_facture", facture_id=facture.id))
    return send_file(facture.fichier_path)


# --- TVA ---


@main.route("/tva")
def page_tva():
    """Page de synthèse TVA."""
    annee = request.args.get("annee", date.today().year, type=int)
    tva_service = TVAService()
    resume = tva_service.resume_annuel(annee)
    stats_fournisseurs = tva_service.statistiques_fournisseurs()
    non_classees = tva_service.factures_non_classees()

    return render_template(
        "tva.html",
        resume=resume,
        stats_fournisseurs=stats_fournisseurs,
        non_classees=non_classees,
        annee=annee,
    )


@main.route("/tva/export/<periode>")
def export_tva(periode):
    """Exporte les factures d'une période en CSV."""
    tva_service = TVAService()
    csv_content = tva_service.export_csv(periode)

    from io import BytesIO

    buffer = BytesIO(csv_content.encode("utf-8-sig"))
    return send_file(
        buffer,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"factures_tva_{periode}.csv",
    )


# --- Fournisseurs ---


@main.route("/fournisseurs")
def liste_fournisseurs():
    """Liste des fournisseurs."""
    fournisseurs = Fournisseur.query.order_by(Fournisseur.nom).all()
    return render_template("fournisseurs.html", fournisseurs=fournisseurs)


@main.route("/fournisseurs/ajouter", methods=["POST"])
def ajouter_fournisseur():
    """Ajoute un nouveau fournisseur."""
    fournisseur = Fournisseur(
        nom=request.form["nom"],
        categorie=request.form.get("categorie", ""),
        site_url=request.form.get("site_url", ""),
        notes=request.form.get("notes", ""),
    )
    db.session.add(fournisseur)
    db.session.commit()
    flash(f"Fournisseur '{fournisseur.nom}' ajouté.", "success")
    return redirect(url_for("main.liste_fournisseurs"))


# --- Synchronisation ---


@main.route("/sync/gmail", methods=["POST"])
def sync_gmail():
    """Lance la synchronisation Gmail."""
    if not is_authenticated():
        flash("Veuillez d'abord connecter votre compte Google.", "error")
        return redirect(url_for("main.dashboard"))

    try:
        creds = load_credentials()
        from app.modules.gmail_service import GmailService

        gmail = GmailService(creds, current_app.config["UPLOAD_FOLDER"])
        query = current_app.config.get("GMAIL_SEARCH_QUERY")
        log = gmail.synchroniser(db.session, Facture, SyncLog, query)
        flash(log.message, "success" if log.statut == "succes" else "error")
    except Exception as e:
        flash(f"Erreur synchronisation Gmail : {e}", "error")

    return redirect(url_for("main.dashboard"))


@main.route("/sync/drive", methods=["POST"])
def sync_drive():
    """Lance la synchronisation Google Drive."""
    if not is_authenticated():
        flash("Veuillez d'abord connecter votre compte Google.", "error")
        return redirect(url_for("main.dashboard"))

    folder_id = current_app.config.get("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        flash("ID du dossier Google Drive non configuré.", "error")
        return redirect(url_for("main.dashboard"))

    try:
        creds = load_credentials()
        from app.modules.drive_service import DriveService

        drive = DriveService(creds, current_app.config["UPLOAD_FOLDER"])
        log = drive.synchroniser(db.session, Facture, SyncLog, folder_id)
        flash(log.message, "success" if log.statut == "succes" else "error")
    except Exception as e:
        flash(f"Erreur synchronisation Drive : {e}", "error")

    return redirect(url_for("main.dashboard"))


# --- Authentification Google ---


@main.route("/auth/google")
def auth_google():
    """Démarre le flux d'authentification Google OAuth2."""
    flow = get_flow(
        current_app.config["GOOGLE_CLIENT_ID"],
        current_app.config["GOOGLE_CLIENT_SECRET"],
        current_app.config["GOOGLE_REDIRECT_URI"],
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return redirect(authorization_url)


@main.route("/auth/callback")
def auth_callback():
    """Callback OAuth2 de Google."""
    flow = get_flow(
        current_app.config["GOOGLE_CLIENT_ID"],
        current_app.config["GOOGLE_CLIENT_SECRET"],
        current_app.config["GOOGLE_REDIRECT_URI"],
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    save_credentials(credentials)
    flash("Compte Google connecté avec succès !", "success")
    return redirect(url_for("main.dashboard"))


@main.route("/auth/deconnecter")
def auth_deconnecter():
    """Déconnecte le compte Google."""
    import os

    token_file = "token.json"
    if os.path.exists(token_file):
        os.remove(token_file)
    flash("Compte Google déconnecté.", "info")
    return redirect(url_for("main.dashboard"))


# --- API JSON ---


@main.route("/api/stats")
def api_stats():
    """API JSON pour les statistiques du dashboard."""
    periode = request.args.get("periode", date.today().strftime("%Y-%m"))
    tva_service = TVAService()
    resume = tva_service.resume_periode(periode)
    return jsonify(resume)
