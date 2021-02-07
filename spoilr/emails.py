from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext, loader
from django.shortcuts import redirect, render, get_object_or_404
from django.db import IntegrityError
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.contrib.admin.views.decorators import staff_member_required

import re
import datetime

from .models import *
from .log import *
from .decorators import *
#from .tasks import *

from hunt.actions import get_mmo_unlocked

from nuntius.email import send_mail

import logging
logger = logging.getLogger(__name__)

@staff_member_required
def send_email(request, team=None, interaction=None):
    recipient = request.POST.get('recipient', '')
    if not recipient:
        return 'Missing recipient'
    sender = request.POST.get('sender', '')
    if not sender:
        return 'Missing sender'
    subject = request.POST.get('subject', '')
    if not subject:
        return 'Missing subject'
    body = request.POST.get('body', '')
    if not body:
        return 'Missing body'


    result = send_mail(subject, body, [recipient], (sender, sender))
    if result.status_code != 200:
        return 'Error sending (%d): %s' % (result.status_code, result.text)
    OutgoingMessage.objects.create(subject=subject, body=body, sender=sender, recipient=recipient)
    return 'Email successfully sent.'

@staff_member_required
def emails_queue(request, team_url=None, interaction_url=None):
    result = None
    if request.method == 'POST':
        if request.POST.get('hide', ''):
            try:
                id = int(request.POST.get('id', ''))
                im = IncomingMessage.objects.get(id=id)
                im.hidden = True
                im.save()
            except:
                result = 'Error hiding email'
        elif request.POST.get('email'):
            result = send_email(request)

    emails = IncomingMessage.objects.select_related('team', 'interaction').filter(hidden=False)
    limit = None
    interaction = None
    if interaction_url and interaction_url != 'all':
        interaction = get_object_or_404(Interaction, url=interaction_url)
        emails = emails.filter(interaction=interaction)

    team = None
    if team_url and team_url != 'all':
        team = get_object_or_404(Team, url=team_url)
        emails = emails.filter(team=team)

    emails = emails.order_by('-received_time')

    context = {
        'interaction': interaction,
        'team': team,
        'emails': emails,
        'result': result
    }
    return render(request, 'email_queue.html', context)
