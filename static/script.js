// script.js

// Table bodies
const patientTableBody = document.getElementById('patientTableBody');
const queueTableBody   = document.getElementById('queueTableBody');

// Sections
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

      // "Call In" or "Uncall" logic
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

      // Also a "Move to Queue" button if you want
      const toQueueBtn = document.createElement('button');
      toQueueBtn.textContent = "→ Queue";
      toQueueBtn.classList.add('call-button');
      toQueueBtn.style.marginLeft = '6px';
      toQueueBtn.onclick = () => handleCheckedInToQueue(p);
      actionTd.appendChild(toQueueBtn);

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

      // patNum
      const patNumTd = document.createElement('td');
      patNumTd.textContent = q.pat_num;
      tr.appendChild(patNumTd);

      // date_added
      const dateTd = document.createElement('td');
      dateTd.textContent = q.date_added;
      tr.appendChild(dateTd);

      // Action => "Move to Checked-In" button
      const actionTd = document.createElement('td');
      const arrivedBtn = document.createElement('button');
      arrivedBtn.textContent = "→ Checked-In";
      arrivedBtn.classList.add('call-button');
      arrivedBtn.onclick = () => handleQueueToCheckedIn(q);
      actionTd.appendChild(arrivedBtn);

      tr.appendChild(actionTd);
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

/** handleQueueToCheckedIn(q):
 * forcibly moves them from queue -> checked_in
 * by calling POST /api/queue_to_checked_in
 */
async function handleQueueToCheckedIn(queueObj) {
  try {
    const resp = await fetch('/api/queue_to_checked_in', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pat_num: queueObj.pat_num,
        arrived_at: new Date().toLocaleString()
      })
    });
    if (resp.ok) {
      loadQueue();
      loadPatients();
    } else {
      console.error("Error queue_to_checked_in:", await resp.text());
    }
  } catch (err) {
    console.error("Network error queue_to_checked_in:", err);
  }
}

/** handleCheckedInToQueue(p):
 * forcibly moves them from checked_in -> queue
 * by calling POST /api/checked_in_to_queue
 */
async function handleCheckedInToQueue(checkedInObj) {
  try {
    const resp = await fetch('/api/checked_in_to_queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: checkedInObj.name,
        pat_num: 0  // or real patNum if you have it
      })
    });
    if (resp.ok) {
      loadQueue();
      loadPatients();
    } else {
      console.error("Error checked_in_to_queue:", await resp.text());
    }
  } catch (err) {
    console.error("Network error checked_in_to_queue:", err);
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

// On page load => show "Checked-In", then poll both lists
window.addEventListener('DOMContentLoaded', () => {
  showCheckedIn();
  loadPatients();
  loadQueue();

  setInterval(loadPatients, 10000);
  setInterval(loadQueue, 10000);
});
