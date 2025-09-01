import firebase_admin
from firebase_admin import credentials, auth, db
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

# -----------------------
# CONFIG
# -----------------------
app = Flask(__name__)
app.secret_key = "BlwlibOugl4bvB77mqgo7VJhYMT03zyPNFgdq1oh"

# Initialize Firebase Admin SDK
cred = credentials.Certificate("projects/serviceAccountKey.json")
firebase_admin.initialize_app(cred, {"databaseURL": "https://kidzora-a3808-default-rtdb.firebaseio.com/"})

# -----------------------
# ROUTES
# -----------------------

@app.route("/")
def home():
    return redirect(url_for("login"))

# SIGNUP (creates Firebase user)
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        re_password = request.form.get("re_password")

        if password != re_password:
            flash("Passwords do not match!")
            return redirect(url_for("signup"))

        if not email or "@" not in email:
            flash("Please enter a valid email!")
            return redirect(url_for("signup"))

        if len(password) < 6:
            flash("Password must be at least 6 characters")
            return redirect(url_for("signup"))

        try:
            # 1️⃣ Create user in Firebase Authentication
            user = auth.create_user(
                email=email,
                password=password,
                display_name=name
            )

            # 2️⃣ Save user info in Firebase Realtime Database
            ref = db.reference(f"users/{user.uid}")
            ref.set({
                "name": name,
                "email": email
            })

            flash("Account created successfully! Please log in.")
            return redirect(url_for("login"))

        except Exception as e:
            flash(f"Error creating account: {e}")
            return redirect(url_for("signup"))

    return render_template("signup.html")


# LOGIN (handled by frontend with Firebase JS SDK)
@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")

# Verify token sent from frontend
@app.route("/verify_token", methods=["POST"])
def verify_token():
    data = request.get_json()
    token = data.get("token")
    try:
        decoded_token = auth.verify_id_token(token)
        session["user"] = decoded_token
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", user=session["user"])

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out successfully.")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
