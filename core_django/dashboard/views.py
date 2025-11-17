import requests  
import jwt       
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import StudentForm, CourseForm, ManageRosterForm, PaymentForm
from .models import Student, Course, Payment

# This is the URL of *internal* Flask service
FLASK_API_URL = "http://127.0.0.1:5001/api/v1/get-data"
FLASK_VALIDATE_URL = "http://127.0.0.1:5001/api/v1/validate-student"

@login_required
def fetch_flask_data(request):
    """
    1. Fetches the list of students owned by the current user.
    2. Generates a JWT token for the logged-in user.
    3. Sends a request with that token to the Flask service.
    4. Renders the response from Flask.
    """

    # QUERY FOR STUDENTS
    # Get all students associated with the currently logged-in user
    students = Student.objects.filter(user=request.user).order_by('last_name')

    # Add the 'students' list to the context
    context = {
        "flask_response": None,
        "error": None,
        "students": students  # <-- ADDED THIS LINE
    }

    try: 
        # 1. Generate JWT Token 
        payload = {
            'user_id': request.user.id,
            'username': request.user.username
        }
        token = jwt.encode(payload, settings.SHARED_SECRET_KEY, algorithm="HS256")

        # 2. Make Request to Flask 
        headers = {
            'Authorization': f'Bearer {token}'
        }
        response = requests.get(FLASK_API_URL, headers=headers, timeout=5)
        response.raise_for_status()
        context["flask_response"] = response.json()

    except requests.exceptions.ConnectionError:
        context["error"] = "Could not connect to the Flask service. Is it running?"
    except requests.exceptions.Timeout:
        context["error"] = "The request to the Flask service timed out."
    except requests.exceptions.HTTPError as e:
        context["error"] = f"HTTP Error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        context["error"] = f"An unexpected error occurred: {e}"

    # 3. Render Template
    # This line now passes the 'students' list to HTML
    return render(request, 'dashboard/index.html', context)

@login_required
def add_student(request):
    if request.method == 'POST':
        form = StudentForm(request.POST, user=request.user)
        
        if form.is_valid():
            # 1. Calculate the Initial Balance based on Courses
            selected_courses = form.cleaned_data['courses']
            initial_balance = 0
            for course in selected_courses:
                initial_balance += course.cost
            
            # 2. Prepare Data for Flask Validation
            student_data = form.cleaned_data.copy() # Copy to avoid messing up the form
            
            # Convert courses to a list of IDs or Names for JSON serialization
            # (Flask can't read Django objects directly)

            student_data['courses'] = [c.name for c in selected_courses] 
            student_data['current_balance'] = str(initial_balance) # Send the calculated cost

            # START FLASK VALIDATION 
            payload = {'user_id': request.user.id, 'action': 'validate'}
            token = jwt.encode(payload, settings.SHARED_SECRET_KEY, algorithm="HS256")
            headers = {'Authorization': f'Bearer {token}'}

            try:
                response = requests.post(FLASK_VALIDATE_URL, headers=headers, json=student_data, timeout=5)
                response.raise_for_status()
                validation_result = response.json()

                if validation_result.get('validation_ok'):
                    # 3. Validation Passed - Save the Student
                    student = form.save(commit=False)
                    student.user = request.user
                    
                    # SET THE CALCULATED BALANCE
                    student.current_balance = initial_balance 
                    
                    student.save()
                    form.save_m2m() # Important: Saves the Course links
                    
                    return redirect('/') 
                else:
                    error_msg = validation_result.get('error', 'Validation failed.')
                    form.add_error(None, error_msg)

            except requests.exceptions.RequestException as e:
                form.add_error(None, f"Validation service is offline: {e}")
            # END FLASK VALIDATION

    else:
        form = StudentForm(user=request.user)

    return render(request, 'dashboard/add_student.html', {'form': form})

def register(request):
    """Handles new user registration."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Automatically log the user in after registration
            login(request, user) 
            return redirect('/') # Redirect to the main dashboard
    else:
        form = UserCreationForm()
        
    return render(request, 'dashboard/register.html', {'form': form})

@login_required
def edit_student(request, pk):
    # Get the specific student object, or return a 404 error if not found
    student = get_object_or_404(Student, pk=pk, user=request.user)

    if request.method == 'POST':
        # Load the form with the submitted POST data *and* the existing student instance
        form = StudentForm(request.POST, instance=student)
        
        # NOTE: Will be skipping Flask validation on 'edit' for this prototype
        # to keep it simple, add it back here just like in add_student.
        if form.is_valid():
            form.save()
            return redirect('/') # Redirect to dashboard after saving
    else:
        # This is a GET request, so show the form pre-filled with the student's data
        form = StudentForm(instance=student)

    return render(request, 'dashboard/edit_student.html', {
        'form': form,
        'student': student
    })

@login_required
def delete_student(request, pk):
    # Get the specific student object, or return a 404 error if not found
    student = get_object_or_404(Student, pk=pk, user=request.user)

    if request.method == 'POST':
        # This is a POST request, so delete the object
        student.delete()
        return redirect('/') # Redirect to dashboard after deleting

    # This is a GET request, so show the confirmation page
    return render(request, 'dashboard/delete_student.html', {
        'student': student
    })

@login_required
def course_list(request):
    """Display a list of all courses owned by the logged-in user."""
    courses = Course.objects.filter(user=request.user).order_by('name')
    return render(request, 'dashboard/course_list.html', {'courses': courses})


@login_required
def add_course(request):
    """Handle adding a new course."""
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.user = request.user  # Assign the logged-in user
            course.save()
            return redirect('course_list') # Go back to the course list
    else:
        form = CourseForm()
    
    # Use a generic form template
    return render(request, 'dashboard/course_form.html', {
        'form': form,
        'title': 'Add New Course' # Pass a title
    })


@login_required
def edit_course(request, pk):
    """Handle editing an existing course."""
    course = get_object_or_404(Course, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            return redirect('course_list')
    else:
        form = CourseForm(instance=course)
    
    return render(request, 'dashboard/course_form.html', {
        'form': form,
        'title': 'Edit Course' # Pass a different title
    })


@login_required
def delete_course(request, pk):
    """Handle deleting a course."""
    course = get_object_or_404(Course, pk=pk, user=request.user)
    
    if request.method == 'POST':
        course.delete()
        return redirect('course_list')
        
    return render(request, 'dashboard/course_confirm_delete.html', {
        'course': course
    })

@login_required
def manage_roster(request, pk):
    # Get the course, making sure it's owned by the logged-in user
    course = get_object_or_404(Course, pk=pk, user=request.user)
    
    if request.method == 'POST':
        # Create the form instance with the logged-in user
        form = ManageRosterForm(request.POST, user=request.user)
        if form.is_valid():
            selected_students = form.cleaned_data['students']
            current_students = set(student for student in course.student_set.filter(user=request.user))
            
            for student in selected_students:
                if student not in current_students:
                    student.courses.add(course)
                    student.current_balance += course.cost
                    student.save()
            
            return redirect('course_list')
    else:
        # GET Request: Pre-fill the form with students already in the course
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
    # Get the student we are adding a payment for
    student = get_object_or_404(Student, pk=student_pk, user=request.user)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            # Get the payment amount
            payment_amount = form.cleaned_data['amount']
            
            # 1. Create the Payment object
            payment = form.save(commit=False)
            payment.student = student
            payment.user = request.user
            payment.save()
            
            # 2. Update the student's balance
            # We subtract the payment from their outstanding balance
            student.current_balance -= payment_amount
            student.save()
            
            return redirect('/') # Redirect to the main dashboard
    else:
        form = PaymentForm()

    return render(request, 'dashboard/add_payment.html', {
        'form': form,
        'student': student
    })