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
  const btn = document.getElementById('loadSlotsBtn');
  const trainerId = document.getElementById('trainerSelect').value;
  const date = document.getElementById('dateInput').value;
  const c = document.getElementById('slotsContainer');
  if (!trainerId || !date) { alert('Select a trainer and date'); return; }

  btn.disabled = true;
  const prev = btn.textContent;
  btn.textContent = 'Loading…';
  c.innerHTML = '';

  try {
    const data = await fetchJSON(`/auth/api/trainers/${encodeURIComponent(trainerId)}/availability/?date=${encodeURIComponent(date)}`);
    if (!data.slots || !data.slots.length) { c.textContent = 'No available slots.'; return; }
    data.slots.forEach(s => {
      const b = document.createElement('button');
      b.className = 'btn btn-outline-primary slot-btn';
      b.textContent =
        new Date(s.start_time).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) +
        ' - ' +
        new Date(s.end_time).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
      b.dataset.trainerId = trainerId;
      b.dataset.startIso = s.start_time;
      b.dataset.endIso = s.end_time;
      b.addEventListener('click', onBookClick);
      c.appendChild(b);
      c.appendChild(document.createTextNode(' '));
    });
  } catch (e) {
    console.error('Load slots failed:', e);
    alert(e.message || 'Failed to load slots');
  } finally {
    btn.disabled = false;
    btn.textContent = prev;
  }
}

async function onBookClick(e) {
  const btn = e.currentTarget;
  btn.disabled = true;
  try {
    const payload = {
      trainer: btn.dataset.trainerId,
      machine_instance: (window.TRAINING_CONTEXT && window.TRAINING_CONTEXT.machineInstanceId) || '',
      start_time: btn.dataset.startIso,
      end_time: btn.dataset.endIso
    };
    const data = await fetchJSON('/auth/api/training-reservations/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify(payload),
    });

    btn.classList.add('disabled');
    btn.setAttribute('aria-disabled', 'true');
    btn.textContent = 'Booked';
    alert('Training booked!');
    await loadSlots(); // refresh grid; your chosen slot disappears
  } catch (e2) {
    btn.disabled = false;
    alert(e2.message || 'Booking failed');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const loadBtn = document.getElementById('loadSlotsBtn');
  if (loadBtn) loadBtn.addEventListener('click', loadSlots);
});
