import os
import time
import threading
from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ------------------------------------------------------------------------------
# 1) In-memory data store:
#    A) 'checked_in_patients'
#    B) 'patients_in_queue'
# ------------------------------------------------------------------------------
checked_in_patients = []
"""
checked_in_patients = [
  {
    "name": "Will Smith",
    "arrived": "2025-04-06 10:15 AM",
    "status": "ready" or "called",
    "called_time": "<ISO8601 timestamp if status=='called'>"
  },
  ...
]
"""

patients_in_queue = []
"""
patients_in_queue = [
  {
    "pat_num": 12345,
    "name": "Test Patient",
    "date_added": "2025-04-23T14:22:00Z"
    // potentially "status": "scheduled" or something
  },
  ...
]
"""

# ------------------------------------------------------------------------------
# 2) Cleanup Thread (for called patients in "checked_in_patients")
#    If you also want to remove old queue items, you can adapt similarly
# ------------------------------------------------------------------------------
def cleanup_thread():
    """
    Runs every 60s, removing 'called' patients if their called_time is over 3 hours.
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

        checked_in_patients.clear()
        checked_in_patients.extend(updated)

def start_cleanup():
    t = threading.Thread(target=cleanup_thread, daemon=True)
    t.start()

# ------------------------------------------------------------------------------
# 3) Flask Routes
# ------------------------------------------------------------------------------
@app.route("/")
def index():
    # Renders the main Doctor Dashboard (templates/index.html)
    return render_template("index.html")

# ------------------ A) "Checked-in" Endpoints ------------------
@app.route("/api/current_list", methods=["GET"])
def get_current_list():
    """
    Returns the entire in-memory list of checked-in patients as JSON.
    """
    return jsonify(checked_in_patients)

@app.route("/api/checked_in", methods=["POST"])
def post_checked_in():
    """
    Endpoint for new check-ins. JSON example:
        {
          "first_name": "Will",
          "last_name": "Smith",
          "arrived_at": "2025-04-06 10:15 AM"
        }
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON provided"}), 400

    first = data.get("first_name")
    last  = data.get("last_name")
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
    Mark a patient "called" (server only updates in memory).
    The browser will handle TTS with Web Speech API.
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
    Clears all patients from the in-memory list.
    """
    checked_in_patients.clear()
    print("[INFO] All patients cleared.")
    return jsonify({"message": "All patients cleared"}), 200

# ------------------ B) "Patients in Queue" Endpoints ------------------
@app.route("/api/patients_in_queue", methods=["GET"])
def get_patients_in_queue():
    """
    Returns the entire in-memory list of patients in the queue as JSON.
    """
    return jsonify(patients_in_queue)

@app.route("/api/add_to_queue", methods=["POST"])
def add_to_queue():
    """
    Called by the main app if it detects a patient has a same-day appointment.
    JSON example:
        {
          "pat_num": 137768,
          "first_name": "Will",
          "last_name": "Smith"
        }
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON provided"}), 400

    pat_num = data.get("pat_num")
    f = data.get("first_name", "")
    l = data.get("last_name", "")

    if not pat_num or not f or not l:
        return jsonify({"error": "Missing 'pat_num' or name"}), 400

    # Build queue object
    queue_obj = {
        "pat_num": pat_num,
        "name": f"{f} {l}",
        "date_added": datetime.utcnow().isoformat()
    }
    patients_in_queue.append(queue_obj)
    print(f"[INFO] Added to queue => {queue_obj}")

    return jsonify({"message": "Successfully queued"}), 200

@app.route("/api/clear_queue", methods=["POST"])
def clear_queue():
    """
    Clears all patients from the in-memory 'patients_in_queue' list
    """
    patients_in_queue.clear()
    print("[INFO] All queue patients cleared.")
    return jsonify({"message": "Queue cleared"}), 200

# --------------------------------------------------------------------------------
# 4) Start the app
# --------------------------------------------------------------------------------
if __name__ == "__main__":
    start_cleanup()
    app.run(debug=True, port=5000)
