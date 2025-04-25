// script.js

const patientTableBody = document.getElementById('patientTableBody');
const queueTableBody   = document.getElementById('queueTableBody');

const checkedInSection = document.getElementById('checkedInSection');
const queueSection     = document.getElementById('queueSection');

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

/** loadPatients => GET /api/current_list => fill #patientTableBody */
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

      // name
      const nameTd = document.createElement('td');
      nameTd.textContent = p.name;
      tr.appendChild(nameTd);

      // arrived
      const arrivedTd = document.createElement('td');
      arrivedTd.textContent = p.arrived;
      tr.appendChild(arrivedTd);

      // action
      const actionTd = document.createElement('td');
      if (p.status === "ready") {
        const callBtn = document.createElement('button');
        callBtn.textContent = "Call In";
        callBtn.classList.add('call-button');
        callBtn.onclick = () => handleCallIn(p);
        actionTd.appendChild(callBtn);
      }
      else if (p.status === "called") {
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

/** loadQueue => GET /api/patients_in_queue => fill #queueTableBody */
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

      // name
      const nameTd = document.createElement('td');
      nameTd.textContent = q.name;
      tr.appendChild(nameTd);

      // pat_num
      const patNumTd = document.createElement('td');
      patNumTd.textContent = q.pat_num;
      tr.appendChild(patNumTd);

      // date_added
      const dateTd = document.createElement('td');
      dateTd.textContent = q.date_added;
      tr.appendChild(dateTd);

      // no direct action column here unless you want to add
      // e.g. a "Move to Checked-In" button => handleQueueToCheckedIn(q)...

      queueTableBody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading queue:", err);
  }
}

/** handleCallIn => set "called" for a 'ready' patient */
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

/** handleUncall => revert "called" => "ready" */
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

/** handleClearList => POST /api/clear_list => empty checked_in */
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

/** clearQueue => POST /api/clear_queue => empty queue */
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

// On page load, default => "Checked-In", poll both lists
window.addEventListener('DOMContentLoaded', () => {
  showCheckedIn();
  loadPatients();
  loadQueue();

  setInterval(loadPatients, 10000);
  setInterval(loadQueue, 10000);
});
