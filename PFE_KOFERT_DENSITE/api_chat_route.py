"""
api_chat_route.py
------------------
Blueprint Flask : POST /api/chat
"""
from flask import Blueprint, request, jsonify
from chat_service import answer

chat_bp = Blueprint("chat_bp", __name__)


@chat_bp.route("/api/chat", methods=["POST"])
def chat_route():
    data = request.get_json(force=True)

    question = data.get("question")
    history = data.get("history", [])

    if not question:
        return jsonify({"erreur": "question est requise"}), 400

    try:
        result = answer(question, history)
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

    return jsonify(result)
