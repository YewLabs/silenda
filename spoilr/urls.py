from django.urls import path, re_path, include

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from . import dashboard
from . import gatekeeper
from . import log
from . import submit
from . import hint
from . import views
from . import shortcuts
from . import emails

urlpatterns = [
    # Uncomment the admin/doc line below to enable admin documentation:
    # re_path('^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    re_path('^admin/', admin.site.urls),

    re_path('^(?:embed/)?submit/puzzle/(?P<puzzle>[^/]+)/$', submit.submit_puzzle, name='submit_puzzle'),
    re_path('^(?:embed/)?submit/survey/([^/]+)/$', submit.submit_survey, name='submit_survey'),
    re_path('^(?:embed/)?submit/contact/$', submit.submit_contact, name='submit_contact'),
    re_path('^(?:embed/)?submit/hint/([^/]+)/$', hint.hint_puzzle, name='submit_hint'),
    re_path('^(?:embed/)?submit/update_team/$', views.update_team, name='update_team'),

    re_path('^hq/hint/$', hint.hint_queue, name='hint_queue'),
    re_path('^hq/hint/([^/]+)/$', hint.hint_queue, name='hint_queue'),
    re_path('^hq/hint/([^/]+)/([^/]+)/$', hint.hint_queue, name='hint_queue'),
    re_path('^hq/queue/$', submit.queue, name='hq_queue'),
    re_path('^hq/queue/(answer|contact)/$', submit.queue, name='hq_queue'),
    re_path('^hq/interactions/$', gatekeeper.interactions_queue, name='all_interactions_queue'),
    re_path('^hq/interaction/(.*)/$', gatekeeper.gatekeeper_interaction_view, name='interaction_queue'),

    re_path('^hq/$', dashboard.dashboard, name='hq'),
    re_path('^hq/all-teams/$', dashboard.all_teams_view, name='all_teams'),
    re_path('^hq/one-team/(.*)/$', dashboard.one_team_view, name='one_team'),
    re_path('^hq/all-puzzles/$', dashboard.all_puzzles_view, name='all_puzzles'),

    re_path('^hq/impersonate/(.*)/$', views.impersonate, name='impersonate'),
    re_path('^hq/end_impersonate/$', views.end_impersonate, name='end_impersonate'),

    re_path('^hq/log/(\d+)?$', log.system_log_view, name='hq_log'),
    re_path('^hq/survey-log/(\d+)?$', log.survey_log_view, name='hq_surveylog'),
    re_path('^hq/hint-log/(\d+)?$', log.hint_log_view, name='hq_hintlog'),
    re_path('^hq/updates/$', views.updates_view, name='hq_updates'),

    re_path('^hq/gatekeeper/$', gatekeeper.gatekeeper_view, name='gatekeeper'),
    re_path('^hq/gatekeeper/prelaunch/$', gatekeeper.gatekeeper_prelaunch_view, name='gatekeeper_prelaunch'),
    re_path('^hq/gatekeeper/launch/$', gatekeeper.gatekeeper_launch_view, name='gatekeeper_launch'),
    re_path('^hq/gatekeeper/unlock_mmo/$', gatekeeper.gatekeeper_unlock_mmo_view, name='gatekeeper_unlock_mmo'),
    re_path('^hq/gatekeeper/force_unlock/$', gatekeeper.gatekeeper_force_unlock_view, name='gatekeeper_force_unlock'),
    re_path('^hq/gatekeeper/disable_mmo/$', gatekeeper.gatekeeper_disable_mmo_view, name='gatekeeper_disable_mmo'),
    re_path('^hq/gatekeeper/nuke_cache/$', gatekeeper.gatekeeper_nuke_cache_view, name='gatekeeper_nuke_cache'),

    re_path('^hq/gatekeeper/release_interactions/$', gatekeeper.gatekeeper_release_interactions_view, name='gatekeeper_release_interactions'),
    re_path('^hq/gatekeeper/complete_interactions/$', gatekeeper.gatekeeper_complete_interactions_view, name='gatekeeper_complete_interactions'),
    re_path('^hq/gatekeeper/quiet_complete_interactions/$', gatekeeper.gatekeeper_quiet_complete_interactions_view, name='gatekeeper_quiet_complete_interactions'),

    re_path('^hq/emails/$', emails.emails_queue, name='emails_queue'),
    re_path('^hq/emails/([^/]+)/$', emails.emails_queue, name='emails_queue'),
    re_path('^hq/emails/([^/]+)/([^/]+)/$', emails.emails_queue, name='emails_queue'),

    re_path('^hq/solve-graph/$', dashboard.solve_graph, name='solve_graph'),

    re_path('^login/?$', views.login, name='login'),
    re_path('^logout/?$', views.logout, name='logout'),

    re_path('^shortcuts$', shortcuts.shortcuts, name='shortcuts'),
    re_path('', include('hunt.urls')),

    re_path('^hq/cafe_admin/(.*)/$', views.cafe_admin, name='cafe_admin'),
    re_path('^_ah/warmup$', views.warmup),
]
