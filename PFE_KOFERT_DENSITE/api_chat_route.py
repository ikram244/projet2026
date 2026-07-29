"""
api_chat_route.py
------------------
Blueprint Flask : POST   /api/chat
                  GET    /api/conversations
                  GET    /api/conversations/<id>/messages
                  DELETE /api/conversations/<id>
"""
from flask import Blueprint, request, jsonify, session
from chat_service import answer
from db import (
    create_conversation,
    get_conversations,
    get_messages,
    add_message,
    delete_conversation,
)

chat_bp = Blueprint("chat_bp", __name__)


@chat_bp.route("/api/chat", methods=["POST"])
def chat_route():
    data = request.get_json(force=True)

    question = data.get("question")
    history = data.get("history", [])
    conversation_id = data.get("conversation_id")
    utilisateur_id = session.get("user_id")

    if not question:
        return jsonify({"erreur": "question est requise"}), 400
    if not utilisateur_id:
        return jsonify({"erreur": "utilisateur non connecte"}), 401

    if not conversation_id:
        titre = question[:50] + ("..." if len(question) > 50 else "")
        conversation_id = create_conversation(utilisateur_id, titre)
        if not conversation_id:
            return jsonify({"erreur": "impossible de creer la conversation"}), 500

    add_message(conversation_id, "user", question)

    try:
        result = answer(question, history)
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

    add_message(conversation_id, "bot", result.get("reponse", ""))

    result["conversation_id"] = conversation_id
    return jsonify(result)


@chat_bp.route("/api/conversations", methods=["GET"])
def liste_conversations():
    utilisateur_id = session.get("user_id")
    if not utilisateur_id:
        return jsonify({"erreur": "utilisateur non connecte"}), 401

    conversations = get_conversations(utilisateur_id)
    return jsonify(conversations or [])


@chat_bp.route("/api/conversations/<int:conversation_id>/messages", methods=["GET"])
def messages_conversation(conversation_id):
    messages = get_messages(conversation_id)
    return jsonify(messages or [])


@chat_bp.route("/api/conversations/<int:conversation_id>", methods=["DELETE"])
def supprimer_conversation(conversation_id):
    result = delete_conversation(conversation_id)
    if not result:
        return jsonify({"erreur": "suppression echouee"}), 500
    return jsonify({"succes": True})