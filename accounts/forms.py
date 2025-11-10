from django import forms
from .models import StudentProfile

# School choices
SCHOOL_CHOICES = [
    ('', 'Select School'),
    ('MCAS', 'MCAS - Morrissey College of Arts and Sciences'),
    ('CSOM', 'CSOM - Carroll School of Management'),
    ('CSON', 'CSON - Connell School of Nursing'),
    ('LSEHD', 'LSEHD - Lynch School of Education and Human Development'),
]

# Helper function to convert list of strings to Django choice tuples
def make_choices(items):
    """Convert a list of strings to Django choice tuples (value, label)"""
    return [(item, item) for item in items]

# Major choices organized by school
MAJORS_BY_SCHOOL = {
    'MCAS': make_choices([
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
    ]),
    'CSOM': make_choices([
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
    ]),
    'CSON': make_choices([
        'Nursing (B.S.)',
        'Global Public Health and the Common Good (B.A./B.S.)',
    ]),
    'LSEHD': make_choices([
        'Applied Psychology & Human Development',
        'Elementary Education',
        'Secondary Education',
        'Transformative Educational Studies',
    ]),
}

# All majors for fallback (used when school is not selected)
ALL_MAJORS = []
for school_majors in MAJORS_BY_SCHOOL.values():
    ALL_MAJORS.extend(school_majors)
ALL_MAJORS = sorted(set(ALL_MAJORS), key=lambda x: x[1])

# Minor choices (alphabetical)
MINOR_CHOICES = [('', 'Select Minor')] + make_choices([
    'Accounting',
    'Ancient Greek',
    'Arabic Studies',
    'Art History',
    'Biology',
    'Business Analytics',
    'Chemistry',
    'Chinese',
    'Computer Science',
    'Economics',
    'English',
    'Finance',
    'Film Studies',
    'French',
    'Geological Sciences',
    'German',
    'Global Public Health and Common Good',
    'Hispanic Studies',
    'History',
    'Information Systems',
    'Italian',
    'Latin',
    'Linguistics',
    'Management',
    'Marketing',
    'Mathematics',
    'Music',
    'Philosophy',
    'Physics',
    'Russian',
    'Sociology',
    'Studio Art',
    'Theatre',
    'Theology',
])

class StudentProfileForm(forms.ModelForm):
    school1 = forms.ChoiceField(
        choices=SCHOOL_CHOICES,
        required=False,
        label="School (for Major 1)",
        widget=forms.Select(attrs={"id": "id_school1", "class": "school-select"})
    )
    school2 = forms.ChoiceField(
        choices=SCHOOL_CHOICES,
        required=False,
        label="School (for Major 2)",
        widget=forms.Select(attrs={"id": "id_school2", "class": "school-select"})
    )
    
    class Meta:
        model = StudentProfile
        fields = ["major1", "major2", "minor1", "minor2"]
        widgets = {
            "major1": forms.Select(attrs={"id": "id_major1", "class": "major-select"}),
            "major2": forms.Select(attrs={"id": "id_major2", "class": "major-select"}),
            "minor1": forms.Select(choices=MINOR_CHOICES, attrs={"id": "id_minor1", "class": "minor-select"}),
            "minor2": forms.Select(choices=MINOR_CHOICES, attrs={"id": "id_minor2", "class": "minor-select"}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        
        # Set initial choices for majors (will be updated by JavaScript)
        self.fields['major1'].choices = [('', 'Select school first')]
        self.fields['major2'].choices = [('', 'Select school first')]
        
        # If editing existing profile, try to determine schools from existing majors
        if instance:
            # Try to find school for major1
            if instance.major1:
                for school, majors in MAJORS_BY_SCHOOL.items():
                    if any(value == instance.major1 for value, _ in majors):
                        self.fields['school1'].initial = school
                        # Populate major1 choices for this school
                        self.fields['major1'].choices = [('', 'Select Major')] + MAJORS_BY_SCHOOL[school]
                        break
            
            # Try to find school for major2
            if instance.major2:
                for school, majors in MAJORS_BY_SCHOOL.items():
                    if any(value == instance.major2 for value, _ in majors):
                        self.fields['school2'].initial = school
                        # Populate major2 choices for this school
                        self.fields['major2'].choices = [('', 'Select Major')] + MAJORS_BY_SCHOOL[school]
                        break