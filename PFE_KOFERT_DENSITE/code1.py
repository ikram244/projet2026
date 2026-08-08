# generate_figures.py
import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

DATA_CSV = "PFE_KOFERT_DENSITE/data/raw/data_densite_pret_pour_modele_v3.csv"
METRICS_JSON = "PFE_KOFERT_DENSITE/model/saved/metrics_forward_all.json"
OUTDIR = "report_figures"
os.makedirs(OUTDIR, exist_ok=True)

# Chargement des données (si disponible)
df = pd.read_csv(DATA_CSV, parse_dates=["horodatage"])
metrics = json.load(open(METRICS_JSON, "r", encoding="utf-8"))

# 1) Statistiques descriptives globales et par echelon
desc = df.describe(include="all")
desc.to_csv(os.path.join(OUTDIR, "dataset_describe.csv"))

for ech in ["J","K","L"]:
    d = df[df["echelon"]==ech]
    if len(d)==0:
        continue
    d[["TIC_sortie_ech","TI_entree_ech","PI_calendre","PI_boucle","PI_separateur","prod_sortie_54","densite_sortie_54"]].describe().to_csv(os.path.join(OUTDIR, f"describe_{ech}.csv"))

# 2) Histograms and boxplots for features (global)
features = ["TIC_sortie_ech","TI_entree_ech","PI_calendre","PI_boucle","PI_separateur","prod_sortie_54"]
for f in features:
    plt.figure(figsize=(8,4))
    sns.histplot(df[f].dropna(), bins=50, kde=False)
    plt.title(f"Histogramme : {f}")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, f"hist_{f}.png"))
    plt.close()

    plt.figure(figsize=(6,4))
    sns.boxplot(x="echelon", y=f, data=df)
    plt.title(f"Boxplot par échelon : {f}")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, f"box_{f}.png"))
    plt.close()

# 3) Correlation heatmap (features vs target) — numeric subset
num_cols = features + ["densite_sortie_54"]
corr = df[num_cols].corr()
plt.figure(figsize=(8,6))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1)
plt.title("Matrice de corrélation (features vs densite_sortie_54)")
plt.tight_layout()
plt.savefig(os.path.join(OUTDIR, "corr_heatmap.png"))
plt.close()

# 4) Feature importances from metrics JSON (bar plots)
for ech, info in metrics.items():
    fi = info.get("feature_importances", {})
    if not fi:
        continue
    items = sorted(fi.items(), key=lambda x: x[1], reverse=True)
    names = [i[0] for i in items]
    vals = [i[1] for i in items]
    plt.figure(figsize=(8,4))
    sns.barplot(x=vals, y=names, palette="viridis")
    plt.title(f"Feature importances — Forward model (échelon {ech})")
    plt.xlabel("Importance")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, f"fi_forward_{ech}.png"))
    plt.close()

# 5) Performance table from metrics
rows = []
for ech, info in metrics.items():
    rows.append({
        "echelon": ech,
        "n_train": info.get("n_train"),
        "n_test": info.get("n_test"),
        "mae": info.get("mae"),
        "r2": info.get("r2")
    })
perf_df = pd.DataFrame(rows).set_index("echelon")
perf_df.to_csv(os.path.join(OUTDIR, "performance_forward.csv"))

print("Figures et tableaux générés dans", OUTDIR)