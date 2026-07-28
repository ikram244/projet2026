"""
predict_service.py
-------------------
Charge les modèles forward (un par échelon) et expose predict_density().
"""

import json
import os

import joblib

SAVED_DIR = "model/saved"
FEATURES = [
    "TIC_sortie_ech",
    "TI_entree_ech",
    "PI_calendre",
    "PI_boucle",
    "PI_separateur",
    "prod_sortie_54",
]

_forward_models = {}
_forward_metrics = {}


def _load_echelon(echelon: str):
    if echelon not in _forward_models:
        path = os.path.join(SAVED_DIR, f"forward_model_{echelon}.joblib")
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Modèle forward introuvable pour l'échelon {echelon}. "
                f"Lancez `python train_forward_model.py` d'abord."
            )
        _forward_models[echelon] = joblib.load(path)

        metrics_path = os.path.join(SAVED_DIR, f"metrics_forward_{echelon}.json")
        if os.path.exists(metrics_path):
            with open(metrics_path) as fh:
                _forward_metrics[echelon] = json.load(fh)
    return _forward_models[echelon]


def get_metrics(echelon: str) -> dict:
    _load_echelon(echelon)
    return _forward_metrics.get(echelon, {})


def params_to_vector(params: dict) -> list:
    """Convertit un dict {nom_tag: valeur} dans l'ordre attendu par le modèle."""
    missing = [f for f in FEATURES if f not in params]
    if missing:
        raise ValueError(f"Paramètres manquants pour la prédiction : {missing}")
    return [params[f] for f in FEATURES]


def predict_density(echelon: str, params: dict) -> float:
    """
    params : dict avec les clés TIC_sortie_ech, TI_entree_ech, PI_calendre,
             PI_boucle, PI_separateur, prod_sortie_54
    Retourne la densité 54% prédite.
    """
    model = _load_echelon(echelon)
    x = [params_to_vector(params)]
    return float(model.predict(x)[0])
