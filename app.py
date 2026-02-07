import os
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_file
from dotenv import load_dotenv

from video_engine import build_video

load_dotenv()

app = Flask(__name__)
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/generate")
def generate_video():
    body = request.get_json(silent=True) or {}
    mood = (body.get("mood") or "cold").lower()
    language = (body.get("language") or "english").lower()

    if mood not in {"cold", "dark", "calm"}:
        return jsonify({"error": "Mood must be one of: cold, dark, calm."}), 400
    if language != "english":
        return jsonify({"error": "Only English is supported."}), 400

    try:
        result = build_video(mood=mood, output_dir=OUTPUT_DIR)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.get("/download/<path:filename>")
def download(filename: str):
    target = OUTPUT_DIR / filename
    if not target.exists():
        return jsonify({"error": "File not found."}), 404
    return send_file(target, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
