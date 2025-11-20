import requests  
import jwt
from django.utils import timezone
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db import transaction # ADDED: Import transaction for atomic updates
from django.contrib import messages
from decimal import Decimal

# Imports from local modules
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
    """
    Manages the roster for a specific course by explicitly updating Enrollment records.
    - On GET, displays the current students in the course.
    - On POST, updates the enrollment list: removes unselected students and adds new ones.
    """
    # Get the course
    course = get_object_or_404(Course, pk=pk, user=request.user)
    # Get the currently enrolled student IDs
    current_enrolled_students = Student.objects.filter(enrollment__course=course)

    if request.method == 'POST':
        form = ManageRosterForm(request.POST, user=request.user) 
        if form.is_valid():
            selected_students = form.cleaned_data.get('students')
            
            selected_set = set(selected_students)
            current_set = set(current_enrolled_students)
            
            students_to_add = selected_set - current_set
            students_to_remove = current_set - selected_set
            
            # FIX 2: Use an atomic transaction to update Enrollment records
            with transaction.atomic():
                # 1. Remove students: Delete their Enrollment record(s) for this course
                Enrollment.objects.filter(
                    course=course, 
                    student__in=students_to_remove
                ).delete()
                
                # 2. Add students: Create a new Enrollment record for each
                enrollments_to_create = [
                    Enrollment(course=course, student=student) 
                    for student in students_to_add
                ]
                Enrollment.objects.bulk_create(enrollments_to_create)

            messages.success(request, f'Roster for {course.name} updated successfully.')
            return redirect('course_list')
        
    else: # GET request
        # Populate the form with students currently enrolled (so they appear checked)
        form = ManageRosterForm(initial={'students': current_enrolled_students}, user=request.user)
    
    context = {'course': course, 'form': form}
    return render(request, 'dashboard/manage_roster.html', context)

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

@login_required
def dashboard_analytics(request):
    user_students = Student.objects.filter(user=request.user)
    
    # Total Revenue (Sum of payments)
    total_revenue_result = Payment.objects.filter(
        student__user=request.user
    ).aggregate(total=Sum('amount'))
    
    # Use Decimal('0.00') instead of 0.00 (float)
    total_revenue = total_revenue_result.get('total') or Decimal('0.00')

    # Total Fees Charged (Sum of course costs via Enrollment)
    total_charges_result = Enrollment.objects.filter(
        student__user=request.user
    ).aggregate(total_cost=Sum('course__cost'))
    
    # Again use Decimal('0.00') instead of 0.00 (float) [DON'T MAKE THE SAME FREAKING MISTAKE!]
    total_charges = total_charges_result.get('total_cost') or Decimal('0.00')

    # Calculate Balance (Now safe because both are Decimals)
    total_fees_owed = total_charges - total_revenue

    total_students = user_students.count()
    total_courses = Course.objects.filter(user=request.user).count()

    context = {
        'total_students': total_students,
        'total_revenue': total_revenue,
        'total_fees_owed': total_fees_owed,
        'total_courses': total_courses,
    }
    
    return render(request, 'dashboard/analytics.html', context)

@login_required
def student_detail(request, pk):
    """
    Shows a single student's general information and status.
    Uses get_object_or_404 to ensure the student exists AND belongs to the user.
    """
    student = get_object_or_404(Student, pk=pk, user=request.user)
    payments = Payment.objects.filter(student=student).order_by('-date_of_payment')
    
    # Fetch Enrollment History
    enrollment_history = Enrollment.objects.filter(student=student).order_by('-start_date')
    
    context = {
        'student': student,
        'payments': payments,
        'enrollment_history': enrollment_history, # <-- Pass this to template
        'page_title': f"{student.first_name} {student.last_name}'s Profile", 
    }
    
    return render(request, 'dashboard/student_detail.html', context)

# Define a mapping for day abbreviations used in Course.schedule_days
DAY_ABBREVIATIONS = {
    0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"
}

@login_required
def take_attendance(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk, user=request.user)
    
    date_str = request.GET.get('date')
    if date_str:
        current_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        current_date = timezone.now().date()

    schedule_warning = None
    
    # Get the current day abbreviation (e.g., Tuesday -> "Tue")
    current_day_abbr = DAY_ABBREVIATIONS.get(current_date.weekday())
    course_schedule = course.schedule_days or ""
    

    if course_schedule and current_day_abbr:
        scheduled_days_list = [day.strip() for day in course_schedule.split('/')]

        if current_day_abbr not in scheduled_days_list:
            # Generate the warning message
            schedule_warning = (
                f"Warning: Attendance is being taken on a {current_date.strftime('%A')}. "
                f"This course is typically scheduled for: {course_schedule}."
            )

    # Fetch student's active enrollments in this course
    active_enrollments = Enrollment.objects.filter(course=course, is_active=True)
    
    if active_enrollments.exists():
        students = [e.student for e in active_enrollments]
    else:
        students = list(course.student_set.all())

    students.sort(key=lambda x: x.last_name)

    # Saves Attendance
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

    roster_data = []
    for student in students:
        attendance = Attendance.objects.filter(
            course=course, student=student, date=current_date
        ).first()
        status = attendance.status if attendance else None
        roster_data.append((student, status))

    context = {
        'course': course,
        'current_date': current_date,
        'roster_data': roster_data,
        'status_choices': Attendance.AttendanceStatus.choices,
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