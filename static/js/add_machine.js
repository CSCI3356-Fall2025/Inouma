// Additional validation for image upload (now allows HEIC)
const imageInput = document.getElementById('customImageInput');

if (imageInput) {
    imageInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        const fileName = file.name.toLowerCase();
        const allowedExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif'];
        
        // Check for allowed formats
        if (!allowedExtensions.some(ext => fileName.endsWith(ext))) {
            alert('Invalid file format. Please upload a JPG, PNG, GIF, WebP, or HEIC image.');
            e.target.value = ''; // Clear the input
            return;
        }
        
        // Show info message if HEIC
        if (fileName.endsWith('.heic') || fileName.endsWith('.heif')) {
            console.log('HEIC file detected - will be converted to JPG automatically');
        }
    });
}


let duplicateCheckPassed = false;

// Training level cascade
function handleTrainingLevelChange() {
    const level1 = document.getElementById('level1');
    const level2 = document.getElementById('level2');
    const level3 = document.getElementById('level3');
    
    if (level3.checked) {
        level2.checked = true;
        level1.checked = true;
    }
    if (level2.checked) {
        level1.checked = true;
    }
    if (!level1.checked) {
        level2.checked = false;
        level3.checked = false;
    }
    if (!level2.checked) {
        level3.checked = false;
    }
}

// Image selection handling
function handleImageChoice() {
    const choice = document.getElementById('imageChoice').value;
    const existingSection = document.getElementById('existingImageSection');
    const uploadSection = document.getElementById('uploadImageSection');
    const hiddenChoice = document.getElementById('imageChoiceHidden');
    
    // Hide all sections first
    existingSection.style.display = 'none';
    uploadSection.style.display = 'none';
    
    // Show relevant section and set hidden field
    if (choice === 'none') {
        hiddenChoice.value = 'default';
    } else if (choice === 'existing') {
        existingSection.style.display = 'block';
        hiddenChoice.value = 'existing';
    } else if (choice === 'upload') {
        uploadSection.style.display = 'block';
        hiddenChoice.value = 'upload';
    }
}

// Filter images by category
function filterImagesByCategory() {
    const selectedCategory = document.getElementById('categoryFilter').value;
    const categoryDivs = document.querySelectorAll('.category-images');
    
    categoryDivs.forEach(div => {
        const category = div.getAttribute('data-category');
        if (selectedCategory === 'all' || selectedCategory === category) {
            div.style.display = 'block';
        } else {
            div.style.display = 'none';
        }
    });
}

// Highlight selected image
function selectExistingImage(radio) {
    document.querySelectorAll('.image-option').forEach(el => {
        el.style.border = '2px solid #ddd';
        el.style.background = 'white';
    });
    
    const imageOption = radio.closest('label').querySelector('.image-option');
    imageOption.style.border = '2px solid var(--maroon)';
    imageOption.style.background = 'var(--light-gold)';
}

// Machine type autocomplete
const machineTypeInput = document.getElementById('machineTypeInput');
const suggestionsDiv = document.getElementById('suggestions');
let debounceTimer;

machineTypeInput.addEventListener('input', function() {
    clearTimeout(debounceTimer);
    const query = this.value.trim();
    
    if (query.length < 1) {
        suggestionsDiv.style.display = 'none';
        return;
    }
    
    debounceTimer = setTimeout(() => {
        fetch(`/api/machine-suggestions/?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                if (data.suggestions.length > 0) {
                    suggestionsDiv.innerHTML = data.suggestions.map(suggestion => 
                        `<div style="padding: 0.75rem; cursor: pointer; border-bottom: 1px solid #eee;" 
                              onmouseover="this.style.background='var(--light-gold)'" 
                              onmouseout="this.style.background='white'"
                              onclick="selectSuggestion('${suggestion.replace(/'/g, "\\'")}')">${suggestion}</div>`
                    ).join('');
                    suggestionsDiv.style.display = 'block';
                } else {
                    suggestionsDiv.style.display = 'none';
                }
            });
    }, 300);
});

function selectSuggestion(value) {
    machineTypeInput.value = value;
    suggestionsDiv.style.display = 'none';
}

document.addEventListener('click', function(e) {
    if (!machineTypeInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
        suggestionsDiv.style.display = 'none';
    }
});

// Live duplicate checking
const nameInput = document.getElementById('machineNameInput');
const duplicateWarning = document.getElementById('duplicateWarning');
const duplicateWarningText = document.getElementById('duplicateWarningText');
let duplicateCheckTimer;

function checkForDuplicates() {
    clearTimeout(duplicateCheckTimer);
    
    const name = nameInput.value.trim();
    const machineType = machineTypeInput.value.trim();
    
    if (!name || !machineType) {
        duplicateWarning.style.display = 'none';
        return;
    }
    
    duplicateCheckTimer = setTimeout(async () => {
        try {
            const response = await fetch(`/api/check-duplicate/?name=${encodeURIComponent(name)}&machine_name=${encodeURIComponent(machineType)}`);
            const data = await response.json();
            
            if (data.duplicate) {
                duplicateWarningText.textContent = `A machine "${data.machine_name}" with identifier "${data.name}" already exists in ${data.location}.`;
                duplicateWarning.style.display = 'block';
            } else {
                duplicateWarning.style.display = 'none';
            }
        } catch (error) {
            console.error('Error checking for duplicates:', error);
            duplicateWarning.style.display = 'none';
        }
    }, 500);
}

nameInput.addEventListener('input', checkForDuplicates);
machineTypeInput.addEventListener('input', checkForDuplicates);

// Form submission with duplicate check
const addMachineForm = document.querySelector('form[action="{% url \'add_machine\' %}"]');
const duplicateModal = document.getElementById('duplicateWarningModal');
const duplicateMessage = document.getElementById('duplicateMessage');
const newIdentifierInput = document.getElementById('newIdentifier');

addMachineForm.addEventListener('submit', async function(e) {
    if (duplicateCheckPassed) {
        duplicateCheckPassed = false;
        return;
    }
    
    e.preventDefault();
    
    const name = nameInput.value.trim();
    const machineType = machineTypeInput.value.trim();
    
    if (!name || !machineType) return;
    
    try {
        const response = await fetch(`/api/check-duplicate/?name=${encodeURIComponent(name)}&machine_name=${encodeURIComponent(machineType)}`);
        const data = await response.json();
        
        if (data.duplicate) {
            duplicateMessage.innerHTML = `
                The machine <strong>${data.machine_name}</strong> with identifier <strong>"${data.name}"</strong> 
                already exists in the Hatchery (${data.category} - ${data.location}).<br><br>
                Are you sure you want to create a second machine, or would you like to change the identifier?
            `;
            duplicateModal.style.display = 'block';
        } else {
            duplicateCheckPassed = true;
            addMachineForm.submit();
        }
    } catch (error) {
        console.error('Error checking for duplicates:', error);
        duplicateCheckPassed = true;
        addMachineForm.submit();
    }
});

function closeDuplicateModal() {
    duplicateModal.style.display = 'none';
    newIdentifierInput.value = '';
}

function submitWithDuplicate() {
    duplicateCheckPassed = true;
    closeDuplicateModal();
    addMachineForm.submit();
}

function changeIdentifier() {
    const newName = newIdentifierInput.value.trim();
    if (newName) {
        nameInput.value = newName;
        checkForDuplicates();
    }
    closeDuplicateModal();
}

duplicateModal.addEventListener('click', function(e) {
    if (e.target === duplicateModal) {
        closeDuplicateModal();
    }
});


function toggleAddMachineSection() {
    var section = document.getElementById('addMachineSection');
    var icon = document.getElementById('addMachineToggleIcon');
    if (!section || !icon) return;
    
    if (section.style.display === "none" || section.style.display === "") {
        section.style.display = "block";
        icon.textContent = "▼";
        icon.style.transform = "rotate(90deg)";
    } else {
        section.style.display = "none";
        icon.textContent = "▶";
        icon.style.transform = "rotate(0deg)";
    }
}



