from flask import Flask, send_file, request, jsonify, render_template
import subprocess
import os
from drive_upload import upload_to_drive  # Import function

app = Flask(__name__, template_folder="templates", static_folder="static")

PPT_FILE = "final_presentation.pptx"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    try:
        # Run the main pipeline (which should generate `final_presentation.pptx`)
        subprocess.run(["python", "main.py"], check=True)

        if not os.path.exists(PPT_FILE):
            return jsonify({"success": False, "error": "Presentation file not found."}), 500

        # Upload to Google Drive & get the link
        slides_link, _ = upload_to_drive()

        print(f"Presentation ready: {PPT_FILE}, Google Slides link: {slides_link}")

        # **Return JSON response instead of forcing file download**
        return jsonify({
            "success": True,
            "ppt_url": "/download",
            "slides_link": slides_link
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/download")
def download():
    """Serve the generated PPT file."""
    if os.path.exists(PPT_FILE):
        return send_file(PPT_FILE, as_attachment=True,
                         mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation")
    else:
        return jsonify({"error": "PPT file not found."}), 404

if __name__ == "__main__":
    app.run(debug=True)
