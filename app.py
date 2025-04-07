import os
import time
import threading
from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --------------------------------------------------------------------------------
# 1) In-memory data store: 'checked_in_patients'
# --------------------------------------------------------------------------------
# We'll still include one dummy patient to test calling in immediately.
checked_in_patients = [
    {
        "name": "John Doe",
        "arrived": "2025-04-09 09:00 AM",
        "status": "ready"
        # "called_time": None  <-- not set until they're called
    }
]
"""
Structure of each entry:
{
  "name": "Will Smith",
  "arrived": "2025-04-06 10:15 AM",
  "status": "ready" or "called",
  "called_time": "<ISO8601 timestamp if status=='called'>"
}
"""

# --------------------------------------------------------------------------------
# 2) Cleanup Thread for "called" patients older than 3 hours
# --------------------------------------------------------------------------------
def cleanup_thread():
    """
    Runs every 60s, removing 'called' patients if their called_time is over 3 hours ago.
    """
    while True:
        time.sleep(60)
        now = datetime.utcnow()
        updated = []
        for p in checked_in_patients:
            if p["status"] == "called" and "called_time" in p:
                dt_called = datetime.fromisoformat(p["called_time"])
                if now - dt_called > timedelta(hours=3):
                    print(f"[CLEANUP] Removing {p['name']} (called > 3h ago).")
                    continue
            updated.append(p)

        # Replace the global list in place
        checked_in_patients.clear()
        checked_in_patients.extend(updated)

def start_cleanup():
    t = threading.Thread(target=cleanup_thread, daemon=True)
    t.start()

# --------------------------------------------------------------------------------
# 3) Flask Routes
# --------------------------------------------------------------------------------
@app.route("/")
def index():
    # Renders the main Doctor Dashboard (templates/index.html)
    return render_template("index.html")

@app.route("/api/current_list", methods=["GET"])
def get_current_list():
    """
    Returns the entire in-memory list of patients as JSON.
    """
    return jsonify(checked_in_patients)

@app.route("/api/checked_in", methods=["POST"])
def post_checked_in():
    """
    Endpoint for new check-ins. Expects JSON like:
        {
          "first_name": "Will",
          "last_name": "Smith",
          "arrived_at": "2025-04-06 10:15 AM"
        }
    Appends a dict to checked_in_patients with status = "ready".
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON provided"}), 400

    first = data.get("first_name")
    last = data.get("last_name")
    arrived = data.get("arrived_at", "Unknown")

    if not first or not last:
        return jsonify({"error": "Missing name fields"}), 400

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
    Mark a patient "called" (the front-end will do browser-based TTS).
    JSON body: { "name": "Will Smith" }
    """
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"error": "No patient name"}), 400

    name = data["name"]
    found_any = False

    for p in checked_in_patients:
        if p["name"] == name and p["status"] == "ready":
            p["status"] = "called"
            p["called_time"] = datetime.utcnow().isoformat()
            found_any = True
            break

    if not found_any:
        return jsonify({"error": f"No 'ready' patient found with name '{name}'"}), 404

    return jsonify({"message": f"Called in {name}"}), 200

@app.route("/api/uncall", methods=["POST"])
def uncall():
    """
    Revert a 'called' patient back to 'ready'.
    JSON body: { "name": "Will Smith" }
    """
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"error": "No patient name"}), 400

    name = data["name"]
    found_any = False

    for p in checked_in_patients:
        if p["name"] == name and p["status"] == "called":
            p["status"] = "ready"
            p.pop("called_time", None)
            found_any = True
            break

    if not found_any:
        return jsonify({"error": f"No 'called' patient found with name '{name}'"}), 404

    return jsonify({"message": f"Uncalled {name}"}), 200

@app.route("/api/clear_list", methods=["POST"])
def clear_list():
    """
    Clears all patients from the list.
    """
    checked_in_patients.clear()
    print("[INFO] All patients cleared.")
    return jsonify({"message": "All patients cleared"}), 200

# --------------------------------------------------------------------------------
# 4) Start the app
# --------------------------------------------------------------------------------
if __name__ == "__main__":
    start_cleanup()
    app.run(debug=True, port=5000)
