"""
api_notifications_route.py
----------------------------
Blueprint Flask : notifications (cloche) pour tous les roles sauf STAGIAIRE.

GET  /api/notifications                 -> liste des notifications de l'utilisateur connecte
GET  /api/notifications/count           -> nombre de notifications non lues
POST /api/notifications/marquer-lues    -> marque toutes les notifications comme lues
"""
from flask import Blueprint, jsonify, session

from db import get_notifications, count_notifications_non_lues, marquer_notifications_lues

notifications_bp = Blueprint("notifications_bp", __name__)


@notifications_bp.route("/api/notifications", methods=["GET"])
def list_notifications():
    if "user_id" not in session:
        return jsonify({"error": "Non authentifié."}), 401
    if session.get("user_role") == "STAGIAIRE":
        return jsonify([])

    rows = get_notifications(session["user_id"])
    for r in rows or []:
        if r.get("date_creation"):
            r["date_creation"] = r["date_creation"].strftime("%Y-%m-%d %H:%M")

    return jsonify(rows or [])


@notifications_bp.route("/api/notifications/count", methods=["GET"])
def notifications_count():
    if "user_id" not in session:
        return jsonify({"count": 0})
    if session.get("user_role") == "STAGIAIRE":
        return jsonify({"count": 0})

    count = count_notifications_non_lues(session["user_id"])
    return jsonify({"count": count})


@notifications_bp.route("/api/notifications/marquer-lues", methods=["POST"])
def notifications_marquer_lues():
    if "user_id" not in session:
        return jsonify({"error": "Non authentifié."}), 401

    marquer_notifications_lues(session["user_id"])
    return jsonify({"ok": True})