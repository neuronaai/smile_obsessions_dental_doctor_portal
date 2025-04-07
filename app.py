from flask import Flask, request, render_template, jsonify
import threading
import time
from datetime import datetime, timedelta

app = Flask(__name__)

# In-memory store of patients
# We add an optional "called_time" so we can track how long they've been 'called'
checked_in_patients = []

@app.route('/')
def index():
    return render_template('index.html')  # references templates/index.html

@app.route('/api/current_list', methods=['GET'])
def get_current_list():
    """
    Returns the in-memory patients list as JSON
    e.g. [ { "name": "...", "arrived": "...", "status": "ready" }, ... ]
    """
    return jsonify(checked_in_patients)

@app.route('/api/call_in', methods=['POST'])
def call_in():
    """
    Called when doctor clicks the "Call In" button for a patient.
    JSON body: { "name": "Will Smith", "arrived": "2025-04-06 10:15 AM" }
    """
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"error":"No patient name"}), 400
    
    name = data["name"]
    for p in checked_in_patients:
        if p["name"] == name:
            p["status"] = "called"
            # Record the time we called them
            p["called_time"] = datetime.utcnow().isoformat()
            break
    
    return jsonify({"message": f"Called in {name}"}), 200

@app.route('/api/uncall', methods=['POST'])
def uncall():
    """
    Allows "un-calling" a patient if done accidentally.
    JSON body: { "name": "Will Smith" }
    Sets them back to "ready", removes any "called_time".
    """
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"error": "Missing name"}), 400
    
    name = data["name"]
    for p in checked_in_patients:
        if p["name"] == name:
            p["status"] = "ready"
            p.pop("called_time", None)  # remove the called_time field
            break
    
    return jsonify({"message": f"Uncalled {name}"}), 200

@app.route('/api/clear_list', methods=['POST'])
def clear_list():
    """
    Clears all patients from the in-memory list.
    A big "Clear List" button in the UI can call this.
    """
    checked_in_patients.clear()
    return jsonify({"message": "All patients cleared"}), 200

@app.route('/api/checked_in', methods=['POST'])
def post_checked_in():
    """
    Endpoint for receiving new check-ins from csv_api_checker.py
    
    JSON example:
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

    print(f"[INFO] Received check-in => {first} {last}, arrived {arrived}")

    checked_in_patients.append({
        "name": f"{first} {last}",
        "arrived": arrived,
        "status": "ready"
        # "called_time": None  # We'll add this only once they get "called"
    })

    return jsonify({"message":"OK"}), 200

def cleanup_thread():
    """
    Background thread that runs every minute.
    Removes any "called" patient older than 3 hours from 'called_time'.
    """
    while True:
        time.sleep(60)  # run every 60s
        now = datetime.utcnow()
        # We'll keep only patients who are either not 'called' or
        # have been called less than 3 hours
        updated_list = []
        for p in checked_in_patients:
            if p["status"] == "called" and "called_time" in p:
                dt = datetime.fromisoformat(p["called_time"])
                if now - dt > timedelta(hours=3):
                    # skip them => remove from list
                    print(f"[CLEANUP] Removing {p['name']} (called over 3 hours ago)")
                    continue
            # otherwise keep them
            updated_list.append(p)
        
        # replace the list in place
        checked_in_patients.clear()
        checked_in_patients.extend(updated_list)

# Start the background cleanup thread
def start_cleanup():
    t = threading.Thread(target=cleanup_thread, daemon=True)
    t.start()

if __name__ == "__main__":
    start_cleanup()
    app.run(debug=True, port=5000)
