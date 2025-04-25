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
Example:
checked_in_patients = [
  {
    "pat_num": 1234,
    "name": "Will Smith",
    "arrived": "2025-04-06 10:15",
    "status": "ready" or "called",
    "called_time": "<ISO8601 if 'called'>"
  },
  ...
]
"""

auto_queue = []
"""
Placed here by Emmersa => /api/add_to_queue
Background thread checks 'DateTimeArrived' => moves them to checked_in.
[
  {
    "pat_num": 9999,
    "name": "Test Patient",
    "date_added": "2025-04-23T14:22:00Z"
  },
  ...
]
"""

doctor_queue = []
"""
Manual queue the doctor can use => no automatic checks
[
  {
    "pat_num": 1111,
    "name": "Another Person",
    "date_added": "2025-04-23T14:22:00Z"
  },
  ...
]
"""

# ------------------------------------------------------------------------------
# 2) OD Credentials (for checking DateTimeArrived)
# ------------------------------------------------------------------------------
OD_DEVELOPER_KEY = os.environ.get("OD_API_DEV_KEY", "A0NnBNFvx4DjbwRb")
OD_CUSTOMER_KEY  = os.environ.get("OD_API_CUST_KEY", "JQ1BkECEdo3XILEy")
OD_BASE_URL = "https://api.opendental.com/api/v1"
OD_HEADERS = {
    "Authorization": f"ODFHIR {OD_DEVELOPER_KEY}/{OD_CUSTOMER_KEY}",
    "Content-Type": "application/json"
}

# ------------------------------------------------------------------------------
# 3) Background Threads
# ------------------------------------------------------------------------------
def cleanup_thread():
    """
    Every 60s, remove 'called' patients if they've been 'called' > 3 hours.
    """
    while True:
        time.sleep(60)
        now = datetime.utcnow()
        # We'll build a new list of patients that survive
        survivors = []
        for p in checked_in_patients:
            if p["status"] == "called" and "called_time" in p:
                dt_called = datetime.fromisoformat(p["called_time"])
                if (now - dt_called) > timedelta(hours=3):
                    print(f"[CLEANUP] Removing {p['name']} (called >3h ago).")
                    continue
            survivors.append(p)
        # Mutate in place
        checked_in_patients.clear()
        checked_in_patients.extend(survivors)

def auto_queue_monitor_thread():
    """
    Every 30s => for each patient in auto_queue:
      1) GET /appointments?PatNum=xxx
      2) If we see DateTimeArrived != '...00:00:00', they've arrived => remove from auto_queue => put in checked_in.
      3) Sleep 11s between each patient to avoid overlapping requests
    """
    while True:
        time.sleep(30)
        # Copy the current auto_queue to avoid concurrency issues
        snapshot = auto_queue[:]
        for q in snapshot:
            pat_num = q["pat_num"]
            name    = q["name"]
            apt_url = f"{OD_BASE_URL}/appointments?PatNum={pat_num}"

            try:
                resp = requests.get(apt_url, headers=OD_HEADERS, timeout=5)
                if resp.ok:
                    data = resp.json()
                    arrived_found = False
                    for apt in data:
                        dt_arr = apt.get("DateTimeArrived","")
                        # If dt_arr is not "0001-01-01..." or doesn't end with "00:00:00"
                        if dt_arr and not dt_arr.startswith("0001-01-01"):
                            if dt_arr[-8:] != "00:00:00":
                                arrived_found = True
                                break
                    if arrived_found:
                        print(f"[AUTO_QUEUE] {name} => arrived => move to checked_in.")
                        remove_from_auto_queue(pat_num)
                        remove_from_doctor_queue(pat_num)
                        remove_from_checked_in(pat_num)

                        checked_in_patients.append({
                            "pat_num": pat_num,
                            "name": name,
                            "arrived": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                            "status": "ready"
                        })
                else:
                    print(f"[WARN] GET {apt_url} => {resp.status_code}, {resp.text}")
            except requests.RequestException as e:
                print("[ERROR] auto_queue_monitor_thread =>", e)

            time.sleep(11)

def start_threads():
    t1 = threading.Thread(target=cleanup_thread, daemon=True)
    t1.start()
    t2 = threading.Thread(target=auto_queue_monitor_thread, daemon=True)
    t2.start()

# ------------------------------------------------------------------------------
# 4) Helper Removal Functions (no global needed; we mutate in place)
# ------------------------------------------------------------------------------
def remove_from_auto_queue(pn):
    new_list = [q for q in auto_queue if q["pat_num"] != pn]
    auto_queue.clear()
    auto_queue.extend(new_list)

def remove_from_doctor_queue(pn):
    new_list = [q for q in doctor_queue if q["pat_num"] != pn]
    doctor_queue.clear()
    doctor_queue.extend(new_list)

def remove_from_checked_in(pn):
    new_list = [p for p in checked_in_patients if p["pat_num"] != pn]
    checked_in_patients.clear()
    checked_in_patients.extend(new_list)

# ------------------------------------------------------------------------------
# 5) Flask Routes
# ------------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ==========  A) CHECKED-IN  ==========
@app.route("/api/checked_in_list", methods=["GET"])
def get_checked_in_list():
    return jsonify(checked_in_patients)

@app.route("/api/call_in", methods=["POST"])
def call_in():
    data = request.json
    if not data or "name" not in data:
        return jsonify({"error":"No name"}),400
    
    name = data["name"]
    found = False
    for p in checked_in_patients:
        if p["name"] == name and p["status"]=="ready":
            p["status"] = "called"
            p["called_time"] = datetime.utcnow().isoformat()
            found=True
            break
    if not found:
        return jsonify({"error":f"No 'ready' patient named {name}"}),404
    return jsonify({"message":f"Called in {name}"}),200

@app.route("/api/uncall", methods=["POST"])
def uncall():
    data = request.json
    if not data or "name" not in data:
        return jsonify({"error":"No name"}),400
    
    name=data["name"]
    found=False
    for p in checked_in_patients:
        if p["name"]==name and p["status"]=="called":
            p["status"]="ready"
            p.pop("called_time",None)
            found=True
            break
    if not found:
        return jsonify({"error":f"No 'called' patient with name={name}"}),404
    return jsonify({"message":f"Uncalled {name}"}),200

@app.route("/api/clear_checked_in", methods=["POST"])
def clear_checked_in():
    checked_in_patients.clear()
    print("[INFO] All checked_in cleared.")
    return jsonify({"message":"All patients cleared"}),200

# ==========  B) AUTO QUEUE  ==========
@app.route("/api/auto_queue_list", methods=["GET"])
def get_auto_queue_list():
    return jsonify(auto_queue)

@app.route("/api/add_to_queue", methods=["POST"])
def add_to_queue():
    """
    Emmersa calls this => places patient in 'auto_queue'.
    We remove them from other lists to avoid duplication.
    JSON => { "pat_num":..., "first_name":"...", "last_name":"..." }
    """
    data = request.json
    if not data:
        return jsonify({"error":"No JSON"}),400

    pat_num = data.get("pat_num")
    f       = data.get("first_name","")
    l       = data.get("last_name","")

    if not pat_num or not f or not l:
        return jsonify({"error":"Missing pat_num or name"}),400

    remove_from_auto_queue(pat_num)
    remove_from_doctor_queue(pat_num)
    remove_from_checked_in(pat_num)

    auto_queue.append({
        "pat_num": pat_num,
        "name": f"{f} {l}",
        "date_added": datetime.utcnow().isoformat()
    })
    print(f"[INFO] add_to_queue => {pat_num}, {f} {l}")
    return jsonify({"message":"Added to auto_queue"}),200

@app.route("/api/clear_auto_queue", methods=["POST"])
def clear_auto_queue():
    auto_queue.clear()
    print("[INFO] Auto queue cleared.")
    return jsonify({"message":"auto_queue cleared"}),200

@app.route("/api/auto_to_checked_in", methods=["POST"])
def auto_to_checked_in():
    """
    Doctor forcibly moves from auto_queue => checked_in
    JSON => { "pat_num":..., "arrived_at":... (optional) }
    """
    data = request.json
    if not data or "pat_num" not in data:
        return jsonify({"error":"Missing pat_num"}),400

    pat_num = data["pat_num"]
    arrived_str = data.get("arrived_at", datetime.utcnow().strftime("%Y-%m-%d %H:%M"))

    # find & remove from auto_queue
    found=None
    new_auto=[]
    for q in auto_queue:
        if q["pat_num"]==pat_num:
            found=q
        else:
            new_auto.append(q)
    auto_queue.clear()
    auto_queue.extend(new_auto)

    if found:
        # also remove from doctor_queue + checked_in if any
        remove_from_doctor_queue(pat_num)
        remove_from_checked_in(pat_num)

        checked_in_patients.append({
            "pat_num": pat_num,
            "name": found["name"],
            "arrived": arrived_str,
            "status":"ready"
        })
        return jsonify({"message":f"Moved {found['name']} to checked_in."}),200
    else:
        return jsonify({"error":f"No auto_queue pat_num={pat_num}"}),404

# ==========  C) DOCTOR QUEUE  ==========
@app.route("/api/doctor_queue_list", methods=["GET"])
def get_doctor_queue_list():
    return jsonify(doctor_queue)

@app.route("/api/add_to_doctor_queue", methods=["POST"])
def add_to_doctor_queue():
    """
    JSON => { "pat_num":..., "first_name":"...", "last_name":"..." }
    """
    data=request.json
    if not data:
        return jsonify({"error":"No JSON"}),400

    pat_num=data.get("pat_num")
    fname = data.get("first_name","")
    lname = data.get("last_name","")

    if not pat_num or not fname or not lname:
        return jsonify({"error":"Missing pat_num or name"}),400

    remove_from_auto_queue(pat_num)
    remove_from_doctor_queue(pat_num)
    remove_from_checked_in(pat_num)

    doctor_queue.append({
        "pat_num": pat_num,
        "name": f"{fname} {lname}",
        "date_added": datetime.utcnow().isoformat()
    })
    print(f"[INFO] add_to_doctor_queue => {pat_num}, {fname} {lname}")
    return jsonify({"message":"Added to doctor_queue"}),200

@app.route("/api/clear_doctor_queue", methods=["POST"])
def clear_doctor_queue():
    doctor_queue.clear()
    print("[INFO] Doctor queue cleared.")
    return jsonify({"message":"doctor_queue cleared"}),200

@app.route("/api/doctor_to_checked_in", methods=["POST"])
def doctor_to_checked_in():
    """
    Move from doctor_queue => checked_in
    JSON => { "pat_num":..., "arrived_at":...(optional) }
    """
    data=request.json
    if not data or "pat_num" not in data:
        return jsonify({"error":"Missing pat_num"}),400

    pat_num=data["pat_num"]
    arrived_str=data.get("arrived_at",datetime.utcnow().strftime("%Y-%m-%d %H:%M"))

    found=None
    new_doc=[]
    for q in doctor_queue:
        if q["pat_num"]==pat_num:
            found=q
        else:
            new_doc.append(q)
    doctor_queue.clear()
    doctor_queue.extend(new_doc)

    if found:
        remove_from_auto_queue(pat_num)
        remove_from_checked_in(pat_num)
        checked_in_patients.append({
            "pat_num": pat_num,
            "name": found["name"],
            "arrived": arrived_str,
            "status":"ready"
        })
        return jsonify({"message":f"Moved {found['name']} => checked_in"}),200
    else:
        return jsonify({"error":f"No doc_queue pat_num={pat_num}"}),404

@app.route("/api/checked_in_to_doctor_queue", methods=["POST"])
def checked_in_to_doctor_queue():
    """
    Move from checked_in => doctor_queue
    JSON => { "pat_num":... }
    """
    data=request.json
    if not data or "pat_num" not in data:
        return jsonify({"error":"Missing pat_num"}),400

    pat_num=data["pat_num"]
    found=None
    new_ci=[]
    for p in checked_in_patients:
        if p["pat_num"]==pat_num:
            found=p
        else:
            new_ci.append(p)
    checked_in_patients.clear()
    checked_in_patients.extend(new_ci)

    if found:
        remove_from_auto_queue(pat_num)
        remove_from_doctor_queue(pat_num)
        doctor_queue.append({
            "pat_num": pat_num,
            "name": found["name"],
            "date_added": datetime.utcnow().isoformat()
        })
        return jsonify({"message":f"Moved {found['name']} => doctor_queue"}),200
    else:
        return jsonify({"error":f"No checked_in with pat_num={pat_num}"}),404

# ------------------------------------------------------------------------------
# 6) Start the threads + app
# ------------------------------------------------------------------------------
if __name__=="__main__":
    start_threads()
    app.run(debug=True,port=5000)
