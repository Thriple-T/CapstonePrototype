from django import forms
from .models import Student, Course, Payment 

class StudentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # Safely pop the 'user' argument that is passed from the view
        kwargs.pop('user', None) 
        super(StudentForm, self).__init__(*args, **kwargs)
        # Note: The courses field and its related filtering logic has been removed.

    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'student_id', 
            'email', 'age', 'gender', 'city', 'country', 'status',
        ]

class CourseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # Safely pop 'user' to prevent the TypeError
        kwargs.pop('user', None) 
        super(CourseForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Course
        fields = ['name', 'course_code', 'cost', 'schedule_days', 'start_time', 'end_time', 'end_date']
        
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
class ManageRosterForm(forms.Form):
    students = forms.ModelMultipleChoiceField(
        queryset=Student.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(ManageRosterForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['students'].queryset = Student.objects.filter(user=user)

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'date_of_payment', 'notes']
        widgets = {
            'date_of_payment': forms.DateInput(attrs={'type': 'date'}),
        }