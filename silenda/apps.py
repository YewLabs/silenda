from django.apps import AppConfig
from django.conf import settings

class SilendaConfig(AppConfig):
    name = 'silenda'
    def ready(self):
        if settings.USE_PROFILER:
            import googlecloudprofiler

            try:
                googlecloudprofiler.start(verbose=3)
            except Exception as e:
                print("Skipping profiler: %s" % (e))
