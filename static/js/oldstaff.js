console.log("staff.js is loaded!");

const SLOT_LABELS = ["9-11am", "11am-1pm", "1-3pm", "3-5pm", "5-7pm", "7-9pm"];
let GRID = Array(SLOT_LABELS.length)
  .fill(null)
  .map(() => Array(7).fill(null));

function indexGrid() {
  const grid = document.querySelector(".schedule-grid-detailed");
  if (!grid) return;

  const kids = Array.from(grid.children);
  
  kids.forEach((el) => {
    if (el.classList.contains("schedule-cell-detailed")) {
      el.innerHTML = "";
      el.classList.remove("filled");
    }
  });

  let currentRow = -1;
  let col = -1;

  for (const el of kids) {
    if (el.classList.contains("schedule-time")) {
      const label = el.textContent.trim();
      currentRow = SLOT_LABELS.indexOf(label);
      col = -1;
    } else if (el.classList.contains("schedule-cell-detailed")) {
      col += 1;
      if (currentRow >= 0 && col >= 0 && col < 7) {
        GRID[currentRow][col] = el;
      }
    }
  }
}

function weekdayFromISO(dateStr) {
  // Sunday=0 ... Saturday=6
  return new Date(dateStr + "T00:00:00").getDay();
}

function slotIndexFromTimes(startHHMM, endHHMM) {
  const toMin = (t) => {
    const [h, m] = t.split(":").map(Number);
    return h * 60 + m;
  };
  const s = toMin(startHHMM),
    e = toMin(endHHMM);
  if (s === 540 && e === 660) return 0; // 9-11
  if (s === 660 && e === 780) return 1; // 11-1
  if (s === 780 && e === 900) return 2; // 1-3
  if (s === 900 && e === 1020) return 3; // 3-5
  if (s === 1020 && e === 1140) return 4; // 5-7
  if (s === 1140 && e === 1260) return 5; // 7-9
  return -1;
}

function getCookie(name) {
  const m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
  return m ? m.pop() : "";
}

function renderShiftCell(shift) {
  // shift = {date:"YYYY-MM-DD", start:"HH:MM", end:"HH:MM", trainer:"...", team:"..."}
  const day = weekdayFromISO(shift.date);
  const slot = slotIndexFromTimes(shift.start, shift.end);
  if (slot < 0 || !GRID[slot] || !GRID[slot][day]) return;

  const cell = GRID[slot][day];
  cell.classList.add("filled");

  const divOpen = document.createElement("div");
  divOpen.className = "shift-open";
  divOpen.textContent = `Open: ${shift.trainer}`;

  if (shift.team) {
    const divTeam = document.createElement("div");
    divTeam.className = "shift-training";
    divTeam.textContent = `Team: ${shift.team}`;
    cell.appendChild(divTeam);
  }

  cell.appendChild(divOpen);
}

async function loadShifts(queryString = "") {
  indexGrid();

  try {
    let url = "/schedule/api/shifts/";
    if (queryString) {
      url += "?" + queryString;
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load shifts");

    const data = await res.json(); // expected format: {shifts:[...]}
    data.shifts.forEach(renderShiftCell);
  } catch (err) {
    console.error("Error loading shifts:", err);
  }
}

async function loadSelectedWeek() {
  const weekSelect = document.getElementById("weekSelect");
  if (!weekSelect || !weekSelect.value) {
    alert("Please select a week.");
    return;
  }

  const weekStart = weekSelect.value; // expected format: "YYYY-MM-DD"
  await loadShifts("week_start=" + encodeURIComponent(weekStart));
}

async function runAutoSchedule() {
  const csrftoken = getCookie("csrftoken");

  const payload = {
    start_date: "2025-11-11",
    end_date: "2025-12-15",
    weekdays: [0, 1, 2, 3, 4, 5, 6],
  };

  try {
    const res = await fetch("/schedule/api/auto/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken,
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("Auto-schedule failed");

    alert("Auto-schedule complete! Reloading schedule...");
    await loadShifts();
    closeAutoScheduleModal();
  } catch (err) {
    alert("Alert " + err.message);
  } 
}

function openAutoScheduleModal() {
  document.getElementById("autoScheduleModal").style.display = "block";
}

function closeAutoScheduleModal() {
  document.getElementById("autoScheduleModal").style.display = "none";
}

// initialize
document.addEventListener("DOMContentLoaded", () => {
  const weekSelect = document.getElementById("weekSelect");
  if (weekSelect && weekSelect.value) {
    loadShifts("week_start=" + encodeURIComponent(weekSelect.value));
  } else {
    loadShifts();
  }
});