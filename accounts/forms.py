from django import forms
from django.core.exceptions import ValidationError
from datetime import date
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
    
    # Role specification choices
    ROLE_SPEC_CHOICES = [
        ('', 'Select Role Type'),
        ('Undergraduate', 'Undergraduate'),
        ('Graduate Student', 'Graduate Student'),
        ('PhD Student', 'PhD Student'),
        ('Other', 'Other'),
    ]
    
    role_specification = forms.ChoiceField(
        choices=ROLE_SPEC_CHOICES,
        required=False,
        label="Role Specification",
        help_text="Specify your student type"
    )
    
    birthday = forms.DateField(
        required=False,
        label="Birthday",
        widget=forms.DateInput(attrs={"type": "date", "id": "id_birthday", "class": "date-input"}),
        help_text="Your date of birth"
    )
    
    graduation_year = forms.IntegerField(
        required=False,
        label="Graduation Year",
        widget=forms.NumberInput(attrs={"id": "id_graduation_year", "class": "year-input", "min": "1900", "max": "2100"}),
        help_text="Expected graduation year (e.g., 2025)"
    )
    
    class Meta:
        model = StudentProfile
        fields = ["major1", "major2", "minor1", "minor2", "birthday", "graduation_year", "role_specification"]
        widgets = {
            "major1": forms.Select(attrs={"id": "id_major1", "class": "major-select"}),
            "major2": forms.Select(attrs={"id": "id_major2", "class": "major-select"}),
            "minor1": forms.Select(choices=MINOR_CHOICES, attrs={"id": "id_minor1", "class": "minor-select"}),
            "minor2": forms.Select(choices=MINOR_CHOICES, attrs={"id": "id_minor2", "class": "minor-select"}),
        }
    
    def __init__(self, *args, **kwargs):
        # Extract user from kwargs if provided (for role-based access control)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        
        # Access control: Restrict major and graduation_year to students only
        if self.user and self.user.role != 'student':
            # Hide/disable major and graduation year fields for non-students
            self.fields['major1'].widget = forms.HiddenInput()
            self.fields['major2'].widget = forms.HiddenInput()
            self.fields['minor1'].widget = forms.HiddenInput()
            self.fields['minor2'].widget = forms.HiddenInput()
            self.fields['school1'].widget = forms.HiddenInput()
            self.fields['school2'].widget = forms.HiddenInput()
            self.fields['graduation_year'].widget = forms.HiddenInput()
            # Keep birthday and role_specification visible for all roles
        
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
    
    def clean_birthday(self):
        """Validate birthday is not in the future and reasonable"""
        birthday = self.cleaned_data.get('birthday')
        if birthday:
            if birthday > date.today():
                raise ValidationError("Birthday cannot be in the future.")
            # Check if age is reasonable (at least 13 years old, not more than 150)
            age = (date.today() - birthday).days // 365
            if age < 13:
                raise ValidationError("You must be at least 13 years old.")
            if age > 150:
                raise ValidationError("Please enter a valid birthday.")
        return birthday
    
    def clean_graduation_year(self):
        """Validate graduation year"""
        graduation_year = self.cleaned_data.get('graduation_year')
        if graduation_year:
            current_year = date.today().year
            if graduation_year < 1900 or graduation_year > current_year + 10:
                raise ValidationError(f'Graduation year must be between 1900 and {current_year + 10}')
        return graduation_year
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        
        # Ensure students have at least major1 if they're a student
        if self.user and self.user.role == 'student':
            major1 = cleaned_data.get('major1')
            if not major1:
                raise ValidationError({
                    'major1': 'Students must select at least one major.'
                })
        
        return cleaned_data