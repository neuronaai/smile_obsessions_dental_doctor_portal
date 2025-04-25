/************************************************************
 * script.js
 ************************************************************/

// HTML references
const checkedInSection   = document.getElementById("checkedInSection");
const autoQueueSection   = document.getElementById("autoQueueSection");
const doctorQueueSection = document.getElementById("doctorQueueSection");

const checkedInTableBody   = document.getElementById("checkedInTableBody");
const autoQueueTableBody   = document.getElementById("autoQueueTableBody");
const doctorQueueTableBody = document.getElementById("doctorQueueTableBody");

/************************************************************
 * 1. Section Toggles
 ************************************************************/
function showCheckedIn() {
  checkedInSection.style.display = 'block';
  autoQueueSection.style.display = 'none';
  doctorQueueSection.style.display = 'none';
}
function showAutoQueue() {
  checkedInSection.style.display = 'none';
  autoQueueSection.style.display = 'block';
  doctorQueueSection.style.display = 'none';
}
function showDoctorQueue() {
  checkedInSection.style.display = 'none';
  autoQueueSection.style.display = 'none';
  doctorQueueSection.style.display = 'block';
}

/************************************************************
 * 2. Load Each List
 ************************************************************/
async function loadCheckedIn() {
  try {
    const resp = await fetch('/api/checked_in_list');
    if (!resp.ok) throw new Error(resp.statusText);
    const data = await resp.json();
    checkedInTableBody.innerHTML = '';

    data.forEach(p => {
      const tr = document.createElement('tr');

      const nameTd    = document.createElement('td');
      nameTd.textContent = p.name;
      tr.appendChild(nameTd);

      const arrivedTd = document.createElement('td');
      arrivedTd.textContent = p.arrived;
      tr.appendChild(arrivedTd);

      const actionTd  = document.createElement('td');

      // "Call In" / "Uncall"
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

      // "Move to doctor queue"
      const toDocQ = document.createElement('button');
      toDocQ.textContent = "→ Doc Queue";
      toDocQ.classList.add('call-button');
      toDocQ.style.marginLeft='5px';
      toDocQ.onclick = () => handleCheckedInToDocQueue(p);
      actionTd.appendChild(toDocQ);

      tr.appendChild(actionTd);
      checkedInTableBody.appendChild(tr);
    });
  } catch (err) {
    console.error("loadCheckedIn:", err);
  }
}

async function loadAutoQueue() {
  try {
    const resp = await fetch('/api/auto_queue_list');
    if (!resp.ok) throw new Error(resp.statusText);
    const data = await resp.json();
    autoQueueTableBody.innerHTML = '';

    data.forEach(q => {
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

      const actionTd = document.createElement('td');
      // "Force Move to Checked-In"
      const moveBtn = document.createElement('button');
      moveBtn.textContent = "→ Checked-In";
      moveBtn.classList.add('call-button');
      moveBtn.onclick = () => handleAutoToCheckedIn(q);
      actionTd.appendChild(moveBtn);

      tr.appendChild(actionTd);
      autoQueueTableBody.appendChild(tr);
    });
  } catch (err) {
    console.error("loadAutoQueue:", err);
  }
}

async function loadDoctorQueue() {
  try {
    const resp = await fetch('/api/doctor_queue_list');
    if (!resp.ok) throw new Error(resp.statusText);
    const data = await resp.json();
    doctorQueueTableBody.innerHTML = '';

    data.forEach(q => {
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

      const actionTd = document.createElement('td');
      // "Move to Checked-In"
      const moveBtn = document.createElement('button');
      moveBtn.textContent = "→ Checked-In";
      moveBtn.classList.add('call-button');
      moveBtn.onclick = () => handleDocToCheckedIn(q);
      actionTd.appendChild(moveBtn);

      tr.appendChild(actionTd);
      doctorQueueTableBody.appendChild(tr);
    });
  } catch (err) {
    console.error("loadDoctorQueue:", err);
  }
}

/************************************************************
 * 3. Buttons & Helpers
 ************************************************************/
async function clearCheckedIn() {
  if (!confirm("Clear all checked-in patients?")) return;
  try {
    const resp = await fetch('/api/clear_checked_in', { method:'POST' });
    if (!resp.ok) throw new Error(await resp.text());
    loadCheckedIn();
  } catch (err) {
    console.error("clearCheckedIn:",err);
  }
}

async function clearAutoQueue() {
  if (!confirm("Clear the entire auto-queue?")) return;
  try {
    const resp = await fetch('/api/clear_auto_queue',{ method:'POST' });
    if (!resp.ok) throw new Error(await resp.text());
    loadAutoQueue();
  } catch(err){
    console.error("clearAutoQueue:",err);
  }
}

async function clearDoctorQueue() {
  if (!confirm("Clear the entire doctor queue?")) return;
  try {
    const resp = await fetch('/api/clear_doctor_queue',{ method:'POST' });
    if (!resp.ok) throw new Error(await resp.text());
    loadDoctorQueue();
  } catch(err){
    console.error("clearDoctorQueue:",err);
  }
}

/** handleCallIn => POST /api/call_in => set status=called */
async function handleCallIn(p){
  try {
    const resp = await fetch('/api/call_in',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ name:p.name, pat_num:p.pat_num })
    });
    if(resp.ok){
      announceInBrowser(`${p.name}, please proceed to the doctor's office.`);
      loadCheckedIn();
    } else {
      console.error("handleCallIn error:",await resp.text());
    }
  } catch(err){
    console.error("handleCallIn:",err);
  }
}

/** handleUncall => revert called->ready */
async function handleUncall(p){
  try {
    const resp = await fetch('/api/uncall',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ name:p.name, pat_num:p.pat_num })
    });
    if(resp.ok){
      loadCheckedIn();
    } else {
      console.error("handleUncall error:",await resp.text());
    }
  } catch(err){
    console.error("handleUncall:",err);
  }
}

/** handleAutoToCheckedIn => manually move from auto_queue => checked_in */
async function handleAutoToCheckedIn(q){
  try {
    const resp = await fetch('/api/auto_to_checked_in',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        pat_num:q.pat_num,
        arrived_at:new Date().toLocaleString()
      })
    });
    if(resp.ok){
      loadAutoQueue();
      loadCheckedIn();
    } else {
      console.error("handleAutoToCheckedIn error:",await resp.text());
    }
  } catch(err){
    console.error("handleAutoToCheckedIn:",err);
  }
}

/** handleDocToCheckedIn => move from doctor_queue => checked_in */
async function handleDocToCheckedIn(q){
  try {
    const resp = await fetch('/api/doctor_to_checked_in',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        pat_num:q.pat_num,
        arrived_at:new Date().toLocaleString()
      })
    });
    if(resp.ok){
      loadDoctorQueue();
      loadCheckedIn();
    } else {
      console.error("handleDocToCheckedIn error:",await resp.text());
    }
  } catch(err){
    console.error("handleDocToCheckedIn:",err);
  }
}

/** handleCheckedInToDocQueue => from checked_in => doctor_queue */
async function handleCheckedInToDocQueue(p){
  try {
    const resp = await fetch('/api/checked_in_to_doctor_queue',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ pat_num:p.pat_num })
    });
    if(resp.ok){
      loadCheckedIn();
      loadDoctorQueue();
    } else {
      console.error("handleCheckedInToDocQueue error:",await resp.text());
    }
  } catch(err){
    console.error("handleCheckedInToDocQueue:",err);
  }
}

/************************************************************
 * 4. Web Speech TTS
 ************************************************************/
function announceInBrowser(text){
  if(!('speechSynthesis' in window)){
    console.warn("No speechSynthesis in this browser");
    return;
  }
  const ut = new SpeechSynthesisUtterance(text);
  speechSynthesis.speak(ut);
}

/************************************************************
 * 5. Initialize
 ************************************************************/
window.addEventListener('DOMContentLoaded', () => {
  showCheckedIn();
  loadCheckedIn();
  loadAutoQueue();
  loadDoctorQueue();

  setInterval(loadCheckedIn,  10000);
  setInterval(loadAutoQueue, 10000);
  setInterval(loadDoctorQueue,10000);
});
