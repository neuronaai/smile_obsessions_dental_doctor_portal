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
# 1) In-memory data
# ------------------------------------------------------------------------------
checked_in_patients = []
"""
checked_in_patients = [
  {
    "name": "Will Smith",
    "pat_num": 1234, 
    "arrived": "2025-04-06 10:15",
    "status": "ready" or "called",
    "called_time": "<ISO8601> if called"
  },
  ...
]
"""

auto_queue = []
"""
auto_queue = [
  {
    "pat_num": 9999,
    "name": "Testing Person",
    "date_added": "2025-04-23T14:22:00Z"
  },
  ...
]
"""

doctor_queue = []
"""
doctor_queue = [
  {
    "pat_num": 1111,
    "name": "Manual Person",
    "date_added": "2025-04-23T14:22:00Z"
  },
  ...
]
"""

# ------------------------------------------------------------------------------
# 2) OD Credentials (for background checking DateTimeArrived)
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
# ------------------------------------------------------------------------------
def cleanup_thread():
    """
    Every 60s, remove 'called' patients if more than 3 hours old.
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

def auto_queue_monitor_thread():
    """
    Every 30s => check all patients in auto_queue:
      /appointments?PatNum=xxx 
      -> if DateTimeArrived != '00:00:00', move them to checked_in
      -> remove from auto_queue
      Wait 11s between each patient to avoid overlap
    """
    while True:
        time.sleep(30)
        queue_snapshot = auto_queue[:]  # copy so we don't skip items if we remove them
        for q in queue_snapshot:
            pat_num = q["pat_num"]
            name    = q["name"]
            apt_url = f"{OD_BASE_URL}/appointments?PatNum={pat_num}"
            try:
                resp = requests.get(apt_url, headers=OD_HEADERS, timeout=5)
                if resp.ok:
                    appts = resp.json()
                    arrived_found = False
                    for apt in appts:
                        dt_arrived = apt.get("DateTimeArrived", "")
                        # if it's not "0001-01-01 ..." or doesn't end with "00:00:00", we treat them as arrived
                        if dt_arrived and not dt_arrived.startswith("0001-01-01"):
                            if dt_arrived[-8:] != "00:00:00":
                                arrived_found = True
                                break
                    if arrived_found:
                        print(f"[AUTO-QUEUE] {name} => arrived => move to checked_in.")
                        remove_from_auto_queue(pat_num)
                        checked_in_patients.append({
                            "name": name,
                            "pat_num": pat_num,
                            "arrived": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                            "status": "ready"
                        })
                else:
                    print(f"[WARN] GET {apt_url} => {resp.status_code}, {resp.text}")

            except requests.RequestException as e:
                print("[ERROR] auto_queue_monitor_thread =>", e)

            time.sleep(11)

def remove_from_auto_queue(pat_num):
    global auto_queue
    new_list = []
    for q in auto_queue:
        if q["pat_num"] != pat_num:
            new_list.append(q)
    auto_queue = new_list

def start_threads():
    t1 = threading.Thread(target=cleanup_thread, daemon=True)
    t1.start()
    t2 = threading.Thread(target=auto_queue_monitor_thread, daemon=True)
    t2.start()

# ------------------------------------------------------------------------------
# 4) Flask Routes
# ------------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

# -------------- A) CHECKED-IN PATIENTS --------------
@app.route("/api/checked_in_list", methods=["GET"])
def get_checked_in_list():
    return jsonify(checked_in_patients)

@app.route("/api/call_in", methods=["POST"])
def call_in():
    """
    JSON: { "name":"...", "pat_num":xxx }
    Mark them status="called" => possible TTS call
    """
    data = request.json
    if not data or "name" not in data:
        return jsonify({"error":"Missing name"}), 400

    name = data["name"]
    found = False
    for p in checked_in_patients:
        # match on pat_num if you want to be safer
        if p["name"] == name and p["status"] == "ready":
            p["status"] = "called"
            p["called_time"] = datetime.utcnow().isoformat()
            found = True
            break

    if not found:
        return jsonify({"error":f"No 'ready' patient named '{name}'"}),404

    return jsonify({"message":f"Called in {name}"}),200

@app.route("/api/uncall", methods=["POST"])
def uncall():
    """
    JSON: { "name":"...", "pat_num":xxx }
    Revert them from "called" => "ready"
    """
    data = request.json
    if not data or "name" not in data:
        return jsonify({"error":"Missing name"}),400

    name = data["name"]
    found = False
    for p in checked_in_patients:
        if p["name"] == name and p["status"]=="called":
            p["status"] = "ready"
            p.pop("called_time",None)
            found = True
            break
    if not found:
        return jsonify({"error":f"No 'called' patient with name {name}"}),404

    return jsonify({"message":f"Uncalled {name}"}),200

@app.route("/api/clear_checked_in", methods=["POST"])
def clear_checked_in():
    checked_in_patients.clear()
    return jsonify({"message":"All checked_in cleared"}),200

# -------------- B) AUTO QUEUE --------------
@app.route("/api/auto_queue_list", methods=["GET"])
def get_auto_queue_list():
    return jsonify(auto_queue)

@app.route("/api/add_to_auto_queue", methods=["POST"])
def add_to_auto_queue():
    """
    The AI calls this if a patient has a same-day appt and 'DateTimeArrived' is presumably 00:00.
    If the dateTimeArrived was NOT 00:00, we STILL place them here (your request).
    Then the background thread will move them => checked_in if we see they arrived.
    JSON: { "pat_num":..., "first_name":"...", "last_name":"..." }
    """
    data = request.json
    if not data:
        return jsonify({"error":"No JSON"}),400

    pat_num = data.get("pat_num")
    fname   = data.get("first_name","")
    lname   = data.get("last_name","")
    if not pat_num or not fname or not lname:
        return jsonify({"error":"Missing pat_num / name"}),400

    # remove from any list they might be in, to avoid duplication
    remove_from_auto_queue(pat_num) 
    remove_from_doctor_queue(pat_num)
    remove_from_checked_in(pat_num)

    # Then add
    auto_queue.append({
        "pat_num": pat_num,
        "name": f"{fname} {lname}",
        "date_added": datetime.utcnow().isoformat()
    })
    return jsonify({"message":"Added to auto queue"}),200

@app.route("/api/clear_auto_queue", methods=["POST"])
def clear_auto_queue():
    auto_queue.clear()
    return jsonify({"message":"auto_queue cleared"}),200

@app.route("/api/auto_to_checked_in", methods=["POST"])
def auto_to_checked_in():
    """
    Doctor forcibly moves them from auto_queue => checked_in
    JSON: { "pat_num":..., "arrived_at":... (optional) }
    """
    global auto_queue
    data = request.json
    if not data or "pat_num" not in data:
        return jsonify({"error":"Missing pat_num"}),400

    pat_num = data["pat_num"]
    arrived_str = data.get("arrived_at", datetime.utcnow().strftime("%Y-%m-%d %H:%M"))

    removed=None
    new_auto=[]
    for q in auto_queue:
        if q["pat_num"] == pat_num:
            removed = q
        else:
            new_auto.append(q)
    auto_queue = new_auto

    if removed:
        # remove from checked_in to avoid duplicates
        remove_from_checked_in(pat_num)
        # add
        checked_in_patients.append({
            "name": removed["name"],
            "pat_num":pat_num,
            "arrived": arrived_str,
            "status":"ready"
        })
        return jsonify({"message":f"Moved {removed['name']} to checked_in"}),200
    else:
        return jsonify({"error":f"No auto_queue patient with pat_num={pat_num}"}),404

# -------------- C) DOCTOR QUEUE --------------
@app.route("/api/doctor_queue_list", methods=["GET"])
def get_doctor_queue_list():
    return jsonify(doctor_queue)

@app.route("/api/add_to_doctor_queue", methods=["POST"])
def add_to_doctor_queue():
    """
    Doctor forcibly places a patient in a manual queue (no background calls).
    JSON: { "pat_num":..., "first_name":"...", "last_name":"..." }
    """
    global doctor_queue
    data = request.json
    if not data:
        return jsonify({"error":"No JSON"}),400

    pat_num = data.get("pat_num")
    fname   = data.get("first_name","")
    lname   = data.get("last_name","")
    if not pat_num or not fname or not lname:
        return jsonify({"error":"Missing pat_num / name"}),400

    remove_from_auto_queue(pat_num)
    remove_from_doctor_queue(pat_num)
    remove_from_checked_in(pat_num)

    doctor_queue.append({
        "pat_num": pat_num,
        "name": f"{fname} {lname}",
        "date_added": datetime.utcnow().isoformat()
    })
    return jsonify({"message":"Added to doctor_queue"}),200

@app.route("/api/clear_doctor_queue", methods=["POST"])
def clear_doctor_queue():
    doctor_queue.clear()
    return jsonify({"message":"doctor_queue cleared"}),200

@app.route("/api/doctor_to_checked_in", methods=["POST"])
def doctor_to_checked_in():
    """
    Move from doc queue => checked_in
    JSON: { "pat_num":..., "arrived_at":... (optional) }
    """
    global doctor_queue
    data = request.json
    if not data or "pat_num" not in data:
        return jsonify({"error":"Missing pat_num"}),400

    pat_num=data["pat_num"]
    arrived_str=data.get("arrived_at", datetime.utcnow().strftime("%Y-%m-%d %H:%M"))

    removed=None
    new_doc=[]
    for q in doctor_queue:
        if q["pat_num"]==pat_num:
            removed=q
        else:
            new_doc.append(q)
    doctor_queue=new_doc

    if removed:
        remove_from_checked_in(pat_num)
        checked_in_patients.append({
            "name": removed["name"],
            "pat_num": pat_num,
            "arrived": arrived_str,
            "status":"ready"
        })
        return jsonify({"message":f"Moved {removed['name']} to checked_in"}),200
    else:
        return jsonify({"error":f"No doc_queue patient with pat_num={pat_num}"}),404

# -------------- D) Move from checked_in => doctor_queue --------------
@app.route("/api/checked_in_to_doctor_queue", methods=["POST"])
def checked_in_to_doctor_queue():
    """
    JSON: { "pat_num":..., "arrived_at":... (optional) }
    """
    global checked_in_patients
    data = request.json
    if not data or "pat_num" not in data:
        return jsonify({"error":"Missing pat_num"}),400

    pat_num=data["pat_num"]

    removed=None
    new_list=[]
    for p in checked_in_patients:
        if p["pat_num"]==pat_num:
            removed=p
        else:
            new_list.append(p)
    checked_in_patients=new_list

    if removed:
        remove_from_doctor_queue(pat_num)
        remove_from_auto_queue(pat_num)
        doctor_queue.append({
            "pat_num": pat_num,
            "name": removed["name"],
            "date_added": datetime.utcnow().isoformat()
        })
        return jsonify({"message":f"Moved {removed['name']} to doctor_queue"}),200
    else:
        return jsonify({"error":f"No checked_in found with pat_num={pat_num}"}),404

# ------------------------------------------------------------------------------
# 5) Helpers to remove from the three lists by pat_num
# ------------------------------------------------------------------------------
def remove_from_doctor_queue(pat_num):
    global doctor_queue
    new_doc=[]
    for q in doctor_queue:
        if q["pat_num"] != pat_num:
            new_doc.append(q)
    doctor_queue=new_doc

def remove_from_checked_in(pat_num):
    global checked_in_patients
    new_list=[]
    for p in checked_in_patients:
        if p["pat_num"]!=pat_num:
            new_list.append(p)
    checked_in_patients=new_list

# ------------------------------------------------------------------------------
# 6) Start
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    start_threads()
    app.run(debug=True, port=5000)
