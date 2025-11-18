from django.contrib import admin
from .models import Course, Student

admin.site.register(Course)
admin.site.register(Student) 

#For now go here to make admin changes to models directly
# http://127.0.0.1:8000/admin/