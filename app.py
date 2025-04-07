import os
import time
import threading
from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from flask_cors import CORS
import pyttsx3  # for TTS

app = Flask(__name__)
CORS(app)

# --------------------------------------------------------------------------------
# 1) In-memory data store: 'checked_in_patients'
# --------------------------------------------------------------------------------
checked_in_patients = []
"""
Example structure:
[
  {
    "name": "Will Smith",
    "arrived": "2025-04-06 10:15 AM",
    "status": "ready" or "called",
    "called_time": "<ISO8601 timestamp if status=='called'>"
  },
  ...
]
"""

# --------------------------------------------------------------------------------
# 2) TTS (text-to-speech) function
# --------------------------------------------------------------------------------
def announce_patient(name: str):
    """
    Speaks the patient's name over the default audio device (the machine
    running this code). Make sure that machine has a speaker as default output.
    """
    try:
        print(f"[TTS] Announcing: {name}")
        engine = pyttsx3.init()

        # Print out all voices. This helps you debug which voices are available.
        voices = engine.getProperty('voices')
        for i, v in enumerate(voices):
            print(f"[TTS] Voice #{i}: {v.id}")

        # Example: Pick the second available voice if it exists.
        if len(voices) > 1:
            engine.setProperty('voice', voices[1].id)
            print(f"[TTS] Using voice #{1}: {voices[1].id}")
        else:
            print("[TTS] Only one voice found. Using default voice.")

        # Quick test phrase so you can confirm TTS is working at runtime:
        engine.say("Testing, 1 2 3. Hello from pyttsx3!")

        # Actual announcement for the patient:
        phrase = f"{name}, please proceed to the doctor's office."
        engine.say(phrase)

        engine.runAndWait()
        print("[TTS] Done speaking.")
    except Exception as e:
        print(f"[ERROR] TTS announce_patient failed: {e}")

# --------------------------------------------------------------------------------
# 3) Cleanup Thread for "called" patients older than 3 hours
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
# 4) Flask Routes
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
    Mark a patient "called" + triggers TTS. 
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

            # Speak name in a background thread so we return immediately
            threading.Thread(target=announce_patient, args=(name,), daemon=True).start()
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
# 5) Start the app
# --------------------------------------------------------------------------------
if __name__ == "__main__":
    start_cleanup()
    # Run on localhost:5000
    app.run(debug=True, port=5000)
