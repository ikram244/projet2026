"""
correction_service.py
----------------------
Le coeur "métier" du modèle : à partir de

  - la densité mesurée en laboratoire (valeur réelle, toutes les 30 min)
  - la densité cible souhaitée
  - les valeurs actuelles des paramètres process (les 6 tags)
  - la liste des variables que l'opérateur autorise à modifier

... calcule directement le nouveau jeu de valeurs de consigne à appliquer,
sans passer par les itérations manuelles (régler -> attendre 30 min ->
remesurer -> régler encore).

Principe :
  1. L'écart réel à combler est purement terrain : cible - mesure labo
     (indépendant de tout modèle).
  2. On distribue cet écart entre les variables actives au prorata de leur
     sensibilité réelle (coefficient du modèle inverse) pondérée par leur
     variabilité historique (écart-type) : solution "min-norme" pondérée,
     la même famille de solution que résoudrait un moindre-carré sous-
     déterminé (moins de contraintes que d'inconnues -> on prend la
     correction la plus "économe" en énergie de réglage).
  3. Chaque nouvelle consigne est bornée par la plage historiquement
     observée pour ce tag (on ne propose jamais une valeur jamais vue,
     donc jamais testée en exploitation réelle).
  4. Le modèle forward (RandomForest, plus précis que le modèle linéaire
     pour la prédiction pure) sert à recalculer, à titre de contrôle,
     la densité prédite avant/après correction et donc l'écart final
     réellement attendu.

Remarque technique : on n'utilise pas d'optimiseur à gradient (type
L-BFGS-B) directement sur le forward model RandomForest, car ses
prédictions sont des fonctions "en escalier" (constantes par morceaux) :
le gradient numérique y est quasiment partout nul et l'optimiseur ne
bouge pas. Le modèle linéaire, entraîné sur les mêmes données, donne au
contraire une direction de correction stable et interprétable.
"""

import os

import joblib
import numpy as np

import predict_service
from predict_service import FEATURES

SAVED_DIR = "model/saved"

_inverse_models = {}


def _load_inverse(echelon: str):
    if echelon not in _inverse_models:
        path = os.path.join(SAVED_DIR, f"model_{echelon}.joblib")
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Modèle inverse introuvable pour l'échelon {echelon}. "
                f"Lancez `python train_inverse_model.py` d'abord."
            )
        _inverse_models[echelon] = joblib.load(path)
    return _inverse_models[echelon]


def correct(
    echelon: str,
    densite_mesuree: float,
    densite_cible: float,
    current_params: dict,
    active_vars: list = None,
) -> dict:
    """
    Retourne un dict :
        {
          "densite_predite_actuelle": ...,
          "biais_modele": ...,
          "params_actuels": {...},
          "params_corriges": {...},
          "deltas": {...},
          "densite_predite_apres_correction": ...,
          "ecart_final": ...,   # (prédiction après correction, biais inclus) - cible
          "variables_optimisees": [...]
        }
    """
    linear_model = _load_inverse(echelon)
    coefs = dict(zip(FEATURES, linear_model.coef_.tolist()))

    if active_vars is None or len(active_vars) == 0:
        active_vars = list(FEATURES)
    active_vars = [v for v in active_vars if v in FEATURES]
    if not active_vars:
        raise ValueError("Aucune variable valide à optimiser.")

    x0 = np.array(predict_service.params_to_vector(current_params), dtype=float)

    # Prédiction du modèle forward (RandomForest) au réglage actuel, pour
    # le contrôle / biais terrain-modèle.
    pred_actuelle = predict_service.predict_density(echelon, current_params)
    biais = densite_mesuree - pred_actuelle

    # Écart réel à combler : purement terrain, indépendant du modèle.
    ecart_reel = densite_cible - densite_mesuree

    metrics = predict_service.get_metrics(echelon)
    feature_ranges = metrics.get("feature_ranges", {})
    stds = np.array([feature_ranges.get(f, {}).get("std", 1.0) or 1.0 for f in FEATURES])
    coef_vec = np.array([coefs[f] for f in FEATURES])

    # Solution min-norme pondérée, restreinte aux variables actives.
    active_mask = np.array([f in active_vars for f in FEATURES])
    weights = coef_vec * (stds ** 2) * active_mask
    denom = float(np.sum(coef_vec * weights))
    if abs(denom) < 1e-9:
        raise ValueError("Sensibilité des variables sélectionnées trop faible pour corriger.")

    deltas_arr = (weights / denom) * ecart_reel

    x_opt = x0 + deltas_arr
    # Bornage aux plages historiquement observées pour chaque tag.
    for i, f in enumerate(FEATURES):
        rng = feature_ranges.get(f, {})
        lo, hi = rng.get("min"), rng.get("max")
        if lo is not None and hi is not None:
            x_opt[i] = min(max(x_opt[i], lo), hi)
    deltas_arr = x_opt - x0

    params_corriges = dict(zip(FEATURES, x_opt.tolist()))
    pred_finale = predict_service.predict_density(echelon, params_corriges)
    ecart_final = (pred_finale + biais) - densite_cible

    return {
        "densite_predite_actuelle": round(pred_actuelle, 2),
        "biais_modele": round(biais, 2),
        "params_actuels": dict(zip(FEATURES, x0.tolist())),
        "params_corriges": {f: round(v, 3) for f, v in params_corriges.items()},
        "deltas": {f: round(float(deltas_arr[i]), 3) for i, f in enumerate(FEATURES)},
        "densite_predite_apres_correction": round(pred_finale, 2),
        "ecart_final": round(ecart_final, 2),
        "variables_optimisees": active_vars,
    }
