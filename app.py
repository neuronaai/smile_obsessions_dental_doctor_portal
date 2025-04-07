import os
import csv
import time
import threading
from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from flask_cors import CORS
import pyttsx3  # for TTS

app = Flask(__name__)
CORS(app)

# ----------------------------
# 1) In-memory store
# ----------------------------
checked_in_patients = []
"""
Format of each patient object:
{
  "name": "Will Smith",
  "arrived": "2025-04-06 10:15 AM",
  "status": "ready" or "called",
  "called_time": "<iso8601 timestamp>" (only if 'status' = 'called')
}
"""

# ----------------------------
# 2) TTS function
# ----------------------------
def announce_patient(name: str):
    """
    Speaks the patient's name out loud over the local machine's default audio device.
    Make sure your Bluetooth speaker is set as the default output.
    """
    try:
        engine = pyttsx3.init()
        # Optional: tweak voice or rate:
        # engine.setProperty('rate', 150)
        phrase = f"{name}, please proceed to the doctor's office."
        engine.say(phrase)
        engine.runAndWait()
    except Exception as e:
        print(f"[ERROR] TTS announce_patient failed: {e}")

# ----------------------------
# 3) Cleanup thread
# ----------------------------
def cleanup_thread():
    """
    Runs every 60s, removing 'called' patients older than 3 hours.
    """
    while True:
        time.sleep(60)
        now = datetime.utcnow()
        updated = []
        for p in checked_in_patients:
            if p["status"] == "called" and "called_time" in p:
                dt_called = datetime.fromisoformat(p["called_time"])
                if now - dt_called > timedelta(hours=3):
                    print(f"[CLEANUP] Removing {p['name']} (called >3h ago)")
                    continue
            updated.append(p)
        # replace the global list in place
        checked_in_patients.clear()
        checked_in_patients.extend(updated)

def start_cleanup():
    t = threading.Thread(target=cleanup_thread, daemon=True)
    t.start()

# ----------------------------
# 4) Routes
# ----------------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/current_list", methods=["GET"])
def get_current_list():
    """
    Returns the in-memory patients list as JSON
    e.g. [ { "name": "...", "arrived": "...", "status": "ready" }, ... ]
    """
    return jsonify(checked_in_patients)

@app.route("/api/checked_in", methods=["POST"])
def post_checked_in():
    """
    Called by CSV checker or Emmersa to register new check-ins.
    Body example:
    {
      "first_name": "Will",
      "last_name": "Smith",
      "arrived_at": "2025-04-06 10:15 AM"
    }
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON"}), 400

    first = data.get("first_name")
    last = data.get("last_name")
    arrived = data.get("arrived_at", "Unknown")

    # Simple format
    patient_obj = {
        "name": f"{first} {last}",
        "arrived": arrived,
        "status": "ready"
    }
    checked_in_patients.append(patient_obj)
    print(f"[INFO] Received check-in => {patient_obj}")

    return jsonify({"message": "OK"}), 200

@app.route("/api/call_in", methods=["POST"])
def call_in():
    """
    Doctor clicks 'Call In', sets the patient's status to 'called',
    and triggers TTS.
    JSON Body: { "name": "Will Smith" }
    """
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"error": "No patient name"}), 400

    name = data["name"]
    for p in checked_in_patients:
        if p["name"] == name and p["status"] == "ready":
            p["status"] = "called"
            p["called_time"] = datetime.utcnow().isoformat()

            # Speak the name in a background thread so we return immediately
            threading.Thread(target=announce_patient, args=(p["name"],), daemon=True).start()
            break
    return jsonify({"message": f"Called in {name}"}), 200

@app.route("/api/uncall", methods=["POST"])
def uncall():
    """
    Allows the doctor to revert a 'called' patient back to 'ready' if it was a mistake.
    JSON Body: { "name": "Will Smith" }
    """
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"error": "No patient name"}), 400

    name = data["name"]
    for p in checked_in_patients:
        if p["name"] == name and p["status"] == "called":
            p["status"] = "ready"
            p.pop("called_time", None)
            break
    return jsonify({"message": f"Uncalled {name}"}), 200

@app.route("/api/clear_list", methods=["POST"])
def clear_list():
    """
    Clears all patients from the in-memory list.
    Typically behind a big 'Clear List' button in the UI.
    """
    checked_in_patients.clear()
    return jsonify({"message": "All patients cleared"}), 200

# ----------------------------
# 5) Start app + background cleanup
# ----------------------------
if __name__ == "__main__":
    start_cleanup()  # start the thread that prunes called patients after 3h
    app.run(debug=True, port=5000)
