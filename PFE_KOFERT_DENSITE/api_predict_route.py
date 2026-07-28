"""
api_predict_route.py
---------------------
Blueprint Flask : POST /api/predict
"""

from flask import Blueprint, jsonify, request

import predict_service

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
