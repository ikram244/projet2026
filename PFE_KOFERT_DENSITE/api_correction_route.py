"""
api_correction_route.py
------------------------
Blueprint Flask : POST /api/correction

Corps attendu (JSON) :
{
  "echelon": "J",
  "densite_mesuree": 1618,
  "densite_cible": 1625,
  "params": {
      "TIC_sortie_ech": 83.0,
      "TI_entree_ech": 78.7,
      "PI_calendre": 0.79,
      "PI_boucle": 2.11,
      "PI_separateur": 95.2,
      "prod_sortie_54": 19.1
  },
  "variables_a_optimiser": ["TIC_sortie_ech", "TI_entree_ech", "PI_calendre",
                             "PI_boucle", "PI_separateur", "prod_sortie_54"]
}
"""

from flask import Blueprint, jsonify, request

import correction_service

correction_bp = Blueprint("correction_bp", __name__)


@correction_bp.route("/api/correction", methods=["POST"])
def correction():
    data = request.get_json(force=True)

    echelon = data.get("echelon", "J")
    densite_mesuree = data.get("densite_mesuree")
    densite_cible = data.get("densite_cible")
    params = data.get("params")
    variables_a_optimiser = data.get("variables_a_optimiser")

    if densite_mesuree is None or densite_cible is None or not params:
        return jsonify({
            "error": "Les champs 'densite_mesuree', 'densite_cible' et 'params' sont requis."
        }), 400

    try:
        result = correction_service.correct(
            echelon=echelon,
            densite_mesuree=float(densite_mesuree),
            densite_cible=float(densite_cible),
            current_params=params,
            active_vars=variables_a_optimiser,
        )
    except (ValueError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 400

    result["echelon"] = echelon
    return jsonify(result)
