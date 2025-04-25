/************************************************************
 * script.js
 ************************************************************/

// Sections:
const checkedInSection   = document.getElementById('checkedInSection');
const autoQueueSection   = document.getElementById('autoQueueSection');
const doctorQueueSection = document.getElementById('doctorQueueSection');

// Table bodies:
const checkedInTableBody   = document.getElementById('checkedInTableBody');
const autoQueueTableBody   = document.getElementById('autoQueueTableBody');
const doctorQueueTableBody = document.getElementById('doctorQueueTableBody');

/************************************************************
 * 1. Show/Hide sections
 ************************************************************/
function showCheckedIn() {
  checkedInSection.style.display   = 'block';
  autoQueueSection.style.display   = 'none';
  doctorQueueSection.style.display = 'none';
}
function showAutoQueue() {
  checkedInSection.style.display   = 'none';
  autoQueueSection.style.display   = 'block';
  doctorQueueSection.style.display = 'none';
}
function showDoctorQueue() {
  checkedInSection.style.display   = 'none';
  autoQueueSection.style.display   = 'none';
  doctorQueueSection.style.display = 'block';
}

/************************************************************
 * 2. LOAD each list
 ************************************************************/
async function loadCheckedIn() {
  try {
    const r = await fetch('/api/checked_in_list');
    if (!r.ok) throw new Error(await r.text());
    const data = await r.json();
    checkedInTableBody.innerHTML = '';

    data.forEach(p => {
      const tr = document.createElement('tr');

      // name
      const nameTd = document.createElement('td');
      nameTd.textContent = p.name;
      tr.appendChild(nameTd);

      // arrived
      const arrTd = document.createElement('td');
      arrTd.textContent = p.arrived;
      tr.appendChild(arrTd);

      // actions
      const actionTd = document.createElement('td');

      // if status=ready => "Call In", else "Uncall"
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

      // move => doctor queue
      const toDocQ = document.createElement('button');
      toDocQ.textContent = "→ Doc Queue";
      toDocQ.classList.add('call-button');
      toDocQ.style.marginLeft = '8px';
      toDocQ.onclick = () => handleCheckedInToDocQueue(p);
      actionTd.appendChild(toDocQ);

      tr.appendChild(actionTd);
      checkedInTableBody.appendChild(tr);
    });
  } catch(err) {
    console.error("loadCheckedIn:", err);
  }
}

async function loadAutoQueue() {
  try {
    const r = await fetch('/api/auto_queue_list');
    if (!r.ok) throw new Error(await r.text());
    const data = await r.json();
    autoQueueTableBody.innerHTML = '';

    data.forEach(q => {
      const tr = document.createElement('tr');
      // name
      const nameTd = document.createElement('td');
      nameTd.textContent = q.name;
      tr.appendChild(nameTd);

      // pat_num
      const patTd = document.createElement('td');
      patTd.textContent = q.pat_num;
      tr.appendChild(patTd);

      // date_added
      const dateTd = document.createElement('td');
      dateTd.textContent = q.date_added;
      tr.appendChild(dateTd);

      // actions => "→ Checked-In"
      const actionTd = document.createElement('td');
      const moveBtn = document.createElement('button');
      moveBtn.textContent = "→ Checked-In";
      moveBtn.classList.add('call-button');
      moveBtn.onclick = () => handleAutoToCheckedIn(q);
      actionTd.appendChild(moveBtn);

      tr.appendChild(actionTd);
      autoQueueTableBody.appendChild(tr);
    });
  } catch(err) {
    console.error("loadAutoQueue:", err);
  }
}

async function loadDoctorQueue() {
  try {
    const r = await fetch('/api/doctor_queue_list');
    if(!r.ok) throw new Error(await r.text());
    const data = await r.json();
    doctorQueueTableBody.innerHTML = '';

    data.forEach(q => {
      const tr = document.createElement('tr');

      // name
      const nameTd = document.createElement('td');
      nameTd.textContent = q.name;
      tr.appendChild(nameTd);

      // patNum
      const patTd = document.createElement('td');
      patTd.textContent = q.pat_num;
      tr.appendChild(patTd);

      // date_added
      const dateTd = document.createElement('td');
      dateTd.textContent = q.date_added;
      tr.appendChild(dateTd);

      // actions => "→ Checked-In"
      const actionTd = document.createElement('td');
      const moveBtn = document.createElement('button');
      moveBtn.textContent = "→ Checked-In";
      moveBtn.classList.add('call-button');
      moveBtn.onclick = () => handleDocToCheckedIn(q);
      actionTd.appendChild(moveBtn);

      tr.appendChild(actionTd);
      doctorQueueTableBody.appendChild(tr);
    });
  } catch(err) {
    console.error("loadDoctorQueue:", err);
  }
}

/************************************************************
 * 3. Buttons => Clear
 ************************************************************/
async function clearCheckedIn(){
  if(!confirm("Clear all checked-in patients?")) return;
  try {
    const r = await fetch('/api/clear_checked_in',{method:'POST'});
    if(!r.ok) throw new Error(await r.text());
    loadCheckedIn();
  } catch(err){
    console.error("clearCheckedIn:",err);
  }
}

async function clearAutoQueue(){
  if(!confirm("Clear the entire auto_queue?")) return;
  try {
    const r = await fetch('/api/clear_auto_queue',{method:'POST'});
    if(!r.ok) throw new Error(await r.text());
    loadAutoQueue();
  } catch(err){
    console.error("clearAutoQueue:",err);
  }
}

async function clearDoctorQueue(){
  if(!confirm("Clear the entire doctor_queue?")) return;
  try {
    const r = await fetch('/api/clear_doctor_queue',{method:'POST'});
    if(!r.ok) throw new Error(await r.text());
    loadDoctorQueue();
  } catch(err){
    console.error("clearDoctorQueue:",err);
  }
}

/************************************************************
 * 4. Buttons => Move / Call / Uncall
 ************************************************************/
// A) from checked_in => call_in
async function handleCallIn(p){
  try {
    const r = await fetch('/api/call_in',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ name:p.name, pat_num:p.pat_num })
    });
    if(r.ok){
      announceInBrowser(`${p.name}, please proceed to the doctor's office.`);
      loadCheckedIn();
    } else {
      console.error("handleCallIn error:", await r.text());
    }
  } catch(err){
    console.error("handleCallIn:", err);
  }
}

// B) from checked_in => uncall
async function handleUncall(p){
  try {
    const r = await fetch('/api/uncall',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ name:p.name, pat_num:p.pat_num })
    });
    if(r.ok){
      loadCheckedIn();
    } else {
      console.error("handleUncall error:", await r.text());
    }
  } catch(err){
    console.error("handleUncall:", err);
  }
}

// C) from auto_queue => forcibly => checked_in
async function handleAutoToCheckedIn(q){
  try {
    const r = await fetch('/api/auto_to_checked_in',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        pat_num:q.pat_num,
        arrived_at:new Date().toLocaleString()
      })
    });
    if(r.ok){
      loadAutoQueue();
      loadCheckedIn();
    } else {
      console.error("handleAutoToCheckedIn error:", await r.text());
    }
  } catch(err){
    console.error("handleAutoToCheckedIn:",err);
  }
}

// D) from doctor_queue => checked_in
async function handleDocToCheckedIn(q){
  try {
    const r = await fetch('/api/doctor_to_checked_in',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        pat_num:q.pat_num,
        arrived_at:new Date().toLocaleString()
      })
    });
    if(r.ok){
      loadDoctorQueue();
      loadCheckedIn();
    } else {
      console.error("handleDocToCheckedIn error:", await r.text());
    }
  } catch(err){
    console.error("handleDocToCheckedIn:", err);
  }
}

// E) from checked_in => doctor_queue
async function handleCheckedInToDocQueue(p){
  try {
    const r = await fetch('/api/checked_in_to_doctor_queue',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ pat_num:p.pat_num })
    });
    if(r.ok){
      loadCheckedIn();
      loadDoctorQueue();
    } else {
      console.error("handleCheckedInToDocQueue error:", await r.text());
    }
  } catch(err){
    console.error("handleCheckedInToDocQueue:",err);
  }
}

/************************************************************
 * 5. TTS
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
 * 6. Init
 ************************************************************/
window.addEventListener('DOMContentLoaded', () => {
  showCheckedIn();

  loadCheckedIn();
  loadAutoQueue();
  loadDoctorQueue();

  setInterval(loadCheckedIn, 10000);
  setInterval(loadAutoQueue,10000);
  setInterval(loadDoctorQueue,10000);
});
