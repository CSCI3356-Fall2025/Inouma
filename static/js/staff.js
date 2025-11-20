console.log("staff.js is loaded!");

const NUM_SLOTS = 6;   // 9–11, 11–1, 1–3, 3–5, 5–7, 7–9
const NUM_DAYS = 7;    // Sun–Sat

// Matrix of cells: cells[slotIndex][dayIndex]
let SCHEDULE_CELLS = [];

// Map time range -> row index
function slotIndexFromTimes(startHHMM, endHHMM) {
    const toMin = t => {
        const [h, m] = t.split(":").map(Number);
        return h * 60 + m;
    };
    const s = toMin(startHHMM);
    const e = toMin(endHHMM);

    if (s === 9 * 60 && e === 11 * 60) return 0;    // 9–11
    if (s === 11 * 60 && e === 13 * 60) return 1;   // 11–1
    if (s === 13 * 60 && e === 15 * 60) return 2;   // 1–3
    if (s === 15 * 60 && e === 17 * 60) return 3;   // 3–5
    if (s === 17 * 60 && e === 19 * 60) return 4;   // 5–7
    if (s === 19 * 60 && e === 21 * 60) return 5;   // 7–9

    console.warn("Unrecognized time slot:", startHHMM, endHHMM);
    return -1;
}

// Map ISO date -> day index (0=Sun..6=Sat)
function dayIndexFromISO(dateStr) {
    // "2025-11-12" -> Date -> getDay()
    const d = new Date(dateStr + "T00:00:00");
    return d.getDay();
}

// Build matrix SCHEDULE_CELLS[slot][day]
function initGrid() {
    const grid = document.querySelector(".schedule-grid-detailed");
    if (!grid) {
        console.error("No .schedule-grid-detailed found");
        return;
    }

    const cells = Array.from(grid.querySelectorAll(".schedule-cell-detailed"));
    if (cells.length !== NUM_SLOTS * NUM_DAYS) {
        console.warn(
            "Expected",
            NUM_SLOTS * NUM_DAYS,
            "cells but found",
            cells.length,
            "- check your HTML"
        );
    }

    SCHEDULE_CELLS = [];
    let idx = 0;
    for (let slot = 0; slot < NUM_SLOTS; slot++) {
        SCHEDULE_CELLS[slot] = [];
        for (let day = 0; day < NUM_DAYS; day++) {
            const cell = cells[idx++];
            if (cell) {
                cell.innerHTML = "";              // clear previous content
                cell.classList.remove("filled");  // remove any old styles
                SCHEDULE_CELLS[slot][day] = cell;
            } else {
                SCHEDULE_CELLS[slot][day] = null;
            }
        }
    }
}

// Render one shift into the correct cell
function renderShift(shift) {
    const slotIndex = slotIndexFromTimes(shift.start, shift.end);
    const dayIndex = dayIndexFromISO(shift.date);

    console.log("Placing shift:", shift, "slot:", slotIndex, "day:", dayIndex);

    if (slotIndex < 0 || dayIndex < 0) return;
    if (!SCHEDULE_CELLS[slotIndex] || !SCHEDULE_CELLS[slotIndex][dayIndex]) {
        console.warn("No cell for slot", slotIndex, "day", dayIndex);
        return;
    }

    const cell = SCHEDULE_CELLS[slotIndex][dayIndex];
    cell.classList.add("filled");
    cell.innerHTML += `
        <div class="shift-open">Trainer: ${shift.trainer}</div>
        <div class="shift-training">
            <span class="category-badge">Team</span> ${shift.team || "N/A"}
        </div>
    `;
}

// Load shifts from backend, optionally filtered by week
async function loadShifts(weekStart = null) {
    initGrid();  // rebuild matrix each time

    let url = "/schedule/api/shifts/";
    if (weekStart) {
        url += "?week=" + encodeURIComponent(weekStart);
    }

    console.log("Fetching shifts from:", url);

    try {
        const res = await fetch(url);
        if (!res.ok) {
            console.error("Failed to load shifts:", res.status);
            return;
        }

        const data = await res.json();
        console.log("Shifts from API:", data);

        if (Array.isArray(data.shifts)) {
            data.shifts.forEach(renderShift);
        } else if (Array.isArray(data)) {
            data.forEach(renderShift);
        } else {
            console.warn("Unexpected shifts payload:", data);
        }
    } catch (err) {
        console.error("Error loading shifts:", err);
    }
}

// Called by the "Load Schedule" button
async function loadSelectedWeek() {
    const weekSelect = document.getElementById("weekSelect");
    if (!weekSelect || !weekSelect.value) {
        alert("Please select a week.");
        return;
    }
    const weekStart = weekSelect.value;  // e.g. "2025-11-10"
    await loadShifts(weekStart);
}

// On page load: default to the first week option if present
document.addEventListener("DOMContentLoaded", () => {
    console.log("DOMContentLoaded: initializing schedule grid");
    const weekSelect = document.getElementById("weekSelect");
    if (weekSelect && weekSelect.value) {
        loadShifts(weekSelect.value);
    } else {
        loadShifts(null);
    }
});
