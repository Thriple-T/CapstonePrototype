from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # This line "turns on" the admin panel and its login page
    path('admin/', admin.site.urls), 
    
    # This line includes the dashboard app at the root
    path('', include('dashboard.urls')),
]