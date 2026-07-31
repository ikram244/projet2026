"""
api_predict_route.py
---------------------
Blueprint Flask : POST /api/predict
                   GET /api/predictions/historique (avec désactivation du cache)
"""

from flask import Blueprint, jsonify, request, make_response

import predict_service
from db import get_connection

predict_bp = Blueprint("predict_bp", __name__)


@predict_bp.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json(force=True)

    echelon = data.get("echelon", "J")
    params = data.get("params")
    if not params:
        return jsonify({"error": "Le champ 'params' est requis."}), 400

    try:
        densite = predict_service.predict_density(echelon, params)
    except (ValueError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "echelon": echelon,
        "densite_predite": round(densite, 2),
    })


@predict_bp.route("/api/predictions/historique", methods=["GET"])
def historique():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            p.id AS prediction_id, p.echelon, p.densite_cible, p.densite_mesuree,
            p.densite_predite, p.ecart, p.date_prediction,
            p.temperature_entree, p.temperature_sortie, p.pression_boucle,
            p.pression_calandre, p.depression, p.debit_sortie,
            u.nom, u.prenom,
            a.id AS ajustement_id, a.etat, a.motif, a.etat_du_modele,
            a.nouveau_temperature_entree, a.nouveau_temperature_sortie,
            a.nouveau_pression_boucle, a.nouveau_pression_calandre,
            a.nouveau_depression, a.nouveau_debit_sortie,
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

    response = make_response(jsonify(rows))
    # Désactiver le cache pour un affichage en temps réel
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response