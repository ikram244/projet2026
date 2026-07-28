"""
train_inverse_model.py
------------------------
Entraîne le modèle "inverse" par échelon.

Contrairement au forward model (RandomForest, précis mais non-linéaire donc
pas inversible analytiquement), le modèle inverse est une régression linéaire
sur les mêmes 6 paramètres. Elle sert à deux choses dans correction_service.py :

  1. Donner un premier jeu de valeurs "sensibilité" (coef_i) par tag, utilisées
     pour distribuer intelligemment un premier pas de correction (solution
     min-norme pondérée), avant raffinement par optimisation sur le forward model.
  2. Etre un garde-fou / fallback rapide si le forward model n'est pas disponible.

Usage :
    python train_inverse_model.py
"""

import json
import os

import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from train_forward_model import FEATURES, TARGET, clean, PROCESSED_CSV, SAVED_DIR


def train_one_echelon(df: pd.DataFrame, echelon: str) -> dict:
    d = df[df["echelon"] == echelon].copy()
    d = clean(d)

    X = d[FEATURES].values
    y = d[TARGET].values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LinearRegression()
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)

    metrics = {
        "echelon": echelon,
        "mae": float(mean_absolute_error(yte, pred)),
        "r2": float(r2_score(yte, pred)),
        "intercept": float(model.intercept_),
        "coefficients": dict(zip(FEATURES, model.coef_.tolist())),
    }

    os.makedirs(SAVED_DIR, exist_ok=True)
    joblib.dump(model, os.path.join(SAVED_DIR, f"model_{echelon}.joblib"))
    with open(os.path.join(SAVED_DIR, f"metrics_inverse_{echelon}.json"), "w") as fh:
        json.dump(metrics, fh, indent=2)

    print(f"[{echelon}] (inverse/sensibilité) MAE={metrics['mae']:.2f}  R2={metrics['r2']:.3f}")
    return metrics


def main():
    df = pd.read_csv(PROCESSED_CSV)
    all_metrics = {}
    for echelon in ["J", "K", "L"]:
        if echelon not in df["echelon"].unique():
            continue
        all_metrics[echelon] = train_one_echelon(df, echelon)

    with open(os.path.join(SAVED_DIR, "metrics_inverse_all.json"), "w") as fh:
        json.dump(all_metrics, fh, indent=2)


if __name__ == "__main__":
    main()
