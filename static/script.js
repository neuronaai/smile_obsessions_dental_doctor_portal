// script.js

// Grab the <tbody> where we place rows:
const patientTableBody = document.getElementById('patientTableBody');

/**
 * loadPatients():
 * Fetches the current list of checked-in patients from /api/current_list
 * and updates the table in the DOM.
 */
async function loadPatients() {
  try {
    // 1) Make GET request to /api/current_list
    const resp = await fetch('/api/current_list');
    if (!resp.ok) {
      console.error("Failed /api/current_list:", resp.statusText);
      return;
    }
    const data = await resp.json();  // data is e.g. [ { name, arrived, status }, ... ]

    // 2) Clear existing rows
    patientTableBody.innerHTML = '';

    // 3) Loop over each patient object and build a <tr>
    data.forEach((patient) => {
      const tr = document.createElement('tr');

      // A) Name column
      const nameTd = document.createElement('td');
      nameTd.textContent = patient.name; 
      tr.appendChild(nameTd);

      // B) Arrived column
      const arrivedTd = document.createElement('td');
      arrivedTd.textContent = patient.arrived; 
      tr.appendChild(arrivedTd);

      // C) Action column
      const actionTd = document.createElement('td');
      if (patient.status === "ready") {
        // Show a "Call In" button
        const callBtn = document.createElement('button');
        callBtn.textContent = "Call In";
        callBtn.classList.add('call-button');
        callBtn.onclick = () => handleCallIn(patient);
        actionTd.appendChild(callBtn);
      } else {
        // e.g. "Already Called In"
        actionTd.textContent = "Already Called In";
      }
      tr.appendChild(actionTd);

      // 4) Append <tr> to <tbody>
      patientTableBody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading patients:", err);
  }
}

/**
 * handleCallIn(patient):
 * Calls the /api/call_in endpoint to mark the patient as "called"
 * Then refreshes the table.
 */
async function handleCallIn(patient) {
  try {
    // 1) Send POST /api/call_in with { name: "...", arrived: "..." }
    const resp = await fetch('/api/call_in', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: patient.name,
        arrived: patient.arrived
      })
    });
    const resData = await resp.json();

    // 2) If success, show alert & reload table
    if (resp.ok) {
      alert(`${patient.name} was called in!`);
      loadPatients(); // refresh UI
    } else {
      alert("Error calling in patient: " + (resData.error || resp.statusText));
    }
  } catch (err) {
    alert("Network error calling in patient: " + err);
  }
}

/**
 * On page load => load once, then poll every 10 seconds
 */
window.addEventListener('DOMContentLoaded', () => {
  loadPatients();
  setInterval(loadPatients, 10000);
});
