from flask import Flask, render_template, request, redirect, url_for, session
from flask_cors import CORS
from werkzeug.security import check_password_hash
from functools import wraps

from db import get_connection
from api_correction_route import correction_bp
from api_predict_route import predict_bp
from api_chat_route import chat_bp
from api_admin_route import admin_bp
from api_history_route import history_bp
from api_knowledge_route import knowledge_bp
from api_mesures_route import mesures_bp
from api_notifications_route import notifications_bp

app = Flask(
    __name__,
    template_folder="plateforme/templates",
    static_folder="plateforme/static",
)
app.secret_key = "dev-secret-key-a-changer"
CORS(app)

# Enregistrement des blueprints
app.register_blueprint(predict_bp)
app.register_blueprint(correction_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(history_bp)
app.register_blueprint(knowledge_bp)
app.register_blueprint(mesures_bp)
app.register_blueprint(notifications_bp)

# ============ CONTEXT PROCESSOR POUR LA SIDEBAR ============
@app.context_processor
def inject_menus():
    role = session.get('user_role', '')
    menus = []

    if role == 'ADMIN':
        menus = [
            {'name': 'Tableau de bord', 'url': '/dashboard', 'icon': 'dashboard', 'badge': 'live'},
            {'name': 'Prédiction & Correction', 'url': '/correction', 'icon': 'correction'},
            {'name': 'Historique corrections', 'url': '/historique-corrections', 'icon': 'history'},
            {'name': 'Mesures laboratoire', 'url': '/mesures-laboratoire', 'icon': 'lab'},
            {'name': 'Historique mesures', 'url': '/historique-mesures-laboratoire', 'icon': 'history_lab'},
            {'name': 'Assistant Chatbot', 'url': '/chatbot', 'icon': 'chat', 'badge': 'new'},
            {'name': 'Gestion des utilisateurs', 'url': '/administration', 'icon': 'users'},
            {'name': 'Base de connaissance', 'url': '/administration/base-connaissance', 'icon': 'knowledge'},
        ]
    elif role == 'OUVRIER':
        menus = [
            {'name': 'Tableau de bord', 'url': '/dashboard', 'icon': 'dashboard', 'badge': 'live'},
            {'name': 'Prédiction & Correction', 'url': '/correction', 'icon': 'correction'},
            {'name': 'Historique corrections', 'url': '/historique-corrections', 'icon': 'history'},
            {'name': 'Mesures laboratoire', 'url': '/mesures-laboratoire', 'icon': 'lab'},
            {'name': 'Historique mesures', 'url': '/historique-mesures-laboratoire', 'icon': 'history_lab'},
            {'name': 'Assistant Chatbot', 'url': '/chatbot', 'icon': 'chat', 'badge': 'new'},
        ]
    elif role == 'TECHNICIEN_LABO':
        menus = [
            {'name': 'Tableau de bord', 'url': '/dashboard', 'icon': 'dashboard', 'badge': 'live'},
            {'name': 'Mesures laboratoire', 'url': '/mesures-laboratoire', 'icon': 'lab'},
            {'name': 'Historique mesures', 'url': '/historique-mesures-laboratoire', 'icon': 'history_lab'},
            {'name': 'Assistant Chatbot', 'url': '/chatbot', 'icon': 'chat', 'badge': 'new'},
        ]
    elif role == 'STAGIAIRE':
        menus = [
            {'name': 'Assistant Chatbot', 'url': '/chatbot', 'icon': 'chat', 'badge': 'new'},
        ]
    else:
        menus = []

    return dict(menus=menus, user_role=role)

# ============ ROUTES DES PAGES ============

@app.route("/")
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login_submit():
    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        return render_template("login.html", error="Email et mot de passe requis.")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM utilisateurs WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user or not check_password_hash(user["mot_de_passe"], password):
        return render_template("login.html", error="Email ou mot de passe incorrect.")

    session["user_id"] = user["id"]
    session["user_email"] = user["email"]
    session["user_nom"] = user["nom"]
    session["user_prenom"] = user["prenom"]
    session["user_role"] = user["role"]

    # Redirection selon le rôle
    if user["role"] == "STAGIAIRE":
        return redirect(url_for("chatbot_page"))
    else:
        return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

# ============ PROTECTION PAR RÔLE ============

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_role" not in session:
                return redirect(url_for("login_page"))
            if session["user_role"] not in allowed_roles:
                # Si stagiaire, rediriger vers chatbot
                if session["user_role"] == "STAGIAIRE":
                    return redirect(url_for("chatbot_page"))
                # Sinon vers dashboard
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ============ PAGES PRINCIPALES ============

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    # Stagiaire redirigé vers chatbot
    if session.get("user_role") == "STAGIAIRE":
        return redirect(url_for("chatbot_page"))
    return render_template("dashboard.html")

@app.route("/correction")
@role_required(["ADMIN", "OUVRIER"])
def correction_page():
    return render_template("correction.html")

@app.route("/historique-corrections")
@role_required(["ADMIN", "OUVRIER"])
def historique_page():
    return render_template("historique.html")

@app.route("/mesures-laboratoire")
@role_required(["ADMIN", "OUVRIER", "TECHNICIEN_LABO"])
def mesures_laboratoire():
    return render_template("mesures_laboratoire.html")

@app.route("/historique-mesures-laboratoire")
@role_required(["ADMIN", "OUVRIER", "TECHNICIEN_LABO"])
def historique_mesures_page():
    return render_template("historique_mesures.html")

@app.route("/chatbot")
def chatbot_page():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return render_template("chat.html")

@app.route("/administration")
@role_required(["ADMIN"])
def administration_page():
    return render_template("admin_users.html")

@app.route("/administration/base-connaissance")
@role_required(["ADMIN"])
def base_connaissance_page():
    return render_template("base_connaissance.html")

# ============ DÉMARRAGE ============
if __name__ == "__main__":
    app.run(debug=True, port=5000)