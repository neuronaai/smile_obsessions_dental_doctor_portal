# app.py
from flask import Flask, request, render_template, jsonify
import os

app = Flask(__name__)

# For the example, store some dummy patient data in memory
checked_in_patients = [
    {"name": "Will Smith", "arrived": "2025-04-06 10:15 AM", "status": "ready"},
    {"name": "Jane Doe", "arrived": "2025-04-06 10:25 AM", "status": "ready"},
    {"name": "Shubhankar Katekari", "arrived": "2025-04-06 10:30 AM", "status": "called"},
]

@app.route('/')
def index():
    return render_template('index.html')  # references templates/index.html

@app.route('/api/current_list', methods=['GET'])
def get_current_list():
    # In real usage, you'd fetch from DB or in-memory store
    return jsonify(checked_in_patients)

@app.route('/api/call_in', methods=['POST'])
def call_in():
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"error":"No patient name"}), 400
    
    name = data["name"]
    # Find them, set status => "called"
    for p in checked_in_patients:
        if p["name"] == name:
            p["status"] = "called"
            # Possibly trigger an Emmersa announcement here
            break
    return jsonify({"message":"Announced " + name})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
