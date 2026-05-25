from django.apps import AppConfig
import os

class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'

    def ready(self):
        if os.environ.get('RUN_MAIN', None) == 'true' or not os.environ.get('RUN_MAIN'):
            # we check if it is running main to avoid double execution in development
            from . import tasks
            # tasks.start_scheduler() might be called outside runserver if running migrations. Keep it simple.
            try:
                tasks.start_scheduler()
            except Exception as e:
                pass
