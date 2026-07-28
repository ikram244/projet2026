"""
train_forward_model.py
-----------------------
Entraîne le modèle "forward" : paramètres process -> densité sortie 54%.
Un modèle est entraîné par échelon (J, K, L) car chaque boucle a sa propre
dynamique thermique/hydraulique.

Usage :
    python train_forward_model.py
"""

import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

RAW_CSV = "data/raw/data_densite_pret_pour_modele_v3.csv"
PROCESSED_CSV = "data/processed/data_clean.csv"
SAVED_DIR = "model/saved"

FEATURES = [
    "TIC_sortie_ech",
    "TI_entree_ech",
    "PI_calendre",
    "PI_boucle",
    "PI_separateur",
    "prod_sortie_54",
]
TARGET = "densite_sortie_54"

# Bornes physiques plausibles utilisées pour filtrer les valeurs aberrantes du CSV.
# A ajuster si les tags/instruments changent de plage normale d'exploitation.
PHYSICAL_BOUNDS = {
    "densite_sortie_54": (1400, 1750),
    "TIC_sortie_ech": (50, 120),
    "TI_entree_ech": (50, 120),
    "PI_calendre": (-5, 10),
    "PI_boucle": (-5, 10),
    "PI_separateur": (-50, 250),
    "prod_sortie_54": (0, 40),
}


def clean(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col, (lo, hi) in PHYSICAL_BOUNDS.items():
        out = out[(out[col] > lo) & (out[col] < hi)]
    return out


def train_one_echelon(df: pd.DataFrame, echelon: str) -> dict:
    d = df[df["echelon"] == echelon].copy()
    d = clean(d)

    X = d[FEATURES].values
    y = d[TARGET].values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(
        n_estimators=400,
        max_depth=10,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(Xtr, ytr)

    pred = model.predict(Xte)
    metrics = {
        "echelon": echelon,
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "mae": float(mean_absolute_error(yte, pred)),
        "r2": float(r2_score(yte, pred)),
        "feature_importances": dict(zip(FEATURES, model.feature_importances_.tolist())),
        "feature_ranges": {
            f: {
                "min": float(d[f].quantile(0.02)),
                "max": float(d[f].quantile(0.98)),
                "mean": float(d[f].mean()),
                "std": float(d[f].std()),
            }
            for f in FEATURES
        },
        "target_range": {
            "min": float(d[TARGET].quantile(0.02)),
            "max": float(d[TARGET].quantile(0.98)),
            "mean": float(d[TARGET].mean()),
            "std": float(d[TARGET].std()),
        },
    }

    os.makedirs(SAVED_DIR, exist_ok=True)
    joblib.dump(model, os.path.join(SAVED_DIR, f"forward_model_{echelon}.joblib"))
    with open(os.path.join(SAVED_DIR, f"metrics_forward_{echelon}.json"), "w") as fh:
        json.dump(metrics, fh, indent=2)

    print(f"[{echelon}] MAE={metrics['mae']:.2f}  R2={metrics['r2']:.3f}  "
          f"(train={metrics['n_train']}, test={metrics['n_test']})")
    return metrics


def main():
    df = pd.read_csv(RAW_CSV)
    os.makedirs("data/processed", exist_ok=True)
    df.to_csv(PROCESSED_CSV, index=False)

    all_metrics = {}
    for echelon in ["J", "K", "L"]:
        if echelon not in df["echelon"].unique():
            continue
        all_metrics[echelon] = train_one_echelon(df, echelon)

    with open(os.path.join(SAVED_DIR, "metrics_forward_all.json"), "w") as fh:
        json.dump(all_metrics, fh, indent=2)


if __name__ == "__main__":
    main()
