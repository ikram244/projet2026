# PFE KOFERT — Correction de densité (échelons J/K/L)

Assistant IA remplaçant le réglage manuel itératif de la densité (28% -> 54%) :
l'opérateur donne la densité mesurée en labo et la densité cible, l'outil
renvoie directement les nouvelles consignes des 6 paramètres process.

## Installation

```bash
python -m venv venv
source venv/bin/activate      # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

## 1. Entraîner les modèles (déjà fait, fichiers .joblib inclus dans model/saved/)

```bash
python train.py
```

Cela entraîne, pour chaque échelon (J, K, L) :
- `forward_model_<echelon>.joblib` : RandomForest, paramètres -> densité (précision de prédiction)
- `model_<echelon>.joblib` : régression linéaire, sert de modèle de sensibilité
  pour calculer la direction de correction (voir `correction_service.py`)
- des fichiers `metrics_*.json` (MAE, R², plages historiques par tag)

## 2. Lancer le serveur

```bash
python app.py
```

Puis ouvrir http://localhost:5000

## Structure

```
app.py                     -> point d'entrée Flask
api_predict_route.py       -> POST /api/predict   (paramètres -> densité)
api_correction_route.py    -> POST /api/correction (mesure + cible -> nouvelle consigne)
predict_service.py         -> charge et interroge le modèle forward
correction_service.py      -> logique métier de correction (coeur du projet)
train_forward_model.py     -> entraînement du modèle forward (RandomForest)
train_inverse_model.py     -> entraînement du modèle de sensibilité (linéaire)
train.py                   -> lance les deux entraînements
data/raw/                  -> CSV source
data/processed/            -> CSV nettoyé (bornes physiques appliquées)
model/saved/                -> modèles .joblib + métriques
frontend/templates/index.html -> interface (densité mesurée + cible + 6 tags)
frontend/static/style.css     -> style de l'interface
```

## Principe de la correction (correction_service.py)

1. **Écart réel** = densité cible − densité mesurée en labo (indépendant du modèle).
2. Cet écart est distribué entre les variables actives au prorata de leur
   sensibilité réelle (coefficients du modèle linéaire) pondérée par leur
   variabilité historique — solution "min-norme" : la correction la plus
   économe en amplitude de réglage.
3. Chaque nouvelle consigne est bornée par la plage historiquement observée
   pour ce tag (percentiles 2–98% du dataset).
4. Le modèle forward (RandomForest, plus précis en prédiction pure) sert de
   contrôle : il recalcule la densité prédite avant/après correction, d'où
   l'« écart final » affiché à l'écran.

### Pourquoi pas un optimiseur à gradient sur le RandomForest ?

Testé, puis écarté : les prédictions d'un RandomForest sont des fonctions
en escalier (constantes par morceaux). Le gradient numérique y est presque
partout nul, donc un optimiseur type L-BFGS-B ne bouge pas les paramètres.
Le modèle linéaire donne une direction de correction stable et interprétable ;
le RandomForest reste seulement l'outil de prédiction/contrôle.

## Limites actuelles / pistes d'amélioration pour le rapport de PFE

- R² du modèle forward : J=0.73, K=0.71, L=0.84 (RandomForest, 6 features).
- R² du modèle de sensibilité (linéaire) : ~0.44–0.51 — la relation
  paramètres -> densité n'est pas purement linéaire, d'où l'écart final
  non rigoureusement nul après correction.
- Pistes : ajouter des features (débit acide 28% entrée, temps depuis
  dernier réglage), tester un modèle différentiable (réseau de neurones
  ou gradient boosting avec approximation lisse) pour permettre une
  vraie optimisation par gradient, ou une boucle de correction itérative
  (recalcul après chaque petit pas, comme le ferait un opérateur mais en
  quelques secondes au lieu de plusieurs heures).
