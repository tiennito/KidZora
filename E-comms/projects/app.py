from flask import Flask, request, jsonify, session, render_template
import firebase_admin
from firebase_admin import credentials, auth

app = Flask(__name__)
app.secret_key = "your-secret-key"

# ✅ Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate("projects/serviceAccountKey.json")  # download from Firebase Console
    firebase_admin.initialize_app(cred)

@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return "Unauthorized", 401
    return render_template("dashboard.html")

@app.route("/verify_token", methods=["POST"])
def verify_token():
    data = request.get_json()
    token = data.get("token")

    try:
        decoded_token = auth.verify_id_token(token)
        session["user"] = decoded_token["uid"]
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print("Token verification failed:", e)
        return jsonify({"error": str(e)}), 401

if __name__ == "__main__":
    app.run(debug=True)
