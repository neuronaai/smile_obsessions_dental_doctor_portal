// script.js

// We'll assume your server has an endpoint like /api/current_list
// that returns JSON array of patients:
//   [ { name: "Will Smith", arrived: "2025-04-06 10:15 AM", status: "ready" }, ... ]

const patientTableBody = document.getElementById('patientTableBody');

// Example: fetch your real data from the server, e.g. /api/current_list
async function loadPatients() {
  try {
    // This is an example endpoint. Adapt to your actual route if needed:
    const resp = await fetch('/api/current_list');
    const data = await resp.json();

    // Clear the table body
    patientTableBody.innerHTML = '';

    // Suppose each patient object is { name, arrived, status, etc. }
    data.forEach((p) => {
      const tr = document.createElement('tr');

      const nameTd = document.createElement('td');
      nameTd.textContent = p.name; 
      // or p.first_name + " " + p.last_name
      tr.appendChild(nameTd);

      const arrivedTd = document.createElement('td');
      arrivedTd.textContent = p.arrived; // e.g. "2025-04-06 10:15 AM"
      tr.appendChild(arrivedTd);

      const actionTd = document.createElement('td');

      // If they've not been "called in" yet, show "Call In" button:
      if (p.status === "ready") {
        const btn = document.createElement('button');
        btn.textContent = "Call In";
        btn.classList.add('call-button');
        btn.onclick = () => handleCallIn(p);
        actionTd.appendChild(btn);
      } else {
        // e.g. "Already Called In"
        actionTd.textContent = "Already Called In";
      }
      tr.appendChild(actionTd);

      patientTableBody.appendChild(tr);
    });
  } catch (err) {
    console.error("Failed to load patients:", err);
  }
}

// Suppose we have an endpoint /api/announce or /api/call_in
// that triggers Emmersa to do something
async function handleCallIn(patientObj) {
  try {
    const resp = await fetch('/api/call_in', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        name: patientObj.name, // or first_name/last_name
        arrived: patientObj.arrived 
      })
    });
    const resData = await resp.json();
    if (resp.ok) {
      // Possibly update the UI
      alert(`${patientObj.name} was called in!`);
      // Reload the table to show new status
      loadPatients();
    } else {
      alert("Error calling in patient: " + (resData.error || resp.statusText));
    }
  } catch (err) {
    alert("Network error calling in patient: " + err);
  }
}

// On page load, fetch patients every X seconds
window.addEventListener('DOMContentLoaded', () => {
  loadPatients();
  setInterval(loadPatients, 10000); // poll every 10s
});
