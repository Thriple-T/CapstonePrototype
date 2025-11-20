from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
                
class Course(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    course_code = models.CharField(max_length=20, blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    schedule_days = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., Mon/Wed")
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    
    end_date = models.DateField(blank=True, null=True)
    
    # Automatically records the timestamp when click on "Save Course"
    created_at = models.DateTimeField(auto_now_add=True)

class Student(models.Model):
    class StudentStatus(models.TextChoices):
        ACTIVE = 'ACT', 'Active'
        LEAVE = 'LVE', 'On Leave'
        DROPPED = 'DRP', 'Dropped Out'

    class GenderChoices(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'
        OTHER = 'O', 'Other'
        PREFER_NOT_TO_SAY = 'P', 'Prefer not to say'

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    student_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    gender = models.CharField(
        max_length=1,
        choices=GenderChoices.choices,
        default=GenderChoices.PREFER_NOT_TO_SAY,
        blank=True,
        null=True
    )
    city = models.CharField(max_length=100, blank=True, null=True) 
    country = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=3,
        choices=StudentStatus.choices,
        default=StudentStatus.ACTIVE
    )

    current_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    courses = models.ManyToManyField(Course, through='Enrollment', related_name='students', blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student_id', 'first_name', 'last_name') 

    @property
    def current_balance(self):
        # Calculate total cost of courses the student is enrolled in through Enrollment
        total_course_cost = self.enrollment_set.aggregate(total=Sum('course__cost'))['total'] or 0
        # Calculate total payments received from the student
        total_payments = self.payment_set.aggregate(total=Sum('amount'))['total'] or 0
        
        return total_course_cost - total_payments

    def __str__(self):
        return f"{self.first_name} {self.last_name} (Owner: {self.user.username})"

class Payment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_of_payment = models.DateField(default=timezone.now)
    reference_id = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    date_recorded = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Payment of ${self.amount} for {self.student.first_name}"
    
class Attendance(models.Model):
    class AttendanceStatus(models.TextChoices):
        PRESENT = 'P', 'Present'
        ABSENT = 'A', 'Absent'
        LATE = 'L', 'Late'
        EXCUSED = 'E', 'Excused'

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=1, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT)
    
    class Meta:
        # Ensures a student can't be marked present twice for the same course on the same day
        unique_together = ('course', 'student', 'date')

    def __str__(self):
        return f"{self.student} - {self.course} - {self.date}"
    
class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(blank=True, null=True)
    
    schedule_snapshot = models.CharField(max_length=100, blank=True, help_text="e.g. Wed/Thurs @ 5pm")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.student} in {self.course} ({self.start_date})"