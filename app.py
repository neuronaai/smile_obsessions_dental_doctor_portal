import os
import time
import threading
import requests
from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ------------------------------------------------------------------------------
# 1) In-memory data store
# ------------------------------------------------------------------------------
checked_in_patients = []
"""
checked_in_patients = [
  {
    "name": "Will Smith",
    "arrived": "2025-04-06 10:15",
    "status": "ready" or "called",
    "called_time": "<ISO8601> if 'called'"
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
  },
  ...
]
"""

# ------------------------------------------------------------------------------
# 2) OD Credentials for GET /appointments?PatNum=...
# ------------------------------------------------------------------------------
OD_DEVELOPER_KEY = os.environ.get("OD_API_DEV_KEY", "A0NnBNFvx4DjbwRb")
OD_CUSTOMER_KEY  = os.environ.get("OD_API_CUST_KEY", "JQ1BkECEdo3XILEy")
OD_BASE_URL = "https://api.opendental.com/api/v1"
OD_HEADERS = {
    "Authorization": f"ODFHIR {OD_DEVELOPER_KEY}/{OD_CUSTOMER_KEY}",
    "Content-Type": "application/json"
}

# ------------------------------------------------------------------------------
# 3) Threads
#    A) cleanup_thread => remove "called" > 3h
#    B) queue_monitor_thread => checks DateTimeArrived
# ------------------------------------------------------------------------------
def cleanup_thread():
    """
    Every 60s, remove 'called' patients if > 3 hours since 'called_time'.
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

        # We do not need global here because we're not reassigning the entire list
        checked_in_patients.clear()
        checked_in_patients.extend(updated)

def queue_monitor_thread():
    """
    Every 30s => for each pat in queue:
      1) GET /appointments?PatNum=xxx
      2) If any apt's DateTimeArrived != "0001-01-01 00:00:00"
         and doesn't end in "00:00:00", they are arrived => move them to checked_in
      3) Wait 11s before next pat => no overlap calls
    """
    while True:
        time.sleep(30)

        # snapshot in case the queue changes while we iterate
        queue_copy = patients_in_queue[:]
        for q in queue_copy:
            pat_num = q["pat_num"]
            name    = q["name"]
            apt_url = f"{OD_BASE_URL}/appointments?PatNum={pat_num}"
            try:
                resp = requests.get(apt_url, headers=OD_HEADERS, timeout=5)
                if resp.ok:
                    appointments = resp.json()
                    arrived_found = False
                    for apt in appointments:
                        dt_arrived_str = apt.get("DateTimeArrived", "")
                        # e.g. "2025-04-21 00:00:00" => if last 8 != "00:00:00", they're arrived
                        if dt_arrived_str and not dt_arrived_str.startswith("0001-01-01"):
                            if dt_arrived_str[-8:] != "00:00:00":
                                arrived_found = True
                                break
                    if arrived_found:
                        print(f"[QUEUE] {name} => DateTimeArrived changed => move to checked_in.")
                        remove_from_queue(pat_num)
                        checked_in_patients.append({
                            "name": name,
                            "arrived": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                            "status": "ready"
                        })
                else:
                    print(f"[WARN] /appointments => {resp.status_code} {resp.text}")
            except requests.RequestException as e:
                print("[ERROR] queue_monitor_thread =>", e)

            time.sleep(11)  # wait 11s before next pat

def remove_from_queue(pat_num):
    """
    Helper => remove single pat_num from patients_in_queue
    """
    global patients_in_queue  # we fully reassign the list below

    new_q = []
    for q in patients_in_queue:
        if q["pat_num"] != pat_num:
            new_q.append(q)
    patients_in_queue = new_q

def start_threads():
    t1 = threading.Thread(target=cleanup_thread, daemon=True)
    t1.start()
    t2 = threading.Thread(target=queue_monitor_thread, daemon=True)
    t2.start()

# ------------------------------------------------------------------------------
# 4) Flask Routes
# ------------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

# A) Checked-In Endpoints
@app.route("/api/current_list", methods=["GET"])
def get_current_list():
    return jsonify(checked_in_patients)

@app.route("/api/checked_in", methods=["POST"])
def post_checked_in():
    """
    Called to add a patient directly to 'checked_in'.
    JSON: { "first_name":..., "last_name":..., "arrived_at":... }
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON provided"}), 400

    first = data.get("first_name")
    last  = data.get("last_name")
    arrived = data.get("arrived_at", datetime.utcnow().strftime("%Y-%m-%d %H:%M"))

    if not first or not last:
        return jsonify({"error": "Missing name fields"}), 400

    obj = {
        "name": f"{first} {last}",
        "arrived": arrived,
        "status": "ready"
    }
    checked_in_patients.append(obj)
    print(f"[INFO] Received check-in => {obj}")
    return jsonify({"message": "OK"}), 200

@app.route("/api/call_in", methods=["POST"])
def call_in():
    """
    Mark a patient "called".
    JSON: { "name": "Will Smith" }
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
    Revert "called" -> "ready".
    JSON: { "name": "Will Smith" }
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
    checked_in_patients.clear()
    print("[INFO] All checked_in patients cleared.")
    return jsonify({"message": "All patients cleared"}), 200

# B) Patients in Queue
@app.route("/api/patients_in_queue", methods=["GET"])
def get_patients_in_queue():
    return jsonify(patients_in_queue)

@app.route("/api/add_to_queue", methods=["POST"])
def add_to_queue():
    """
    JSON: { "pat_num":..., "first_name":..., "last_name":... }
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON provided"}), 400

    pat_num = data.get("pat_num")
    f = data.get("first_name", "")
    l = data.get("last_name", "")

    if not pat_num or not f or not l:
        return jsonify({"error": "Missing pat_num or name fields"}), 400

    q_obj = {
        "pat_num": pat_num,
        "name": f"{f} {l}",
        "date_added": datetime.utcnow().isoformat()
    }
    patients_in_queue.append(q_obj)
    print(f"[INFO] Added to queue => {q_obj}")
    return jsonify({"message": "Successfully queued"}), 200

@app.route("/api/clear_queue", methods=["POST"])
def clear_queue():
    patients_in_queue.clear()
    print("[INFO] All queue patients cleared.")
    return jsonify({"message": "Queue cleared"}), 200

# C) Manually move from queue -> checked_in
@app.route("/api/queue_to_checked_in", methods=["POST"])
def queue_to_checked_in():
    """
    JSON: { "pat_num": 12345, "arrived_at": "2025-04-23 09:00" (optional) }
    """
    data = request.json
    if not data or "pat_num" not in data:
        return jsonify({"error": "Missing pat_num"}), 400

    global patients_in_queue
    pat_num = data["pat_num"]
    arrived_str = data.get("arrived_at", datetime.utcnow().strftime("%Y-%m-%d %H:%M"))

    removed = None
    new_q = []
    for q in patients_in_queue:
        if q["pat_num"] == pat_num:
            removed = q
        else:
            new_q.append(q)
    patients_in_queue = new_q

    if removed:
        checked_in_patients.append({
            "name": removed["name"],
            "arrived": arrived_str,
            "status": "ready"
        })
        return jsonify({"message": f"Moved {removed['name']} to checked_in."}), 200
    else:
        return jsonify({"error": f"No queue patient with pat_num={pat_num}"}), 404

# D) Manually move from checked_in -> queue
@app.route("/api/checked_in_to_queue", methods=["POST"])
def checked_in_to_queue():
    """
    JSON: { "name": "Will Smith", "pat_num": 12345 (optional) }
    """
    global checked_in_patients

    data = request.json
    if not data or "name" not in data:
        return jsonify({"error": "Missing 'name'"}), 400

    name = data["name"]
    pat_num = data.get("pat_num", 0)

    removed = None
    new_list = []
    for p in checked_in_patients:
        if p["name"] == name:
            removed = p
        else:
            new_list.append(p)

    checked_in_patients = new_list

    if removed:
        q_obj = {
            "pat_num": pat_num,
            "name": removed["name"],
            "date_added": datetime.utcnow().isoformat()
        }
        patients_in_queue.append(q_obj)
        return jsonify({"message": f"Moved {removed['name']} to queue."}), 200
    else:
        return jsonify({"error": f"No checked_in patient found with name={name}"}), 404

# ------------------------------------------------------------------------------
# 5) Start the app
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    start_threads()
    app.run(debug=True, port=5000)
