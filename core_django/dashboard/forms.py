from django import forms
from .models import Student, Course, Payment

class StudentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # Get the 'user' object from the view
        user = kwargs.pop('user', None)
        super(StudentForm, self).__init__(*args, **kwargs)
        
        # If a user was passed in, filter the 'courses' field
        if user:
            self.fields['courses'].queryset = Course.objects.filter(user=user)

    class Meta:
        model = Student
        fields = [
            'first_name', 
            'last_name', 
            'student_id', 
            'email', 
            'status',
            'courses'
        ]

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'course_code', 'cost']

class ManageRosterForm(forms.Form):
    # This field will render as a multi-select box
    students = forms.ModelMultipleChoiceField(
        queryset=Student.objects.none(),  # Set the real queryset in __init__
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def __init__(self, *args, **kwargs):
        # Get the 'user' object from the view
        user = kwargs.pop('user', None)
        super(ManageRosterForm, self).__init__(*args, **kwargs)

        if user:
            # This is the key: only show students owned by the logged-in user
            self.fields['students'].queryset = Student.objects.filter(user=user)

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_date', 'notes']
        
        # Add a date picker widget for easier use
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
        }