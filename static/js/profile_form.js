// profile_form.js - Handle school/major/minor dropdown filtering

// Major data organized by school (matches forms.py)
// Each major is just a string since value and label are the same
const MAJORS_BY_SCHOOL = {
    'MCAS': [
        'African and African Diaspora Studies',
        'Applied Physics',
        'Art History',
        'Biochemistry',
        'Biology',
        'Chemistry',
        'Classics',
        'Communication',
        'Computer Science',
        'Economics',
        'English',
        'Environmental Geoscience',
        'Environmental Studies',
        'Film Studies',
        'French',
        'Geological Sciences',
        'German Studies',
        'Hispanic Studies',
        'History',
        'Human-Centered Engineering',
        'Independent Major',
        'International Studies',
        'Islamic Civilization and Societies',
        'Italian',
        'Linguistics',
        'Mathematics',
        'Music',
        'Neuroscience',
        'Philosophy',
        'Physics',
        'Political Science',
        'Psychology',
        'Russian',
        'Slavic Studies',
        'Sociology',
        'Studio Art',
        'Theatre',
        'Theology',
    ],
    'CSOM': [
        'Accounting for CPAs',
        'Accounting for Finance & Consulting',
        'Finance',
        'General Business',
        'General Management',
        'Information Systems',
        'Management & Leadership',
        'Managing for Social Impact & the Public Good',
        'Marketing',
        'Operations Management',
    ],
    'CSON': [
        'Nursing (B.S.)',
        'Global Public Health and the Common Good (B.A./B.S.)',
    ],
    'LSEHD': [
        'Applied Psychology & Human Development',
        'Elementary Education',
        'Secondary Education',
        'Transformative Educational Studies',
    ],
};

/**
 * Update major dropdown based on selected school
 * @param {string} schoolSelectId - ID of the school select element
 * @param {string} majorSelectId - ID of the major select element
 */
function updateMajorDropdown(schoolSelectId, majorSelectId) {
    const schoolSelect = document.getElementById(schoolSelectId);
    const majorSelect = document.getElementById(majorSelectId);
    
    if (!schoolSelect || !majorSelect) return;
    
    const selectedSchool = schoolSelect.value;
    const currentMajorValue = majorSelect.value; // Save current selection
    
    // Clear existing options
    majorSelect.innerHTML = '';
    
    if (!selectedSchool) {
        // No school selected - disable and show placeholder
        majorSelect.disabled = true;
        majorSelect.required = false;
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Select school first';
        majorSelect.appendChild(option);
    } else {
        // Enable dropdown and populate with majors for selected school
        majorSelect.disabled = false;
        majorSelect.required = false; // Make it optional since it's for major2
        
        // Add placeholder option
        const placeholderOption = document.createElement('option');
        placeholderOption.value = '';
        placeholderOption.textContent = 'Select Major';
        majorSelect.appendChild(placeholderOption);
        
        // Add majors for the selected school
        const majors = MAJORS_BY_SCHOOL[selectedSchool] || [];
        majors.forEach((major) => {
            const option = document.createElement('option');
            option.value = major;
            option.textContent = major;
            majorSelect.appendChild(option);
        });
        
        // Try to restore previous selection if it's still valid
        if (currentMajorValue) {
            const optionExists = Array.from(majorSelect.options).some(
                opt => opt.value === currentMajorValue
            );
            if (optionExists) {
                majorSelect.value = currentMajorValue;
            }
        }
    }
}

/**
 * Initialize the profile form dropdowns
 */
function initializeProfileForm() {
    // Set up school 1 -> major 1 filtering
    const school1Select = document.getElementById('id_school1');
    const school2Select = document.getElementById('id_school2');
    
    if (school1Select) {
        // Initialize on page load
        updateMajorDropdown('id_school1', 'id_major1');
        
        // Update when school selection changes
        school1Select.addEventListener('change', function() {
            updateMajorDropdown('id_school1', 'id_major1');
        });
    }
    
    if (school2Select) {
        // Initialize on page load
        updateMajorDropdown('id_school2', 'id_major2');
        
        // Update when school selection changes
        school2Select.addEventListener('change', function() {
            updateMajorDropdown('id_school2', 'id_major2');
        });
    }
    
    // Try to restore school selections from existing major values
    // This helps when editing an existing profile
    restoreSchoolFromMajor('id_major1', 'id_school1');
    restoreSchoolFromMajor('id_major2', 'id_school2');
}

/**
 * Try to determine and set the school based on the current major value
 * This is useful when editing an existing profile
 */
function restoreSchoolFromMajor(majorSelectId, schoolSelectId) {
    const majorSelect = document.getElementById(majorSelectId);
    const schoolSelect = document.getElementById(schoolSelectId);
    
    if (!majorSelect || !schoolSelect || !majorSelect.value) return;
    
    const currentMajor = majorSelect.value;
    
    // Find which school this major belongs to
    for (const [school, majors] of Object.entries(MAJORS_BY_SCHOOL)) {
        const majorExists = majors.includes(currentMajor);
        if (majorExists) {
            schoolSelect.value = school;
            updateMajorDropdown(schoolSelectId, majorSelectId);
            break;
        }
    }
}

// Enable all fields before form submission (disabled fields don't submit)
function enableAllFieldsBeforeSubmit() {
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function() {
            // Enable all disabled fields so they submit their values
            const disabledFields = form.querySelectorAll('select:disabled, input:disabled');
            disabledFields.forEach(field => {
                field.disabled = false;
            });
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeProfileForm();
    enableAllFieldsBeforeSubmit();
});

