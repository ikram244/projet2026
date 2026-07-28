from flask import Flask, render_template
from flask_cors import CORS

from api_correction_route import correction_bp
from api_predict_route import predict_bp
from api_chat_route import chat_bp

app = Flask(
    __name__,
    template_folder="plateforme/templates",
    static_folder="plateforme/static",
)
CORS(app)

app.register_blueprint(predict_bp)
app.register_blueprint(correction_bp)
app.register_blueprint(chat_bp)


@app.route("/")
def login():
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/correction")
def correction_page():
    return render_template("correction.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)