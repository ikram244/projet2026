"""
api_history_route.py
---------------------
Blueprint Flask : enregistrement et historique des corrections.

POST /api/predictions              -> crée une ligne predictions_modele (état "avant correction")
POST /api/predictions/<id>/ajustement -> crée une ligne ajustements_parametres liée (APPLIQUEE ou REFUSEE)
GET  /api/predictions/historique   -> liste jointe predictions_modele + ajustements_parametres
"""

from flask import Blueprint, request, jsonify, session

from db import get_connection

history_bp = Blueprint("history_bp", __name__)

FEATURE_TO_COLUMN = {
    "TI_entree_ech": "temperature_entree",
    "TIC_sortie_ech": "temperature_sortie",
    "PI_boucle": "pression_boucle",
    "PI_calendre": "pression_calandre",
    "PI_separateur": "depression",
    "prod_sortie_54": "debit_sortie",
}


@history_bp.route("/api/predictions", methods=["POST"])
def create_prediction():
    if "user_id" not in session:
        return jsonify({"error": "Non authentifié."}), 401

    data = request.get_json(force=True)

    echelon = data.get("echelon")
    densite_cible = data.get("densite_cible")
    densite_mesuree = data.get("densite_mesuree")
    params_actuels = data.get("params_actuels", {})
    densite_predite = data.get("densite_predite")
    ecart = data.get("ecart")

    if not echelon or densite_cible is None or densite_mesuree is None:
        return jsonify({"error": "echelon, densite_cible et densite_mesuree sont requis."}), 400

    cols = {FEATURE_TO_COLUMN[k]: v for k, v in params_actuels.items() if k in FEATURE_TO_COLUMN}

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO predictions_modele
                (utilisateur_id, echelon, densite_cible, densite_mesuree,
                 temperature_entree, temperature_sortie, pression_boucle,
                 pression_calandre, depression, debit_sortie,
                 densite_predite, ecart)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session["user_id"], echelon, densite_cible, densite_mesuree,
                cols.get("temperature_entree"), cols.get("temperature_sortie"),
                cols.get("pression_boucle"), cols.get("pression_calandre"),
                cols.get("depression"), cols.get("debit_sortie"),
                densite_predite, ecart,
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"Erreur enregistrement prédiction : {e}"}), 400

    cursor.close()
    conn.close()
    return jsonify({"prediction_id": new_id}), 201


@history_bp.route("/api/predictions/<int:prediction_id>/ajustement", methods=["POST"])
def create_ajustement(prediction_id):
    if "user_id" not in session:
        return jsonify({"error": "Non authentifié."}), 401

    data = request.get_json(force=True)

    etat = data.get("etat")
    motif = data.get("motif")
    params_corriges = data.get("params_corriges", {})
    densite_predite_apres = data.get("densite_predite_apres_correction")
    densite_cible = data.get("densite_cible_apres_correction")
    ecart_final = data.get("ecart_final")
    etat_du_modele = data.get("etat_du_modele", "Recalé sur Labo")

    if etat not in ("APPLIQUEE", "REFUSEE"):
        return jsonify({"error": "etat doit être APPLIQUEE ou REFUSEE."}), 400

    if etat == "REFUSEE" and not motif:
        return jsonify({"error": "Le motif est obligatoire en cas de refus."}), 400

    cols = {FEATURE_TO_COLUMN[k]: v for k, v in params_corriges.items() if k in FEATURE_TO_COLUMN}

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO ajustements_parametres
                (prediction_id, nouveau_temperature_entree, nouveau_temperature_sortie,
                 nouveau_pression_boucle, nouveau_pression_calandre, nouveau_depression,
                 nouveau_debit_sortie, densite_predite_apres_correction,
                 densite_cible_apres_correction, ecart_final, etat, motif, etat_du_modele)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                prediction_id,
                cols.get("temperature_entree"), cols.get("temperature_sortie"),
                cols.get("pression_boucle"), cols.get("pression_calandre"),
                cols.get("depression"), cols.get("debit_sortie"),
                densite_predite_apres, densite_cible, ecart_final,
                etat, motif, etat_du_modele,
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"Erreur enregistrement ajustement : {e}"}), 400

    cursor.close()
    conn.close()
    return jsonify({"ajustement_id": new_id, "etat": etat}), 201


@history_bp.route("/api/predictions/historique", methods=["GET"])
def historique():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            p.id AS prediction_id, p.echelon, p.densite_cible, p.densite_mesuree,
            p.densite_predite, p.ecart, p.date_prediction,
            u.nom, u.prenom,
            a.id AS ajustement_id, a.etat, a.motif, a.etat_du_modele,
            a.densite_predite_apres_correction, a.ecart_final, a.date_ajustement
        FROM predictions_modele p
        JOIN utilisateurs u ON u.id = p.utilisateur_id
        LEFT JOIN ajustements_parametres a ON a.prediction_id = p.id
        ORDER BY p.date_prediction DESC
        LIMIT 200
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    for r in rows:
        if r.get("date_prediction"):
            r["date_prediction"] = r["date_prediction"].strftime("%Y-%m-%d %H:%M")
        if r.get("date_ajustement"):
            r["date_ajustement"] = r["date_ajustement"].strftime("%Y-%m-%d %H:%M")

    return jsonify(rows)