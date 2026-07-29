"""
api_admin_route.py
-------------------
Blueprint Flask : gestion des utilisateurs (admin)

GET    /api/admin/users        -> liste des utilisateurs
POST   /api/admin/users        -> créer un utilisateur
DELETE /api/admin/users/<id>   -> supprimer un utilisateur
"""

from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash

from db import get_connection

admin_bp = Blueprint("admin_bp", __name__)


@admin_bp.route("/api/admin/users", methods=["GET"])
def list_users():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, nom, prenom, email, role, date_creation, last_connexion "
        "FROM utilisateurs ORDER BY date_creation DESC"
    )
    users = cursor.fetchall()
    cursor.close()
    conn.close()

    for u in users:
        if u.get("date_creation"):
            u["date_creation"] = u["date_creation"].strftime("%Y-%m-%d %H:%M")
        if u.get("last_connexion"):
            u["last_connexion"] = u["last_connexion"].strftime("%Y-%m-%d %H:%M")

    return jsonify(users)


@admin_bp.route("/api/admin/users", methods=["POST"])
def create_user():
    data = request.get_json(force=True)

    nom = data.get("nom")
    prenom = data.get("prenom")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")

    if not all([nom, prenom, email, password, role]):
        return jsonify({"error": "Tous les champs (nom, prenom, email, password, role) sont requis."}), 400

    if role not in ("ADMIN", "OUVRIER", "STAGIAIRE", "TECHNICIEN_LABO"):
        return jsonify({"error": "Rôle invalide."}), 400

    hashed = generate_password_hash(password)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO utilisateurs (nom, prenom, email, mot_de_passe, role) "
            "VALUES (%s, %s, %s, %s, %s)",
            (nom, prenom, email, hashed, role),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"Erreur lors de la création : {e}"}), 400

    cursor.close()
    conn.close()
    return jsonify({"id": new_id, "nom": nom, "prenom": prenom, "email": email, "role": role}), 201


@admin_bp.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM utilisateurs WHERE id = %s", (user_id,))
    conn.commit()
    deleted = cursor.rowcount
    cursor.close()
    conn.close()

    if deleted == 0:
        return jsonify({"error": "Utilisateur introuvable."}), 404
    return jsonify({"deleted": user_id})

@admin_bp.route("/api/admin/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.get_json(force=True)

    nom = data.get("nom")
    prenom = data.get("prenom")
    email = data.get("email")
    role = data.get("role")
    password = data.get("password")  # optionnel : si vide, on ne change pas le mot de passe

    if not all([nom, prenom, email, role]):
        return jsonify({"error": "Nom, prénom, email et rôle sont requis."}), 400

    if role not in ("ADMIN", "OUVRIER", "STAGIAIRE", "TECHNICIEN_LABO"):
        return jsonify({"error": "Rôle invalide."}), 400

    conn = get_connection()
    cursor = conn.cursor()
    try:
        if password:
            hashed = generate_password_hash(password)
            cursor.execute(
                "UPDATE utilisateurs SET nom=%s, prenom=%s, email=%s, role=%s, mot_de_passe=%s WHERE id=%s",
                (nom, prenom, email, role, hashed, user_id),
            )
        else:
            cursor.execute(
                "UPDATE utilisateurs SET nom=%s, prenom=%s, email=%s, role=%s WHERE id=%s",
                (nom, prenom, email, role, user_id),
            )
        conn.commit()
        updated = cursor.rowcount
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": f"Erreur lors de la modification : {e}"}), 400

    cursor.close()
    conn.close()

    if updated == 0:
        return jsonify({"error": "Utilisateur introuvable."}), 404
    return jsonify({"id": user_id, "nom": nom, "prenom": prenom, "email": email, "role": role})