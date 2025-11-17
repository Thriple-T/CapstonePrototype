import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dashboard.apps.DashboardConfig',
    'django.contrib.humanize',
]

# may add rest of the settings in later dev

SHARED_SECRET_KEY="a-key-that-is-numyabusizness"
SECRET_KEY = 'idk-let-me-just-put-some-random-string-here-1234567890'

# Also add a login URL (for the @login_required decorator)
LOGIN_URL = '/admin/login/' # Easiest way for this prototype

# core/settings.py

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    
    # The error says to put SessionMiddleware before AuthenticationMiddleware
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Note: MIDDLEWARE list might have slightly different entries,
# The key is 'django.contrib.sessions.middleware.SessionMiddleware'
# Must appear before 'django.contrib.auth.middleware.AuthenticationMiddleware'.

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # We will keep this empty for this simple prototype
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages', # <-- Crucial for admin messages
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # <-- This uses the Path object for prototype
    }
}

DEBUG = True 

# Add the local addresses
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/
STATIC_URL = '/static/'

# This points Django to main urls.py file (core/urls.py)
ROOT_URLCONF = 'core.urls'

# This line is important, keep it
WSGI_APPLICATION = 'core.wsgi.application'