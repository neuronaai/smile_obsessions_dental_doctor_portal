from flask import Flask, request, render_template, jsonify

app = Flask(__name__)

# In-memory store of patients
checked_in_patients = [
]

@app.route('/')
def index():
    return render_template('index.html')  # references templates/index.html

@app.route('/api/current_list', methods=['GET'])
def get_current_list():
    return jsonify(checked_in_patients)

@app.route('/api/call_in', methods=['POST'])
def call_in():
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"error":"No patient name"}), 400
    
    name = data["name"]
    # Mark them "called"
    for p in checked_in_patients:
        if p["name"] == name:
            p["status"] = "called"
            # Possibly do an Emmersa announcement here
            break
    
    return jsonify({"message": f"Announced {name}"})

@app.route('/api/checked_in', methods=['POST'])
def post_checked_in():
    """
    Endpoint for receiving new check-ins from csv_api_checker.py

    Expected JSON:
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

    # **Important**: add them to the in-memory list
    checked_in_patients.append({
        "name": f"{first} {last}",
        "arrived": arrived,
        "status": "ready"
    })

    return jsonify({"message":"OK"}), 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)
