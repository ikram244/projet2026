"""
correction_constraints.py
----------------------------
Filtre de coherence physique applique APRES correction_service.correct().
Ne modifie pas correction_service.py : post-traitement appele depuis
api_correction_route.py.

Probleme cible : la solution min-norme ponderee de correction_service.py
traite les 6 variables independamment via leurs coefficients de
regression lineaire. Deux variables physiquement liees (ex. temperature
entree / sortie de l'echangeur, qui montent et descendent ensemble dans
le procede reel) peuvent recevoir des corrections de sens oppose.

Ce module calcule, a partir de l'historique reel, la correlation entre
chaque paire de variables. Si deux variables sont fortement correlees
mais que les deltas proposes vont dans un sens incoherent avec cette
correlation, le delta de la variable la moins sensible est annule.
"""

import pandas as pd

from train_forward_model import FEATURES, PROCESSED_CSV, clean
import predict_service
import correction_service

SEUIL_CORRELATION = 0.5

_correlations = {}


def _get_correlation_matrix(echelon: str) -> pd.DataFrame:
    if echelon not in _correlations:
        df = pd.read_csv(PROCESSED_CSV)
        d = clean(df[df["echelon"] == echelon])
        _correlations[echelon] = d[FEATURES].corr()
    return _correlations[echelon]


def _coefs(echelon: str) -> dict:
    linear_model = correction_service._load_inverse(echelon)
    return dict(zip(FEATURES, linear_model.coef_.tolist()))


def recadrer_resultat(echelon: str, result: dict, densite_cible: float) -> dict:
    corr = _get_correlation_matrix(echelon)
    coefs = _coefs(echelon)

    deltas = dict(result["deltas"])
    params_actuels = result["params_actuels"]
    modifie = False

    for i, f1 in enumerate(FEATURES):
        for f2 in FEATURES[i + 1:]:
            if f1 not in corr.columns or f2 not in corr.columns:
                continue
            r = corr.loc[f1, f2]
            if pd.isna(r) or abs(r) < SEUIL_CORRELATION:
                continue

            d1, d2 = deltas.get(f1, 0.0), deltas.get(f2, 0.0)
            if d1 == 0 or d2 == 0:
                continue

            meme_sens_attendu = r > 0
            meme_sens_propose = (d1 > 0) == (d2 > 0)

            if meme_sens_attendu != meme_sens_propose:
                moins_sensible = f1 if abs(coefs.get(f1, 0)) < abs(coefs.get(f2, 0)) else f2
                deltas[moins_sensible] = 0.0
                modifie = True

    if not modifie:
        return result

    params_corriges = {f: params_actuels[f] + deltas.get(f, 0.0) for f in FEATURES}
    pred_finale = predict_service.predict_density(echelon, params_corriges)
    ecart_final = (pred_finale + result["biais_modele"]) - densite_cible

    result["deltas"] = {f: round(deltas.get(f, 0.0), 3) for f in FEATURES}
    result["params_corriges"] = {f: round(params_corriges[f], 3) for f in FEATURES}
    result["densite_predite_apres_correction"] = round(pred_finale, 2)
    result["ecart_final"] = round(ecart_final, 2)
    return result