import requests  
import jwt
from django.utils import timezone
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

# UPDATE IMPORTS TO INCLUDE Payment and PaymentForm
from .forms import StudentForm, CourseForm, ManageRosterForm, PaymentForm
from .models import Student, Course, Payment, Enrollment, Attendance

FLASK_API_URL = "http://127.0.0.1:5001/api/v1/get-data"
FLASK_VALIDATE_URL = "http://127.0.0.1:5001/api/v1/validate-student"
FLASK_PREDICT_URL = "http://127.0.0.1:5001/api/v1/predict-risk"

@login_required
def fetch_flask_data(request):
    """
    1. Fetches the list of students and courses owned by the current user.
    2. Generates a JWT token for the logged-in user.
    3. Sends a request with that token to the Flask service.
    4. Renders the response from Flask.
    """
    students = Student.objects.filter(user=request.user).order_by('last_name')
    courses = Course.objects.filter(user=request.user).order_by('name')

    # Calculate Risk (In-Memory)
    # This adds the 'risk' attribute to each student object for the template
    for student in students:
        try:
            # Logic: If balance > $500 or courses < 1, high risk
            risk_label = "Low Risk"
            risk_score = 10
            
            if student.current_balance > 500:
                risk_label = "Critical"
                risk_score = 90
            elif student.courses.count() == 0:
                risk_label = "Moderate Risk"
                risk_score = 50
                
            student.risk = {'label': risk_label, 'risk_score': risk_score}
        except Exception:
            student.risk = {'label': 'Error', 'risk_score': 0}

    # 3. Prepare Context
    context = {
        "flask_response": None,
        "error": None,
        "students": students,
        "courses": courses
    }

    return render(request, 'dashboard/index.html', context)


@login_required
def add_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST, user=request.user)
        
        if form.is_valid():
            selected_courses = form.cleaned_data['courses']
            initial_balance = 0
            for course in selected_courses:
                initial_balance += course.cost
            
            student_data = form.cleaned_data.copy()
            student_data['courses'] = [c.name for c in selected_courses] 
            student_data['current_balance'] = str(initial_balance)

            payload = {'user_id': request.user.id, 'action': 'validate'}
            token = jwt.encode(payload, settings.SHARED_SECRET_KEY, algorithm="HS256")
            headers = {'Authorization': f'Bearer {token}'}

            try:
                response = requests.post(FLASK_VALIDATE_URL, headers=headers, json=student_data, timeout=5)
                response.raise_for_status()
                validation_result = response.json()

                if validation_result.get('validation_ok'):
                    student = form.save(commit=False)
                    student.user = request.user
                    student.current_balance = initial_balance 
                    student.save()
                    form.save_m2m()
                    return redirect('/') 
                else:
                    error_msg = validation_result.get('error', 'Validation failed.')
                    form.add_error(None, error_msg)
            except requests.exceptions.RequestException as e:
                form.add_error(None, f"Validation service is offline: {e}")

    else:
        form = StudentForm(user=request.user)

    return render(request, 'dashboard/add_student.html', {'form': form})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) 
            return redirect('/') 
    else:
        form = UserCreationForm()
    return render(request, 'dashboard/register.html', {'form': form})

@login_required
def edit_student(request, pk):
    student = get_object_or_404(Student, pk=pk, user=request.user)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('/') 
    else:
        form = StudentForm(instance=student, user=request.user)
    return render(request, 'dashboard/edit_student.html', {'form': form, 'student': student})

@login_required
def delete_student(request, pk):
    student = get_object_or_404(Student, pk=pk, user=request.user)
    if request.method == 'POST':
        student.delete()
        return redirect('/') 
    return render(request, 'dashboard/delete_student.html', {'student': student})

@login_required
def course_list(request):
    courses = Course.objects.filter(user=request.user).order_by('name')
    return render(request, 'dashboard/course_list.html', {'courses': courses})

@login_required
def add_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.user = request.user
            course.save()
            return redirect('course_list')
    else:
        form = CourseForm()
    return render(request, 'dashboard/course_form.html', {'form': form, 'title': 'Add New Course'})

@login_required
def edit_course(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            return redirect('course_list')
    else:
        form = CourseForm(instance=course)
    return render(request, 'dashboard/course_form.html', {'form': form, 'title': 'Edit Course'})

@login_required
def delete_course(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    if request.method == 'POST':
        course.delete()
        return redirect('course_list')
    return render(request, 'dashboard/course_confirm_delete.html', {'course': course})

@login_required
def manage_roster(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = ManageRosterForm(request.POST, user=request.user)
        if form.is_valid():
            selected_students = form.cleaned_data['students']
            current_students = set(student for student in course.student_set.filter(user=request.user))
            
            for student in selected_students:
                if student not in current_students:
                    # 1. Add to the "Live" Roster 
                    student.courses.add(course)
                    
                    # 2. Update Financials 
                    student.current_balance += course.cost
                    student.save()
                    
                    # 3. CREATE ENROLLMENT HISTORY
                    # Create a string for the schedule snapshot
                    sched_str = f"{course.schedule_days}"
                    if course.start_time:
                        sched_str += f" @ {course.start_time.strftime('%I:%M %p')}"
                    
                    Enrollment.objects.create(
                        student=student,
                        course=course,
                        start_date=timezone.now(),
                        schedule_snapshot=sched_str,
                        is_active=True
                    )
            
            return redirect('course_list')
    else:
        form = ManageRosterForm(
            user=request.user,
            initial={'students': course.student_set.all()}
        )
        
    return render(request, 'dashboard/manage_roster.html', {
        'form': form,
        'course': course
    })

@login_required
def add_payment(request, student_pk):
    student = get_object_or_404(Student, pk=student_pk, user=request.user)
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment_amount = form.cleaned_data['amount']
            payment = form.save(commit=False)
            payment.student = student
            payment.user = request.user
            payment.save()
            
            student.current_balance -= payment_amount
            student.save()
            return redirect('/') 
    else:
        form = PaymentForm()
    return render(request, 'dashboard/add_payment.html', {'form': form, 'student': student})

@login_required
def dashboard_analytics(request):
    """Calculates and displays key descriptive analytics."""
    
    # Filter data to only include records owned by the logged-in user
    user_payments = Payment.objects.filter(user=request.user)
    user_students = Student.objects.filter(user=request.user)
    
    # 1. Overall Revenue (Sum of all payments received)
    total_revenue_result = user_payments.aggregate(Sum('amount'))
    total_revenue = total_revenue_result['amount__sum'] or 0
    
    # 2. Total Outstanding Fees (Sum of positive student balances)
    # We only sum balances > 0 (what they owe, not what they prepaid)
    total_owed_result = user_students.filter(current_balance__gt=0).aggregate(Sum('current_balance'))
    total_owed = total_owed_result['current_balance__sum'] or 0
    
    # 3. Key Metrics
    total_students = user_students.count()
    total_courses = Course.objects.filter(user=request.user).count()

    context = {
        'total_revenue': total_revenue,
        'total_owed': total_owed,
        'total_students': total_students,
        'total_courses': total_courses,
    }
    
    return render(request, 'dashboard/analytics.html', context)

@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk, user=request.user)
    payments = Payment.objects.filter(student=student).order_by('-payment_date')
    
    # Fetch Enrollment History
    enrollment_history = Enrollment.objects.filter(student=student).order_by('-start_date')
    
    context = {
        'student': student,
        'payments': payments,
        'enrollment_history': enrollment_history, # <-- Pass this to template
    }
    
    return render(request, 'dashboard/student_detail.html', context)