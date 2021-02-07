from django.urls import path, re_path, include
from django.conf import settings

import nuntius.views as views

urlpatterns = [
    re_path('^api/incoming_email/$', views.incoming_email_view, name='incoming_email_view'),
]
