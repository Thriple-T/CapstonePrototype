from django import forms
from .models import Student, Course, Payment 

class StudentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(StudentForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['courses'].queryset = Course.objects.filter(user=user)

    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'student_id', 
            'email', 'status', 'courses'
        ]

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        # Add 'end_date' to the fields list
        fields = ['name', 'course_code', 'cost', 'schedule_days', 'start_time', 'end_date']
        
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            # Add the HTML5 Date Picker for easy selection
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
        fields = ['amount', 'payment_date', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
        }