"""
train.py
--------
Lance l'entraînement complet (forward puis inverse) pour les 3 échelons.

Usage :
    python train.py
"""

import train_forward_model
import train_inverse_model

if __name__ == "__main__":
    print("=== Entraînement du modèle forward (paramètres -> densité) ===")
    train_forward_model.main()

    print("\n=== Entraînement du modèle inverse / sensibilité ===")
    train_inverse_model.main()

    print("\nTerminé. Modèles sauvegardés dans model/saved/")
