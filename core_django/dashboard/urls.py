from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.fetch_flask_data, name='fetch_data'),
    path('register/', views.register, name='register'),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    # Student Paths
    path('student/<int:pk>/', views.student_detail, name='student_detail'),
    path('student/add/', views.add_student, name='add_student'),
    path('student/edit/<int:pk>/', views.edit_student, name='edit_student'),
    path('student/delete/<int:pk>/', views.delete_student, name='delete_student'),\
    path('students/', views.student_list, name='student_list'),

    # Course Paths
    path('courses/', views.course_list, name='course_list'),
    path('course/<int:course_pk>/attendance/', views.take_attendance, name='take_attendance'),
    path('course/add/', views.add_course, name='add_course'),
    path('course/edit/<int:pk>/', views.edit_course, name='edit_course'),
    path('course/delete/<int:pk>/', views.delete_course, name='delete_course'),
    path('course/manage/<int:pk>/', views.manage_roster, name='manage_roster'),

    # Payment Paths
    path('student/<int:student_pk>/add-payment/', views.add_payment, name='add_payment'),

    #Attendance Paths
    path('student/<int:student_pk>/history/', views.student_attendance_history, name='student_attendance_history'),

    # Dashboard Analytics Path
    path('analytics/', views.dashboard_analytics, name='dashboard_analytics'),
]