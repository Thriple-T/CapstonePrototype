import requests  
import jwt
import os
import joblib
import pandas as pd
import json
from django.utils import timezone
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count, F, Q
from django.db import transaction # ADDED: Import transaction for atomic updates
from django.contrib import messages
from decimal import Decimal
from django.db.models.functions import TruncMonth
from django.conf import settings

# Imports from local modules
from .forms import StudentForm, CourseForm, ManageRosterForm, PaymentForm
from .models import Student, Course, Payment, Enrollment, Attendance, GradeRecord

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

    # Prepare Context
    context = {
        "flask_response": None,
        "error": None,
        "students": students,
        "courses": courses
    }

    return render(request, 'dashboard/index.html', context)

@login_required
def dashboard_home(request):
    """
    The Main Landing Page.
    """
    print("--------------------------------------------------")
    print(f"LOADING DASHBOARD HOME for user: {request.user}")
    user = request.user

    student_list = Student.objects.filter(user=user).order_by('-id')[:10]
    total_students = Student.objects.filter(user=user).count()
    active_students = Student.objects.filter(
        user=user, 
        enrollment__isnull=False
    ).distinct().count()

    revenue_agg = Payment.objects.filter(student__user=user).aggregate(total=Sum('amount'))
    total_revenue = revenue_agg.get('total') or Decimal('0.00')
    
    charges_agg = Enrollment.objects.filter(student__user=user).aggregate(total=Sum('course__cost'))
    total_charges = charges_agg.get('total') or Decimal('0.00')
    total_owed = total_charges - total_revenue

    courses = Course.objects.filter(user=user).order_by('-created_at')

    context = {
        'total_students': total_students,
        'active_students': active_students, # Now reflects the Roster count
        'student_list': student_list,
        'total_revenue': total_revenue,
        'total_owed': total_owed,
        'courses': courses,
    }

    return render(request, 'dashboard/index.html', context)

@login_required
def student_list_view(request):
    """Fetches and displays the list of students for the dashboard."""
    
    # Filter students by the current user
    students = Student.objects.filter(user=request.user).prefetch_related('courses')
    
    context = {
        'students': students,
        'title': 'Student Roster',
        # any other context variables 
    }

    return render(request, 'dashboard/index.html', context)

@login_required
def add_student(request):
    if request.method == 'POST':
        # Pass the user to the form initializer to filter M2M fields
        form = StudentForm(request.POST, user=request.user) 
        if form.is_valid():
            student = form.save(commit=False)
            
            # Assign the foreign key to the current user
            student.user = request.user 
            
            student.save()
            # Must call save_m2m() after saving the student instance
            form.save_m2m() 
            messages.success(request, 'Student added successfully!')
            return redirect('student_detail', pk=student.pk)
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
def student_list(request):
    students = Student.objects.filter(user=request.user)
    return render(request, 'dashboard/student_list.html', {'students': students})

@login_required
def course_detail(request, pk):
    """
    Displays the detailed information for a single course.
    """
    course = get_object_or_404(Course, pk=pk, user=request.user)
    enrolled_students = Student.objects.filter(
        enrollment__course=course
    ).order_by('last_name')

    context = {
        'course': course,
        'enrolled_students': enrolled_students,
    }
    return render(request, 'dashboard/course_detail.html', context)

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
            
            # Assign the foreign key to the current user
            course.user = request.user 
            
            course.save()
            messages.success(request, 'Course added successfully!')
            return redirect('course_list')
    else:
        form = CourseForm()
    
    return render(request, 'dashboard/course_form.html', {'form': form})

@login_required
def edit_course(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            course = form.save(commit=False)
            
            # Assign the foreign key to the current user
            course.user = request.user 
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

        student_ids_to_add = request.POST.getlist('students_to_add')
        
        if student_ids_to_add:
            for student_id in student_ids_to_add:
                student = get_object_or_404(Student, pk=student_id, user=request.user)
                
                # This checks if enrollment exists. If yes, it does nothing. If no, it creates it.
                obj, created = Enrollment.objects.get_or_create(
                    course=course,
                    student=student,
                    defaults={'start_date': timezone.now()}
                )
            
            messages.success(request, f"Successfully enrolled {len(student_ids_to_add)} students.")
            return redirect('manage_roster', pk=course.pk)

        remove_student_id = request.POST.get('remove_student_id')
        
        if remove_student_id:
            student = get_object_or_404(Student, pk=remove_student_id, user=request.user)
            Enrollment.objects.filter(course=course, student=student).delete()
            
            messages.warning(request, f"Removed {student.first_name} from the roster.")
            return redirect('manage_roster', pk=course.pk)
        
        messages.info(request, "No students were selected for action.")
        return redirect('manage_roster', pk=course.pk)
    
    enrolled_students = Student.objects.filter(enrollment__course=course).order_by('last_name')
        
    available_students = Student.objects.filter(user=request.user).exclude(id__in=enrolled_students.values_list('id', flat=True)).order_by('first_name')

    return render(request, 'dashboard/manage_roster.html', {
        'course': course,
        'enrolled_students': enrolled_students,
        'available_students': available_students
    })

@login_required
def add_payment(request, student_pk):
    student = get_object_or_404(Student, pk=student_pk, user=request.user)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.student = student
            payment.user = request.user 
            
            payment.save()
            messages.success(request, f'Payment of ${payment.amount} logged successfully.')
            return redirect('student_detail', pk=student.pk)
    else:
        form = PaymentForm()

    return render(request, 'dashboard/add_payment.html', {'form': form, 'student': student})

def predict_next_revenue(payment_data):
    y = payment_data
    x = list(range(1, len(y) + 1))
    n = len(y)
    if n < 2: return sum(y) / n if n > 0 else 0.0
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_xx = sum(xi ** 2 for xi in x)
    try:
        m = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x ** 2)
        b = (sum_y - m * sum_x) / n
    except ZeroDivisionError:
        return 0.0
    return max(0.0, m * (n + 1) + b)


@login_required
def dashboard_analytics(request):
    total_students = Student.objects.filter(user=request.user).count()
    gender_data = Student.objects.filter(user=request.user).values('gender').annotate(count=Count('id'))
    gender_labels = [item['gender'] for item in gender_data]
    gender_counts = [item['count'] for item in gender_data]
    status_data = Student.objects.filter(user=request.user).values('status').annotate(count=Count('id'))
    status_labels = [item['status'] for item in status_data]
    status_counts = [item['count'] for item in status_data]

    dropped_count = Student.objects.filter(user=request.user, status='Dropped').count()
    churn_rate = (dropped_count / total_students * 100) if total_students > 0 else 0.0

    total_revenue_result = Payment.objects.filter(student__user=request.user).aggregate(total=Sum('amount'))
    total_revenue = total_revenue_result.get('total') or Decimal('0.00')

    total_charges_result = Enrollment.objects.filter(student__user=request.user).aggregate(total=Sum('course__cost'))
    total_charges = total_charges_result.get('total') or Decimal('0.00')
    total_fees_owed = total_charges - total_revenue
    
    # Using aggregate to sum up the delays recorded for all students
    total_late_payments = Student.objects.filter(user=request.user).aggregate(total=Sum('payment_delays'))['total'] or 0

    # Revenue Prediction
    monthly_revenue_query = Payment.objects.filter(student__user=request.user)\
        .annotate(month=TruncMonth('date_of_payment'))\
        .values('month').annotate(total=Sum('amount')).order_by('month')
    
    revenue_series = [float(item['total']) for item in monthly_revenue_query]
    predicted_revenue = predict_next_revenue(revenue_series)
    
    revenue_labels = [item['month'].strftime('%b %Y') for item in monthly_revenue_query]
    if revenue_labels: revenue_labels.append("Forecast")
    chart_revenue_data = revenue_series + [predicted_revenue]

    total_attendance_records = Attendance.objects.filter(student__user=request.user).count()
    present_records = Attendance.objects.filter(student__user=request.user, status='P').count()
    avg_attendance_rate = (present_records / total_attendance_records * 100) if total_attendance_records > 0 else 0.0

    grade_distribution = {
        'A (90-100)': Enrollment.objects.filter(student__user=request.user, current_average__gte=90).count(),
        'B (80-89)': Enrollment.objects.filter(student__user=request.user, current_average__gte=80, current_average__lt=90).count(),
        'C (70-79)': Enrollment.objects.filter(student__user=request.user, current_average__gte=70, current_average__lt=80).count(),
        'D (60-69)': Enrollment.objects.filter(student__user=request.user, current_average__gte=60, current_average__lt=70).count(),
        'F (<60)': Enrollment.objects.filter(student__user=request.user, current_average__lt=60).count(),
    }
    grade_labels = list(grade_distribution.keys())
    grade_counts = list(grade_distribution.values())

    context = {
        'total_students': total_students,
        'churn_rate': churn_rate,
        'status_labels': json.dumps(status_labels),
        'status_counts': json.dumps(status_counts),
        'gender_labels': json.dumps(gender_labels),
        'gender_counts': json.dumps(gender_counts),
        'total_revenue': total_revenue,
        'total_fees_owed': total_fees_owed,
        'total_late_payments': total_late_payments,
        'predicted_revenue': predicted_revenue,
        'revenue_labels': json.dumps(revenue_labels),
        'revenue_data': json.dumps(chart_revenue_data),
        'avg_attendance_rate': avg_attendance_rate,
        'grade_labels': json.dumps(grade_labels),
        'grade_counts': json.dumps(grade_counts),
    }

    return render(request, 'dashboard/analytics.html', context)

@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk, user=request.user)
    
    payments = Payment.objects.filter(student=student).order_by('-date_of_payment')
    enrollment_history = Enrollment.objects.filter(student=student).order_by('-start_date')
    
    total_days = student.attendance_set.count()
    present_days = student.attendance_set.filter(status='P').count()
    attendance_rate = (present_days / total_days) if total_days > 0 else 1.0

    predicted_grade = None
    ml_message = "Not enough data to predict."
    
    try:
        model_path = os.path.join(settings.BASE_DIR, 'ml_engine', 'grade_predictor.pkl')
        
        if os.path.exists(model_path):
            model = joblib.load(model_path)
            
            # Prepare the features exactly as trained
            # Features: ['attendance_rate', 'study_hours', 'previous_grade', 'payment_delays']
            features = pd.DataFrame({
                'attendance_rate': [attendance_rate],
                'study_hours': [student.study_hours],
                'previous_grade': [student.previous_grade],
                'payment_delays': [student.payment_delays] # Assuming this field exists or defaults to 0
            })
            
            # Predict
            prediction = model.predict(features)[0]
            predicted_grade = round(prediction, 1)
            
            # Generate Insight Message
            if predicted_grade > 85:
                ml_message = "High Performer! On track for an A."
            elif predicted_grade > 70:
                ml_message = "Solid Performance. Keep consistent."
            elif predicted_grade > 50:
                ml_message = "Risk Warning. Needs support in attendance or study hours."
            else:
                ml_message = "High Dropout Risk. Immediate intervention required."
                
    except Exception as e:
        print(f"ML Error: {e}")
        ml_message = "AI Model unavailable."

    context = {
        'student': student,
        'payments': payments,
        'enrollment_history': enrollment_history, 
        'page_title': f"{student.first_name}'s Profile",
        
        # Pass AI Data to Template
        'attendance_rate_percent': round(attendance_rate * 100, 1),
        'predicted_grade': predicted_grade,
        'ml_message': ml_message,
    }
    
    return render(request, 'dashboard/student_detail.html', context)

# Define a mapping for day abbreviations used in Course.schedule_days
DAY_ABBREVIATIONS = {
    0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"
}

# In dashboard/views.py

@login_required
def take_attendance(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, user=request.user)
    students = Student.objects.filter(
        enrollment__course=course, 
        status='Active'
    ).order_by('last_name')

    date_str = request.GET.get('date')
    if date_str:
        current_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        current_date = timezone.now().date()

    # SCHEDULE WARNING LOGIC
    schedule_warning = None
    DAY_ABBREVIATIONS = {
        0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'
    }
    
    current_day_abbr = DAY_ABBREVIATIONS.get(current_date.weekday())
    course_schedule = course.schedule_days or "" # e.g., "Mon/Wed/Fri"
    
    if course_schedule and current_day_abbr:
        normalized_schedule = course_schedule.replace(',', ' ').replace('/', ' ')
        
        if current_day_abbr not in normalized_schedule:
            schedule_warning = (
                f"Warning: Attendance is being taken on a {current_date.strftime('%A')}. "
                f"This course is typically scheduled for: {course_schedule}."
            )

    # SAVE ATTENDANCE
    if request.method == 'POST':
        for student in students:
            status_key = f"status_{student.id}"
            status_value = request.POST.get(status_key)
            
            if status_value:
                Attendance.objects.update_or_create(
                    course=course,
                    student=student,
                    date=current_date,
                    defaults={'status': status_value}
                )
        return redirect(f'{request.path}?date={current_date}')

    # PREPARE ROSTER DATA
    roster_data = []
    
    # Get all attendance for this course/date in one query for performance
    existing_attendance = Attendance.objects.filter(course=course, date=current_date)
    attendance_map = {rec.student.id: rec.status for rec in existing_attendance}

    for student in students:
        # Check if we have a status in the map, else None
        status = attendance_map.get(student.id)
        roster_data.append((student, status))

    context = {
        'course': course,
        'current_date': current_date,
        'roster_data': roster_data,
        'schedule_warning': schedule_warning,
    }
    
    return render(request, 'dashboard/take_attendance.html', context)

@login_required
def student_attendance_history(request, student_pk):
    """
    Displays the complete attendance history for a single student across all their courses,
    along with a summary count of P, A, L, E statuses.
    """
    # Fetch the student object, restricting to the current user's students
    student = get_object_or_404(Student, pk=student_pk, user=request.user)
    
    # 1. Fetch all attendance records for this student
    # Order by date descending (most recent first)
    all_attendance_records = Attendance.objects.filter(student=student).order_by('-date')
    
    # 2. Calculate the summary counts
    summary_counts = {
        'P': 0, # Present
        'A': 0, # Absent
        'L': 0, # Late
        'E': 0, # Excused
    }
    
    for record in all_attendance_records:
        # The 'status' field holds the code ('P', 'A', 'L', 'E')
        if record.status in summary_counts:
            summary_counts[record.status] += 1
            
    # 3. Prepare the data for the template
    context = {
        'student': student,
        'attendance_records': all_attendance_records,
        'summary_counts': summary_counts,
        
        # This is useful for displaying the full status name in the template
        'status_labels': {code: label for code, label in Attendance.AttendanceStatus.choices},
    }
    
    return render(request, 'dashboard/student_attendance_history.html', context)

@login_required
def add_grade(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, user=request.user)
    # Get all active students in this course
    students = Student.objects.filter(enrollment__course=course, status='Active')

    if request.method == 'POST':
        description = request.POST.get('description') # e.g., "Unit 1 Test"
        date = request.POST.get('date')
        max_score = float(request.POST.get('max_score')) # e.g., 50

        # Loop through all students to find their scores in the form data
        for student in students:
            score_key = f"score_{student.id}" # Look for input named 'score_5'
            score_val = request.POST.get(score_key)
            
            if score_val: # Only save if a score was entered
                # 1. Create the Grade Record
                GradeRecord.objects.create(
                    student=student,
                    course=course,
                    description=description,
                    date=date,
                    score_obtained=float(score_val),
                    max_score=max_score
                )
                
                # 2. Update the Enrollment Average immediately
                enrollment = Enrollment.objects.filter(student=student, course=course).first()
                if enrollment:
                    enrollment.update_average()

        messages.success(request, f"Grades for '{description}' recorded successfully.")
        return redirect('course_list') # Or back to gradebook

    return render(request, 'dashboard/add_grade.html', {
        'course': course,
        'students': students,
        'current_date': timezone.now()
    })

@login_required
def update_grade(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id)
    
    if request.method == 'POST':
        try:
            new_score = float(request.POST.get('grade'))
            
            # Grades are out of 100 points for simplicity
            GradeRecord.objects.create(
                student=enrollment.student,
                course=enrollment.course,
                description="Manual Adjustment", # The name in the history log
                score_obtained=new_score,
                max_score=100.0,
                date=timezone.now()
            )
            
            # Trigger the Recalculation
            enrollment.update_average()
            
            messages.success(request, f"Grade updated and recorded in history.")
            
        except ValueError:
            messages.error(request, "Invalid grade value.")
            
    return redirect('student_detail', pk=enrollment.student.pk)

@login_required
def course_gradebook(request, pk):
    course = get_object_or_404(Course, pk=pk, user=request.user)
    enrollments = Enrollment.objects.filter(course=course).select_related('student')

    if request.method == 'POST':
        for enrollment in enrollments:
            field_name = f"grade_{enrollment.id}"
            if field_name in request.POST:
                try:
                    new_score = float(request.POST.get(field_name))
                    
                    # Check if score is different to avoid spamming history with duplicates
                    # (Simple check: is the new score different from current avg? 
                    #  Or just always record it as a new entry. Let's always record.)
                    
                    GradeRecord.objects.create(
                        student=enrollment.student,
                        course=course,
                        description="Gradebook Entry",
                        score_obtained=new_score,
                        max_score=100.0,
                        date=timezone.now()
                    )
                    
                    enrollment.update_average()
                    
                except ValueError:
                    continue 
        
        messages.success(request, f"Grades recorded for {course.name}")
        return redirect('course_gradebook', pk=course.pk)

    return render(request, 'dashboard/course_gradebook.html', {
        'course': course,
        'enrollments': enrollments
    })
