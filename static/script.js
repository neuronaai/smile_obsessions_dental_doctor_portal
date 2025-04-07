// script.js

const patientTableBody = document.getElementById('patientTableBody');

/**
 * loadPatients():
 * Fetches the current list of checked-in patients from /api/current_list
 * and updates the table in the DOM.
 */
async function loadPatients() {
  try {
    const resp = await fetch('/api/current_list');
    if (!resp.ok) {
      console.error("Failed /api/current_list:", resp.statusText);
      return;
    }
    const data = await resp.json();  // e.g. [ { name, arrived, status }, ...]

    // Clear existing rows
    patientTableBody.innerHTML = '';

    data.forEach((p) => {
      const tr = document.createElement('tr');

      // 1) Name
      const nameTd = document.createElement('td');
      nameTd.textContent = p.name;
      tr.appendChild(nameTd);

      // 2) Arrived
      const arrivedTd = document.createElement('td');
      arrivedTd.textContent = p.arrived; 
      tr.appendChild(arrivedTd);

      // 3) Action
      const actionTd = document.createElement('td');

      if (p.status === "ready") {
        // Show "Call In" button
        const callBtn = document.createElement('button');
        callBtn.textContent = "Call In";
        callBtn.classList.add('call-button');
        callBtn.onclick = () => handleCallIn(p);
        actionTd.appendChild(callBtn);
      }
      else if (p.status === "called") {
        // Show "Uncall" button
        const uncallBtn = document.createElement('button');
        uncallBtn.textContent = "Uncall";
        uncallBtn.classList.add('call-button');
        uncallBtn.onclick = () => handleUncall(p);
        actionTd.appendChild(uncallBtn);
      }
      tr.appendChild(actionTd);

      patientTableBody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading patients:", err);
  }
}

/** handleCallIn(patient): sets them to "called" */
async function handleCallIn(patient) {
  try {
    const resp = await fetch('/api/call_in', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: patient.name,
        arrived: patient.arrived
      })
    });
    if (resp.ok) {
      alert(`${patient.name} was called in!`);
      loadPatients();
    } else {
      const resData = await resp.json();
      alert("Error calling in patient: " + (resData.error || resp.statusText));
    }
  } catch (err) {
    alert("Network error calling in patient: " + err);
  }
}

/** handleUncall(patient): revert them from "called" to "ready" */
async function handleUncall(patient) {
  try {
    const resp = await fetch('/api/uncall', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: patient.name
      })
    });
    if (resp.ok) {
      alert(`${patient.name} was uncalled!`);
      loadPatients();
    } else {
      const resData = await resp.json();
      alert("Error uncalling patient: " + (resData.error || resp.statusText));
    }
  } catch (err) {
    alert("Network error uncalling patient: " + err);
  }
}

/** handleClearList(): calls /api/clear_list to wipe entire list */
async function handleClearList() {
  if (!confirm("Are you sure you want to clear the entire list?")) {
    return;
  }
  try {
    const resp = await fetch('/api/clear_list', { method: 'POST' });
    if (resp.ok) {
      alert("All patients cleared!");
      loadPatients();
    } else {
      alert("Error clearing list: " + resp.statusText);
    }
  } catch (err) {
    alert("Network error clearing list: " + err);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  loadPatients();
  setInterval(loadPatients, 10000);
});
