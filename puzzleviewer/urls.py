from django.urls import path, re_path

from . import views

urlpatterns = [
    re_path('^(?P<puzzle_slug>[^/]+)/$', views.puzzle, name='puzzle'),
    re_path('^(?P<puzzle_slug>[^/]+)/solution/$', views.solution, name='solution'),
    re_path('^(?P<puzzle_slug>[^/]+)/posthunt/$', views.posthunt, name='posthunt'),
    re_path('^(?P<puzzle_slug>[^/]+)/(?P<resource>.*)$', views.resource, name='resource'),
]
