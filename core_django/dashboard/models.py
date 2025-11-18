from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Course(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    course_code = models.CharField(max_length=20, blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    schedule_days = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., Mon/Wed")
    start_time = models.TimeField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    
    # Automatically records the timestamp when click on "Save Course"
    created_at = models.DateTimeField(auto_now_add=True)

class Student(models.Model):
    class StudentStatus(models.TextChoices):
        ACTIVE = 'ACT', 'Active'
        LEAVE = 'LVE', 'On Leave'
        DROPPED = 'DRP', 'Dropped Out'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    student_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    status = models.CharField(
        max_length=3,
        choices=StudentStatus.choices,
        default=StudentStatus.ACTIVE
    )

    current_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    courses = models.ManyToManyField(Course, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student_id', 'first_name', 'last_name') 

    @property
    def absolute_balance(self):
        return abs(self.current_balance)

    def __str__(self):
        return f"{self.first_name} {self.last_name} (Owner: {self.user.username})"

class Payment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)

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
    
    # Snapshot the schedule here. Why? 
    # If the course schedule changes next year, the user still want to know 
    # what the schedule was *when this student took it.
    schedule_snapshot = models.CharField(max_length=100, blank=True, help_text="e.g. Wed/Thurs @ 5pm")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.student} in {self.course} ({self.start_date})"