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
    
    # Récupérer l'utilisateur depuis la session OU depuis le payload
    utilisateur_id = session.get("user_id") or data.get("user_id")
    
    if not question:
        return jsonify({"erreur": "question est requise"}), 400
    if not utilisateur_id:
        return jsonify({"erreur": "utilisateur non connecte"}), 401

    # Créer une nouvelle conversation si nécessaire
    if not conversation_id:
        titre = question[:50] + ("..." if len(question) > 50 else "")
        conversation_id = create_conversation(utilisateur_id, titre)
        if not conversation_id:
            return jsonify({"erreur": "impossible de creer la conversation"}), 500

    # Ajouter le message utilisateur
    add_message(conversation_id, "user", question)

    # Appeler le service de chat
    try:
        result = answer(question, history)
    except Exception as e:
        return jsonify({"erreur": str(e)}), 500

    # Ajouter la réponse du bot
    add_message(conversation_id, "bot", result.get("reponse", ""))

    result["conversation_id"] = conversation_id
    return jsonify(result)


@chat_bp.route("/api/conversations", methods=["GET"])
def liste_conversations():
    """Récupère toutes les conversations de l'utilisateur connecté"""
    utilisateur_id = session.get("user_id")
    if not utilisateur_id:
        return jsonify({"erreur": "utilisateur non connecte"}), 401

    conversations = get_conversations(utilisateur_id)
    return jsonify(conversations or [])


@chat_bp.route("/api/conversations/<int:conversation_id>/messages", methods=["GET"])
def messages_conversation(conversation_id):
    """Récupère tous les messages d'une conversation"""
    messages = get_messages(conversation_id)
    return jsonify(messages or [])


@chat_bp.route("/api/conversations/<int:conversation_id>", methods=["DELETE"])
def supprimer_conversation(conversation_id):
    """Supprime une conversation (vérifie que l'utilisateur en est le propriétaire)"""
    utilisateur_id = session.get("user_id")
    if not utilisateur_id:
        return jsonify({"erreur": "utilisateur non connecte"}), 401
    
    # Vérifier que la conversation appartient bien à l'utilisateur
    from db import get_connection
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id FROM conversations_chatbot WHERE id = %s AND utilisateur_id = %s",
        (conversation_id, utilisateur_id)
    )
    exists = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not exists:
        return jsonify({"erreur": "Conversation non trouvée ou non autorisée"}), 404
    
    result = delete_conversation(conversation_id)
    if not result:
        return jsonify({"erreur": "suppression echouee"}), 500
    return jsonify({"succes": True})