// main.js - The Hatchery Makerspace Prototype
// This version uses hardcoded data for prototyping - no API calls

// ============================================================================
// PROTOTYPE DATA
// ============================================================================

const PROTOTYPE_MACHINES = {
    1: {
        id: 1,
        name: 'Epilog Laser Fusion Pro',
        category: 'Laser',
        location: 'Hatch Front',
        description: 'Professional-grade laser cutter for wood, acrylic, and more.',
        is_certified: false,
        instances: [
            {id: 1, nickname: 'Apollo', status: 'available'},
            {id: 2, nickname: 'Zeus', status: 'in-use'}
        ],
        required_trainings: [
            {id: 1, name: 'Laser Cutting Basics', description: 'Learn safe laser operation', duration: 2}
        ]
    },
    2: {
        id: 2,
        name: 'Prusa i3 MK3S+',
        category: '3D Printing',
        location: 'Prototyping Studio',
        description: 'Reliable FDM 3D printer for rapid prototyping.',
        is_certified: true,
        instances: [
            {id: 3, nickname: 'Eddy', status: 'available'},
            {id: 4, nickname: 'Felix', status: 'available'},
            {id: 5, nickname: 'Gizmo', status: 'in-use'},
            {id: 6, nickname: 'Hugo', status: 'available'},
            {id: 7, nickname: 'Iris', status: 'available'},
            {id: 8, nickname: 'Jasper', status: 'available'},
            {id: 9, nickname: 'Kira', status: 'maintenance'},
            {id: 10, nickname: 'Luna', status: 'available'},
            {id: 11, nickname: 'Max', status: 'available'},
            {id: 12, nickname: 'Nova', status: 'available'}
        ],
        required_trainings: [
            {id: 2, name: 'Intro to 3D Printing', description: 'Basic 3D printing skills', duration: 3}
        ]
    },
    3: {
        id: 3,
        name: 'Cricut Maker 3',
        category: 'Vinyl',
        location: 'Hatch Back',
        description: 'Precision cutting for vinyl, paper, and fabric.',
        is_certified: false,
        instances: [
            {id: 13, nickname: 'Slice', status: 'available'},
            {id: 14, nickname: 'Dice', status: 'in-use'}
        ],
        required_trainings: [
            {id: 3, name: 'Vinyl Cutting Basics', description: 'Learn vinyl cutting', duration: 1.5}
        ]
    },
    4: {
        id: 4,
        name: 'Shapeoko 4 XXL CNC',
        category: 'Woodworking',
        location: 'Prototyping Shop',
        description: 'Large format CNC router for wood and soft metals.',
        is_certified: false,
        instances: [
            {id: 15, nickname: 'Chipper', status: 'maintenance'},
            {id: 16, nickname: 'Carver', status: 'available'}
        ],
        required_trainings: [
            {id: 4, name: 'Woodworking Basics', description: 'Shop safety and basics', duration: 2},
            {id: 5, name: 'CNC Routing', description: 'CNC operation', duration: 3}
        ]
    },
    5: {
        id: 5,
        name: 'Electronics Workbench',
        category: 'Electronics',
        location: 'Prototyping Studio',
        description: 'Fully equipped stations for electronics projects.',
        is_certified: false,
        instances: [
            {id: 17, nickname: 'Station Alpha', status: 'available'},
            {id: 18, nickname: 'Station Beta', status: 'available'},
            {id: 19, nickname: 'Station Gamma', status: 'in-use'}
        ],
        required_trainings: [
            {id: 6, name: 'Circuitry Basics', description: 'Electronics fundamentals', duration: 2},
            {id: 7, name: 'Soldering Basics', description: 'Safe soldering techniques', duration: 1}
        ]
    },
    6: {
        id: 6,
        name: 'Ultimaker S5',
        category: '3D Printing',
        location: 'Prototyping Studio',
        description: 'Large format professional 3D printer.',
        is_certified: true,
        instances: [
            {id: 20, nickname: 'Titan', status: 'available'},
            {id: 21, nickname: 'Atlas', status: 'available'}
        ],
        required_trainings: [
            {id: 2, name: 'Intro to 3D Printing', description: 'Basic 3D printing skills', duration: 3}
        ]
    }
};

// ============================================================================
// GLOBAL STATE
// ============================================================================

let currentFilter = 'all';
let selectedInstance = null;

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    initializeMachineDirectory();
    setupModalCloseHandlers();
    setupUserDropdown();
});

// ============================================================================
// MACHINE DIRECTORY - Search & Filter
// ============================================================================

function initializeMachineDirectory() {
    const machineGrid = document.getElementById('machineGrid');
    if (!machineGrid) return;

    // Setup filter chips
    const filterChips = document.querySelectorAll('.filter-chip');
    filterChips.forEach(chip => {
        chip.addEventListener('click', function() {
            filterChips.forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            currentFilter = this.getAttribute('data-filter');
            filterMachines();
        });
    });

    // Setup search input
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', filterMachines);
    }
}

// ============================================================================
// USER DROPDOWN - Header menu on user name
// ============================================================================

function setupUserDropdown() {
    const dropdown = document.getElementById('userDropdown');
    const toggle = document.getElementById('userDropdownToggle');
    if (!dropdown || !toggle) return;

    toggle.addEventListener('click', function(e) {
        e.preventDefault();
        dropdown.classList.toggle('active');
    });

    // Close when clicking outside
    document.addEventListener('click', function(e) {
        if (!dropdown.contains(e.target)) {
            dropdown.classList.remove('active');
        }
    });

    // Close on Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            dropdown.classList.remove('active');
        }
    });
}

function filterMachines() {
    const searchTerm = document.getElementById('searchInput')?.value.toLowerCase() || '';
    const machineCards = document.querySelectorAll('.machine-card');

    let visibleCount = 0;
    machineCards.forEach(card => {
        const category = card.getAttribute('data-category');
        const name = card.getAttribute('data-name') || '';
        const location = card.getAttribute('data-location') || '';

        const matchesFilter = currentFilter === 'all' || category === currentFilter;
        const matchesSearch = name.includes(searchTerm) || 
                            location.includes(searchTerm) || 
                            category.toLowerCase().includes(searchTerm);

        if (matchesFilter && matchesSearch) {
            card.style.display = 'block';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });

    // Show empty state if no results
    let emptyState = document.querySelector('.empty-state-dynamic');
    
    if (visibleCount === 0 && !emptyState) {
        const machineGrid = document.getElementById('machineGrid');
        emptyState = document.createElement('div');
        emptyState.className = 'empty-state empty-state-dynamic';
        emptyState.innerHTML = `
            <div class="empty-state-icon">🔍</div>
            <p>No machines found matching your criteria.</p>
        `;
        machineGrid.appendChild(emptyState);
    } else if (visibleCount > 0 && emptyState) {
        emptyState.remove();
    }
}

// ============================================================================
// MACHINE MODAL - View Details & Reserve
// ============================================================================

function openMachineModal(machineId) {
    const modal = document.getElementById('machineModal');
    const modalBody = document.getElementById('modalBody');
    
    modal.classList.add('active');
    modalBody.innerHTML = '<div style="text-align: center; padding: 2rem;">Loading...</div>';

    // Simulate API delay for realism
    setTimeout(() => {
        const machine = PROTOTYPE_MACHINES[machineId];
        if (machine) {
            displayMachineDetails(machine);
        } else {
            modalBody.innerHTML = '<div style="text-align: center; padding: 2rem; color: red;">Machine not found.</div>';
        }
    }, 300);
}

function displayMachineDetails(machine) {
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.textContent = machine.name;
    
    let modalContent = `
        <div id="modalInfo">
            <p style="margin-bottom: 1rem;"><strong>Category:</strong> ${machine.category}</p>
            <p style="margin-bottom: 1rem;"><strong>Location:</strong> ${machine.location}</p>
            ${machine.description ? `<p style="margin-bottom: 1rem;"><strong>Description:</strong> ${machine.description}</p>` : ''}
        </div>
        <div id="modalActions">
    `;

    if (machine.is_certified) {
        // User is certified - show machine instances
        modalContent += `
            <div style="background: #d4edda; padding: 1rem; border-radius: 8px; margin: 1rem 0; border: 2px solid #28a745;">
                <p style="color: #155724; font-weight: 600;">✓ You are certified for this machine</p>
            </div>
            <h3 style="color: var(--maroon); margin: 1.5rem 0 1rem;">Select a Machine:</h3>
            <div class="machine-instance-grid">
        `;

        machine.instances.forEach(instance => {
            const statusClass = instance.status === 'available' ? 'available' :
                              instance.status === 'in-use' ? 'in-use' : 'maintenance';
            const statusBadgeClass = instance.status === 'available' ? 'status-available-badge' :
                                    instance.status === 'in-use' ? 'status-in-use-badge' : 'status-maintenance-badge';
            const statusText = instance.status === 'available' ? 'Available' :
                             instance.status === 'in-use' ? 'In Use' : 'Maintenance';
            const disabled = instance.status !== 'available';
            const clickHandler = disabled ? '' : `onclick="selectMachineInstance(${instance.id}, '${instance.nickname}', ${machine.id})"`;

            modalContent += `
                <div class="instance-card ${statusClass}" ${clickHandler} ${disabled ? 'style="opacity: 0.6; cursor: not-allowed;"' : ''}>
                    <h4 style="color: var(--maroon); margin-bottom: 0.5rem;">${instance.nickname}</h4>
                    <p style="font-size: 0.85rem; color: #666;">${machine.name}</p>
                    <span class="instance-status ${statusBadgeClass}">${statusText}</span>
                    ${instance.status === 'in-use' ? `<div style="margin-top: 0.5rem;"><button class="btn btn-secondary btn-small" onclick="event.stopPropagation(); joinWaitlist('${instance.nickname}', ${instance.id})">Join Waitlist</button></div>` : ''}
                    ${instance.status === 'available' ? `<div style="margin-top: 0.5rem;"><button class="btn btn-danger btn-small" onclick="event.stopPropagation(); reportIssue('${instance.nickname}', ${instance.id})">Report Issue</button></div>` : ''}
                </div>
            `;
        });

        modalContent += `</div>`;
    } else {
        // User needs training
        const trainingList = machine.required_trainings.map(t => `<li>${t.name}</li>`).join('');
        modalContent += `
            <div style="background: var(--light-maroon); padding: 1rem; border-radius: 8px; margin: 1rem 0; border: 2px solid var(--maroon);">
                <p style="color: var(--maroon); font-weight: 600; margin-bottom: 0.5rem;">⚠️ Training Required</p>
                <p style="font-size: 0.9rem; margin-bottom: 0.5rem;">Complete these trainings to use this machine:</p>
                <ul style="margin-left: 1.5rem; font-size: 0.9rem;">${trainingList}</ul>
            </div>
            <form id="trainingForm" onsubmit="bookTraining(event, ${machine.id})">
                <div class="form-group">
                    <label>Select Training Session</label>
                    <select id="trainSession" required>
                        ${machine.required_trainings.map(t => `<option value="${t.id}">${t.name}</option>`).join('')}
                    </select>
                </div>
                <div class="form-group">
                    <label>Select Training Date</label>
                    <input type="date" id="trainDate" min="${getMinDate()}" required>
                </div>
                <div class="form-group">
                    <label>Select Time Slot</label>
                    <select id="trainTime" required>
                        <option>9:00 AM - 12:00 PM</option>
                        <option>12:00 PM - 3:00 PM</option>
                        <option>3:00 PM - 6:00 PM</option>
                        <option>6:00 PM - 9:00 PM</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-primary" style="width: 100%;">Book Training Session</button>
            </form>
        `;
    }

    modalContent += `</div>`;
    modalBody.innerHTML = modalContent;
}

function selectMachineInstance(instanceId, nickname, machineId) {
    selectedInstance = { id: instanceId, nickname: nickname, machineId: machineId };
    
    const modalActions = document.getElementById('modalActions');
    modalActions.innerHTML = `
        <div style="background: var(--light-gold); padding: 1rem; border-radius: 8px; margin: 1rem 0; border: 2px solid var(--gold);">
            <p style="font-weight: 600; color: var(--maroon);">Selected: ${nickname}</p>
        </div>
        <form id="reservationForm" onsubmit="makeReservation(event)">
            <div class="form-group">
                <label>Select Date</label>
                <input type="date" id="resDate" min="${getMinDate()}" required>
            </div>
            <div class="form-group">
                <label>Select Time Slot</label>
                <select id="resTime" required>
                    <option>9:00 AM - 11:00 AM</option>
                    <option>11:00 AM - 1:00 PM</option>
                    <option>1:00 PM - 3:00 PM</option>
                    <option>3:00 PM - 5:00 PM</option>
                    <option>5:00 PM - 7:00 PM</option>
                    <option>7:00 PM - 9:00 PM</option>
                </select>
            </div>
            <div class="form-group">
                <label>Duration (hours)</label>
                <input type="number" id="resDuration" min="1" max="3" value="2" required>
            </div>
            <div class="form-group">
                <label>Project Description</label>
                <textarea id="resProject" rows="3" placeholder="Brief description of what you're making..." required></textarea>
            </div>
            <div style="display: flex; gap: 0.5rem;">
                <button type="button" class="btn btn-secondary" onclick="openMachineModal(${machineId})" style="flex: 1;">← Back</button>
                <button type="submit" class="btn btn-primary" style="flex: 2;">Reserve ${nickname}</button>
            </div>
        </form>
    `;
}

function makeReservation(event) {
    event.preventDefault();
    
    const date = document.getElementById('resDate').value;
    const time = document.getElementById('resTime').value;
    const duration = document.getElementById('resDuration').value;
    const project = document.getElementById('resProject').value;

    // Prototype: Just show success message
    showMessage('success', `Machine reserved successfully! ${selectedInstance.nickname} is booked for ${duration} hour(s) on ${formatDate(date)} at ${time}.`);
    closeMachineModal();
}

function bookTraining(event, machineId) {
    event.preventDefault();
    
    const training = document.getElementById('trainSession').options[document.getElementById('trainSession').selectedIndex].text;
    const date = document.getElementById('trainDate').value;
    const time = document.getElementById('trainTime').value;

    // Prototype: Just show success message
    showMessage('success', `Training session booked successfully! You're registered for "${training}" on ${formatDate(date)} at ${time}.`);
    closeMachineModal();
}

function closeMachineModal() {
    const modal = document.getElementById('machineModal');
    if (modal) {
        modal.classList.remove('active');
    }
    selectedInstance = null;
}

// ============================================================================
// MACHINE INSTANCE ACTIONS
// ============================================================================

function joinWaitlist(nickname, instanceId) {
    showMessage('success', `✓ You've been added to the waitlist for ${nickname}! You'll receive a notification when this machine becomes available.`);
}

function reportIssue(nickname, instanceId) {
    const issue = prompt(`Report an issue with ${nickname}:\n\nPlease describe the problem:`);
    if (issue) {
        showMessage('success', `Thank you for reporting an issue with ${nickname}. Our staff will investigate and address this issue shortly.`);
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function getMinDate() {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().split('T')[0];
}

function showMessage(type, message) {
    // Create a message div if messages container doesn't exist
    let messagesContainer = document.querySelector('.messages');
    if (!messagesContainer) {
        messagesContainer = document.createElement('div');
        messagesContainer.className = 'messages';
        const container = document.querySelector('.container');
        container.insertBefore(messagesContainer, container.firstChild);
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `alert alert-${type}`;
    messageDiv.textContent = message;
    messagesContainer.appendChild(messageDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        messageDiv.style.opacity = '0';
        setTimeout(() => messageDiv.remove(), 300);
    }, 5000);
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
        weekday: 'short', 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

// ============================================================================
// MODAL CLOSE HANDLERS
// ============================================================================

function setupModalCloseHandlers() {
    // Close modals when clicking outside
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal')) {
            e.target.classList.remove('active');
        }
    });

    // Close modals on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal.active').forEach(modal => {
                modal.classList.remove('active');
            });
        }
    });
}

// ============================================================================
// MY RESERVATIONS PAGE - Cancel & Modify
// ============================================================================

function cancelReservation(reservationId, type) {
    if (!confirm('Are you sure you want to cancel this reservation?')) return;

    // Prototype: Just remove the card and show message
    const card = document.querySelector(`[data-reservation-id="${reservationId}"]`);
    if (card) {
        card.style.opacity = '0';
        card.style.transform = 'translateX(-20px)';
        setTimeout(() => {
            card.remove();
            showMessage('success', 'Reservation cancelled successfully!');
        }, 300);
    }
}

function modifyReservation(reservationId, type) {
    // Prototype: Just show a message
    showMessage('info', 'Modification feature coming soon! In the full version, this would open a form to edit your reservation details.');
}


// ============================================================================
// STAFF DASHBOARD - Machine Management
// ============================================================================

function addMachine() {
    const name = document.getElementById('machineName').value;
    const category = document.getElementById('machineCategory').value;
    const location = document.getElementById('machineLocation').value;
    const description = document.getElementById('machineDescription').value;

    showMessage('success', `Machine "${name}" added successfully to ${location}!`);
    
    // Clear form
    document.getElementById('machineName').value = '';
    document.getElementById('machineDescription').value = '';
}

function removeMachine(machineName) {
    if (!confirm(`Are you sure you want to remove "${machineName}"?`)) return;
    
    showMessage('success', `Machine "${machineName}" removed successfully.`);
    // In real app, would remove from database and update UI
}

// ============================================================================
// STAFF DASHBOARD - Location Management
// ============================================================================

const LOCATION_DATA = {
    1: {
        name: 'Hatch Front',
        machines: [
            { name: 'Epilog Laser Fusion Pro', category: 'Laser' },
            { name: 'Epilog Laser - Rotary', category: 'Laser' }
        ]
    },
    2: {
        name: 'Hatch Back',
        machines: [
            { name: 'Cricut Maker 3', category: 'Vinyl' },
            { name: 'Brother Embroidery Machine', category: 'Textiles' },
            { name: 'Multi-Surface UV Printer', category: 'Laser' }
        ]
    },
    3: {
        name: 'Prototyping Studio',
        machines: [
            { name: 'Prusa i3 MK3S+', category: '3D Printing' },
            { name: 'Ultimaker S5', category: '3D Printing' },
            { name: 'Formlabs Form 3', category: '3D Printing' },
            { name: 'Electronics Workbench', category: 'Electronics' }
        ]
    },
    4: {
        name: 'Prototyping Shop',
        machines: [
            { name: 'Shapeoko 4 XXL CNC', category: 'Woodworking' },
            { name: 'SawStop Table Saw', category: 'Woodworking' },
            { name: 'OMAX Waterjet Cutter', category: 'Metalworking' }
        ]
    }
};

function viewLocationDetails(locationName, locationId) {
    const modal = document.getElementById('locationModal');
    const modalTitle = document.getElementById('locationModalTitle');
    const modalBody = document.getElementById('locationModalBody');
    
    modalTitle.textContent = locationName;
    modal.classList.add('active');
    
    const location = LOCATION_DATA[locationId];
    
    let machineListHtml = '<div class="machine-list"><p style="margin-bottom: 1rem;"><strong>Machines at this location:</strong></p>';
    
    if (location && location.machines.length > 0) {
        location.machines.forEach(machine => {
            machineListHtml += `
                <div class="machine-item">
                    <strong>${machine.name}</strong>
                    <span style="font-size: 0.85rem; color: #666;">${machine.category}</span>
                </div>
            `;
        });
    } else {
        machineListHtml += '<p style="color: #666;">No machines at this location.</p>';
    }
    
    machineListHtml += '</div>';
    modalBody.innerHTML = machineListHtml;
}

function closeLocationModal() {
    const modal = document.getElementById('locationModal');
    if (modal) modal.classList.remove('active');
}

function openEditLocationModal() {
    const modal = document.getElementById('editLocationModal');
    if (modal) modal.classList.add('active');
}

function closeEditLocationModal() {
    const modal = document.getElementById('editLocationModal');
    if (modal) modal.classList.remove('active');
}

function saveLocation() {
    const name = document.getElementById('locationName').value;
    const floor = document.getElementById('locationFloor').value;
    const stations = document.getElementById('locationStations').value;
    const capacity = document.getElementById('locationCapacity').value;
    
    showMessage('success', `Location "${name}" saved successfully!`);
    closeEditLocationModal();
}

// ============================================================================
// STAFF DASHBOARD - Trainer Management
// ============================================================================

function openAutoScheduleModal() {
    const modal = document.getElementById('autoScheduleModal');
    if (modal) modal.classList.add('active');
}

function closeAutoScheduleModal() {
    const modal = document.getElementById('autoScheduleModal');
    if (modal) modal.classList.remove('active');
}

function runAutoSchedule() {
    const priority = document.getElementById('schedulePriority').value;
    
    // Show loading message
    showMessage('info', 'Auto-scheduling in progress...');
    
    // Simulate processing delay
    setTimeout(() => {
        showMessage('success', 
            `Auto-scheduling completed successfully!\n\n` +
            `The system has analyzed:\n` +
            `• 5 trainers\n` +
            `• Their availability constraints\n` +
            `• Tool category expertise\n` +
            `• 2-hour block requirements\n\n` +
            `Schedule generated with priority: ${priority}`
        );
        closeAutoScheduleModal();
    }, 1500);
}

function openManageTrainersModal() {
    const modal = document.getElementById('manageTrainersModal');
    if (modal) modal.classList.add('active');
}

function closeManageTrainersModal() {
    const modal = document.getElementById('manageTrainersModal');
    if (modal) modal.classList.remove('active');
}

function editTrainer(trainerName) {
    showMessage('info', `Edit trainer: ${trainerName}\n\nIn the full version, this would open a form to update their categories, unavailability, and preferences.`);
}

function addNewTrainer() {
    showMessage('info', 'Add New Trainer\n\nIn the full version, this would open a form to enter trainer details, categories, and availability.');
}

function viewTrainerSchedule(trainerName) {
    showMessage('info', `Viewing schedule for ${trainerName}\n\nIn the full version, this would show their complete weekly schedule with all assigned shifts.`);
}

function publishSchedule() {
    if (!confirm('Are you sure you want to publish this schedule to all students? This will make it visible in the app.')) return;
    
    showMessage('success', '🚀 Schedule published successfully! Students can now view open hours and book training sessions.');
}