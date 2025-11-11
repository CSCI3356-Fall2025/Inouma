// Search autocomplete functionality
const searchInput = document.getElementById('searchInput');
const suggestionsDiv = document.getElementById('searchSuggestions');
let debounceTimer;

searchInput.addEventListener('input', function() {
    clearTimeout(debounceTimer);
    const query = this.value.trim();
    
    if (query.length < 1) {
        suggestionsDiv.style.display = 'none';
        return;
    }
    
    debounceTimer = setTimeout(() => {
        fetch(`/api/search-suggestions/?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                if (data.suggestions.length > 0) {
                    suggestionsDiv.innerHTML = data.suggestions.map(suggestion => 
                        `<div style="padding: 0.75rem; cursor: pointer; border-bottom: 1px solid #eee;" 
                              onmouseover="this.style.background='var(--light-gold)'" 
                              onmouseout="this.style.background='white'"
                              onclick="selectSearchSuggestion('${suggestion.value.replace(/'/g, "\\'")}')">${suggestion.display}</div>`
                    ).join('');
                    suggestionsDiv.style.display = 'block';
                } else {
                    suggestionsDiv.style.display = 'none';
                }
            });
    }, 300);
});

function selectSearchSuggestion(value) {
    searchInput.value = value;  // Only fills the actual value (e.g., "James" not "James (Machine Name)")
    suggestionsDiv.style.display = 'none';
    filterMachines();
}

// Close suggestions when clicking outside
document.addEventListener('click', function(e) {
    if (!searchInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
        suggestionsDiv.style.display = 'none';
    }
});

// Search and filter functionality
function filterMachines() {
    const searchTerm = searchInput.value.toLowerCase();
    const machines = document.querySelectorAll('.machine-card');
    
    machines.forEach(machine => {
        const machineType = machine.getAttribute('data-machine-type') || '';
        const machineName = machine.getAttribute('data-machine-name') || '';
        const category = machine.getAttribute('data-category') || '';
        const location = machine.getAttribute('data-location') || '';
        
        const matchesSearch = machineType.includes(searchTerm) || 
                            machineName.includes(searchTerm) ||
                            category.toLowerCase().includes(searchTerm) || 
                            location.includes(searchTerm);
        
        machine.style.display = matchesSearch ? 'block' : 'none';
    });
}


// Filter on input
searchInput.addEventListener('input', filterMachines);

// Category filter functionality
const filterChips = document.querySelectorAll('.filter-chip');
filterChips.forEach(chip => {
    chip.addEventListener('click', function() {
        filterChips.forEach(c => c.classList.remove('active'));
        this.classList.add('active');
        
        const filter = this.getAttribute('data-filter');
        const machines = document.querySelectorAll('.machine-card');
        
        machines.forEach(machine => {
            const category = machine.getAttribute('data-category');
            if (filter === 'all' || category === filter) {
                machine.style.display = 'block';
            } else {
                machine.style.display = 'none';
            }
        });
    });
});
