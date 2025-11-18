from django.urls import path
from . import views

urlpatterns = [
    path('', views.fetch_flask_data, name='fetch_data'),
    path('register/', views.register, name='register'),
    
    # Student Paths
    path('student/add/', views.add_student, name='add_student'),
    path('student/edit/<int:pk>/', views.edit_student, name='edit_student'),
    path('student/delete/<int:pk>/', views.delete_student, name='delete_student'),
    path('student/detail/<int:pk>/', views.student_detail, name='student_detail'),

    # Course Paths
    path('courses/', views.course_list, name='course_list'),
    path('course/add/', views.add_course, name='add_course'),
    path('course/edit/<int:pk>/', views.edit_course, name='edit_course'),
    path('course/delete/<int:pk>/', views.delete_course, name='delete_course'),
    path('course/manage/<int:pk>/', views.manage_roster, name='manage_roster'),

    # Payment Paths
    path('student/<int:student_pk>/add-payment/', views.add_payment, name='add_payment'),

    # Dashboard Analytics Path
    path('analytics/', views.dashboard_analytics, name='dashboard_analytics'),
]