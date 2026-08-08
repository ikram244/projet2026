"""
retrain_manager.py
--------------------
Reentrainement automatique cible : quand une correction proposee est
REFUSEE, les parametres reels + la densite reellement mesuree en labo
(deja enregistres dans predictions_modele au moment de la prediction)
sont un exemple d'entrainement valide que le modele actuel a mal predit.
Ce module ajoute cet exemple au CSV d'entrainement et relance
l'entrainement (forward + inverse) uniquement pour l'echelon concerne.

N'importe et ne modifie AUCUN fichier existant : reutilise
train_forward_model.py et train_inverse_model.py tels quels.
"""

import pandas as pd

import train_forward_model
import train_inverse_model
import predict_service
import correction_service

FEATURES = train_forward_model.FEATURES
TARGET = train_forward_model.TARGET
RAW_CSV = train_forward_model.RAW_CSV
PROCESSED_CSV = train_forward_model.PROCESSED_CSV


def enregistrer_cas_refuse(echelon: str, params_reels: dict, densite_mesuree: float) -> bool:
    """Ajoute une ligne reelle (parametres + densite mesuree labo) au CSV brut."""
    ligne = {f: params_reels.get(f) for f in FEATURES}
    ligne["echelon"] = echelon
    ligne[TARGET] = densite_mesuree

    if any(v is None for v in ligne.values()):
        return False  # donnees incompletes -> pas d'ajout, pas de casse

    df = pd.read_csv(RAW_CSV)
    df = pd.concat([df, pd.DataFrame([ligne])], ignore_index=True)
    df.to_csv(RAW_CSV, index=False)
    return True


def _invalider_cache(echelon: str) -> None:
    """Vide le cache memoire des modeles pour forcer le rechargement des
    nouveaux fichiers .joblib au prochain appel (sans quoi le process
    Flask garderait l'ancien modele en RAM)."""
    predict_service._forward_models.pop(echelon, None)
    predict_service._forward_metrics.pop(echelon, None)
    correction_service._inverse_models.pop(echelon, None)


def reentrainer_echelon(echelon: str) -> dict:
    """Relance forward + inverse pour un seul echelon, avec les memes
    fonctions/hyperparametres que train_forward_model.py / train_inverse_model.py."""
    df = pd.read_csv(RAW_CSV)
    if echelon not in df["echelon"].unique():
        return {"echelon": echelon, "status": "ignore", "raison": "echelon absent du CSV"}

    metrics_forward = train_forward_model.train_one_echelon(df, echelon)

    df.to_csv(PROCESSED_CSV, index=False)
    df_clean = pd.read_csv(PROCESSED_CSV)
    metrics_inverse = train_inverse_model.train_one_echelon(df_clean, echelon)

    _invalider_cache(echelon)

    return {"echelon": echelon, "status": "ok", "forward": metrics_forward, "inverse": metrics_inverse}


def traiter_refus(echelon: str, params_reels: dict, densite_mesuree: float) -> dict:
    """Point d'entree unique appele au moment d'un refus."""
    ajoute = enregistrer_cas_refuse(echelon, params_reels, densite_mesuree)
    if not ajoute:
        return {"echelon": echelon, "status": "ignore", "raison": "parametres incomplets"}
    return reentrainer_echelon(echelon)