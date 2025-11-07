function getCsrfToken() {
  const name = 'csrftoken=';
  const cookies = document.cookie.split(';');
  for (let c of cookies) {
    c = c.trim();
    if (c.startsWith(name)) return c.substring(name.length);
  }
  return '';
}

async function fetchJSON(url, opts = {}) {
  const resp = await fetch(url, { credentials: 'same-origin', ...opts });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.detail || err.message || `HTTP ${resp.status}`);
  }
  return resp.json();
}

async function loadSlots() {
  const trainerId = document.getElementById('trainerSelect').value;
  const date = document.getElementById('dateInput').value;
  if (!trainerId || !date) { alert('Select a trainer and date'); return; }
  const data = await fetchJSON(`/auth/api/trainers/${trainerId}/availability/?date=${encodeURIComponent(date)}`);
  const c = document.getElementById('slotsContainer');
  c.innerHTML = '';
  if (!data.slots.length) { c.textContent = 'No available slots.'; return; }
  data.slots.forEach(s => {
    const btn = document.createElement('button');
    btn.className = 'btn btn-outline-primary slot-btn';
    btn.textContent =
      new Date(s.start_time).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) +
      ' - ' +
      new Date(s.end_time).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    btn.dataset.trainerId = trainerId;
    btn.dataset.startIso = s.start_time;
    btn.dataset.endIso = s.end_time;
    btn.addEventListener('click', onBookClick);
    c.appendChild(btn);
    c.appendChild(document.createTextNode(' '));
  });
}

async function onBookClick(e) {
  const btn = e.currentTarget;
  btn.disabled = true;
  try {
    const trainerId = btn.dataset.trainerId;
    const startISO = btn.dataset.startIso;
    const endISO = btn.dataset.endIso;
    const machineInstanceId = (window.TRAINING_CONTEXT && window.TRAINING_CONTEXT.machineInstanceId) || '';
    const payload = {
      trainer: trainerId,
      machine_instance: machineInstanceId,
      start_time: startISO,
      end_time: endISO
    };
    const data = await fetchJSON('/auth/api/training-reservations/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify(payload),
      credentials: 'same-origin'
    });

    btn.classList.add('disabled');
    btn.setAttribute('aria-disabled', 'true');
    btn.textContent = 'Booked';
    console.info('Training booked', data);

    alert('Training booked. Check server console for the confirmation email (dev mode).');
    await loadSlots();
  } catch (err) {
    btn.disabled = false;
    alert(err.message || 'Booking failed');
  }
}

function init() {
  const loadBtn = document.getElementById('loadSlotsBtn');
  if (loadBtn) loadBtn.addEventListener('click', loadSlots);
}
document.addEventListener('DOMContentLoaded', init);
