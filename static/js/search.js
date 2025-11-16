// Search autocomplete functionality
const searchInput = document.getElementById('searchInput');
const suggestionsDiv = document.getElementById('searchSuggestions');
let debounceTimer;

searchInput.addEventListener('input', function() {
    clearTimeout(debounceTimer);
    const query = this.value.trim();
    
    if (query.length < 1) {
        suggestionsDiv.style.display = 'none';
        filterMachines();
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
            })
            .catch(error => console.error('Search suggestions error:', error));
    }, 300);
    
    filterMachines();
});

function selectSearchSuggestion(value) {
    searchInput.value = value;
    suggestionsDiv.style.display = 'none';
    filterMachines();
}

// Close suggestions when clicking outside
document.addEventListener('click', function(e) {
    if (!searchInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
        suggestionsDiv.style.display = 'none';
    }
});

// Combined filter function with debug logging
function filterMachines() {
    
    const searchTerm = searchInput.value.toLowerCase().trim();
    const activeFilter = document.querySelector('.filter-chip.active');
    const categoryFilter = activeFilter ? activeFilter.getAttribute('data-filter') : 'all';
    
    console.log('Search term:', searchTerm);
    console.log('Category filter:', categoryFilter);
    
    const machines = document.querySelectorAll('.machine-card');
    console.log('Total machines found:', machines.length);
    
    let visibleCount = 0;
    
    machines.forEach(machine => {
        const machineType = (machine.getAttribute('data-machine-type') || '').toLowerCase();
        const machineName = (machine.getAttribute('data-machine-name') || '').toLowerCase();
        const category = machine.getAttribute('data-category') || '';
        const location = (machine.getAttribute('data-location') || '').toLowerCase();
        
        // Condition 1: Search filter
        let passesSearchFilter = true;
        if (searchTerm !== '') {
            passesSearchFilter = machineType.includes(searchTerm) || 
                                machineName.includes(searchTerm) ||
                                category.toLowerCase().includes(searchTerm) || 
                                location.includes(searchTerm);
        }
        
        // Condition 2: Category filter
        let passesCategoryFilter = true;
        if (categoryFilter !== 'all') {
            passesCategoryFilter = (category === categoryFilter);
        }
        
        // Show if BOTH conditions pass
        const shouldShow = passesSearchFilter && passesCategoryFilter;
        
        if (shouldShow) {
            machine.style.display = 'block';
            visibleCount++;
        } else {
            machine.style.display = 'none';
        }
        
    });
    
}

// Category filter click handlers
const filterChips = document.querySelectorAll('.filter-chip');

filterChips.forEach(chip => {
    chip.addEventListener('click', function() {
        
        // Update active state
        filterChips.forEach(c => c.classList.remove('active'));
        this.classList.add('active');
        
        // Re-run filter
        filterMachines();
    });
});

// Initial load - show all machines
console.log('Search.js loaded successfully');
filterMachines();