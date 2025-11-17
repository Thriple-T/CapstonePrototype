from django.apps import AppConfig

class DashboardConfig(AppConfig):  # MUST match the name Django is looking for
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'