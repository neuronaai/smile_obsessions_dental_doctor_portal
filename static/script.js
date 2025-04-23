// script.js

// Table bodies
const patientTableBody = document.getElementById('patientTableBody');
const queueTableBody = document.getElementById('queueTableBody');

// Sections
const checkedInSection = document.getElementById('checkedInSection');
const queueSection = document.getElementById('queueSection');

/** Show "Checked-In" section, hide "Queue" */
function showCheckedIn() {
  checkedInSection.style.display = 'block';
  queueSection.style.display = 'none';
}

/** Show "Queue" section, hide "Checked-In" */
function showQueue() {
  checkedInSection.style.display = 'none';
  queueSection.style.display = 'block';
}

/**
 * loadPatients():
 * Fetches the "checked_in_patients" from /api/current_list
 * Fills #patientTableBody
 */
async function loadPatients() {
  try {
    const resp = await fetch('/api/current_list');
    if (!resp.ok) {
      console.error("Failed /api/current_list:", resp.statusText);
      return;
    }
    const data = await resp.json();
    patientTableBody.innerHTML = '';

    data.forEach((p) => {
      const tr = document.createElement('tr');
      
      const nameTd = document.createElement('td');
      nameTd.textContent = p.name;
      tr.appendChild(nameTd);

      const arrivedTd = document.createElement('td');
      arrivedTd.textContent = p.arrived;
      tr.appendChild(arrivedTd);

      const actionTd = document.createElement('td');
      if (p.status === "ready") {
        const callBtn = document.createElement('button');
        callBtn.textContent = "Call In";
        callBtn.classList.add('call-button');
        callBtn.onclick = () => handleCallIn(p);
        actionTd.appendChild(callBtn);
      } else if (p.status === "called") {
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

/**
 * loadQueue():
 * Fetches "patients_in_queue" from /api/patients_in_queue
 * Fills #queueTableBody
 */
async function loadQueue() {
  try {
    const resp = await fetch('/api/patients_in_queue');
    if (!resp.ok) {
      console.error("Failed /api/patients_in_queue:", resp.statusText);
      return;
    }
    const data = await resp.json();
    queueTableBody.innerHTML = '';

    data.forEach((q) => {
      const tr = document.createElement('tr');

      const nameTd = document.createElement('td');
      nameTd.textContent = q.name;
      tr.appendChild(nameTd);

      const patNumTd = document.createElement('td');
      patNumTd.textContent = q.pat_num;
      tr.appendChild(patNumTd);

      const dateTd = document.createElement('td');
      dateTd.textContent = q.date_added;
      tr.appendChild(dateTd);

      queueTableBody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading queue:", err);
  }
}

/** handleCallIn, handleUncall basically the same as before */
async function handleCallIn(patient) {
  try {
    const resp = await fetch('/api/call_in', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: patient.name })
    });
    if (resp.ok) {
      announceInBrowser(`${patient.name}, please proceed to the doctor's office.`);
      loadPatients();
    } else {
      const resData = await resp.json();
      console.error("Error calling in patient:", resData.error || resp.statusText);
    }
  } catch (err) {
    console.error("Network error calling in patient:", err);
  }
}

async function handleUncall(patient) {
  try {
    const resp = await fetch('/api/uncall', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: patient.name })
    });
    if (resp.ok) {
      loadPatients();
    } else {
      const resData = await resp.json();
      console.error("Error uncalling patient:", resData.error || resp.statusText);
    }
  } catch (err) {
    console.error("Network error uncalling patient:", err);
  }
}

/** handleClearList => wipes checked_in_patients */
async function handleClearList() {
  if (!confirm("Are you sure you want to clear the entire list?")) return;
  try {
    const resp = await fetch('/api/clear_list', { method: 'POST' });
    if (resp.ok) {
      loadPatients();
    } else {
      console.error("Error clearing list:", resp.statusText);
    }
  } catch (err) {
    console.error("Network error clearing list:", err);
  }
}

/** clearQueue => calls /api/clear_queue */
async function clearQueue() {
  if (!confirm("Are you sure you want to clear the entire queue?")) return;
  try {
    const resp = await fetch('/api/clear_queue', { method: 'POST' });
    if (resp.ok) {
      loadQueue();
    } else {
      console.error("Error clearing queue:", resp.statusText);
    }
  } catch (err) {
    console.error("Network error clearing queue:", err);
  }
}

/** announceInBrowser => Web Speech API TTS */
function announceInBrowser(text) {
  if (!('speechSynthesis' in window)) {
    console.warn("This browser does not support speech synthesis.");
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  speechSynthesis.speak(utterance);
}

// On page load, default to the "Checked-In" view
window.addEventListener('DOMContentLoaded', () => {
  showCheckedIn();        // So it reveals the checkedInSection
  loadPatients();
  loadQueue();

  setInterval(loadPatients, 10000);
  setInterval(loadQueue, 10000);
});
