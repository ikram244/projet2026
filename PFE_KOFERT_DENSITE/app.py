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

app.register_blueprint(predict_bp)
app.register_blueprint(correction_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(history_bp)
app.register_blueprint(knowledge_bp)
app.register_blueprint(mesures_bp)
app.register_blueprint(notifications_bp)

@app.route("/")
def login():
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

    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/correction")
def correction_page():
    return render_template("correction.html")


@app.route("/chatbot")
def chatbot_page():
    return render_template("chat.html")


@app.route("/historique-corrections")
def historique_page():
    return render_template("historique.html")


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("user_role") != "ADMIN":
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/administration")
@admin_required
def administration_page():
    return render_template("admin_users.html")


@app.route("/administration/base-connaissance")
@admin_required
def base_connaissance_page():
    return render_template("base_connaissance.html")


@app.route("/mesures-laboratoire")
def mesures_laboratoire():
    return render_template("mesures_laboratoire.html")



@app.route("/historique-mesures-laboratoire")
def historique_mesures_page():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("historique_mesures.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)