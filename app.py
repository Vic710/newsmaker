from flask import Flask, send_file, request, jsonify, render_template, redirect, url_for, session
from functools import wraps
import subprocess
import os
from drive_upload import upload_to_drive  # Import function

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "thisismysupersecretsecretkey")  # Use an env variable in production

# Hardcoded credentials (for now)
USERNAME = "admin"
PASSWORD = "password123"

PPT_FILE = "final_presentation.pptx"

# ---------------------
# Helper: login_required decorator
# ---------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated_function

# ---------------------
# Routes
# ---------------------

# Force the root URL to redirect to the login page
@app.route("/")
def root():
    return redirect(url_for("login_page"))

# Login page (GET shows form, POST processes login)
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        data = request.form
        if data.get("username") == USERNAME and data.get("password") == PASSWORD:
            session["user"] = USERNAME  # Set session
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid username or password")
    else:
        return render_template("login.html")

# Logout route (clears session)
@app.route("/logout")
@login_required
def logout():
    session.pop("user", None)
    return redirect(url_for("login_page"))

# Dashboard page; only accessible after login
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("index.html")

# Generate PPT route; protected by login
@app.route("/generate", methods=["POST"])
@login_required
def generate():
    try:
        subprocess.run(["python", "main.py"], check=True)
        if not os.path.exists(PPT_FILE):
            return jsonify({"success": False, "error": "Presentation file not found."}), 500

        slides_link, _ = upload_to_drive()
        print(f"Presentation ready: {PPT_FILE}, Google Slides link: {slides_link}")

        return jsonify({
            "success": True,
            "ppt_url": "/download",
            "slides_link": slides_link
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Download PPT route; protected by login
@app.route("/download")
@login_required
def download():
    if os.path.exists(PPT_FILE):
        return send_file(PPT_FILE, as_attachment=True,
                         mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation")
    else:
        return jsonify({"error": "PPT file not found."}), 404

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
