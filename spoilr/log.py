import hashlib
import time

from django.contrib.admin.views.decorators import staff_member_required

import requests
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

from .models import *

import logging
logger = logging.getLogger(__name__)


ROUND_ACCESS = 'round-access'
PUZZLE_ACCESS = 'puzzle-access'
PUZZLE_SOLVED = 'puzzle-solved'
PUZZLE_INCORRECT = 'puzzle-incorrect'
METAPUZZLE_ACCESS = 'metapuzzle-access'
METAPUZZLE_SOLVED = 'metapuzzle-solved'
METAPUZZLE_INCORRECT = 'metapuzzle-incorrect'
INTERACTION = 'interaction'
ADMIN_INTERACTION = 'admin-interaction'
HINT_PUZZLE = 'hint-puzzle'
SUBMIT_PUZZLE = 'submit-puzzle'
SUBMIT_CONTACT = 'submit-contact'
QUEUE_CLAIM = 'queue-claim'
QUEUE_TIMEOUT = 'queue-timeout'
QUEUE_RESOLUTION = 'queue-resolution'
HQ_UPDATE = 'hq-update'

HUNT_QUEUE = 'queue'

def discord_basic_log(event_type, data):
    webhook = settings.DISCORD_WEBHOOKS.get(event_type, settings.DISCORD_WEBHOOK_DEFAULT)
    if webhook:
        requests.post(webhook, json=dict(data, username='%s-bot' % event_type))

def discord_log(event_type, team, message):
    if not team:
        discord_basic_log(event_type, {'content': message})
        return
    emoji = team.y2021teamdata.emoji
    if team.username.startswith('test'):
        emoji = "https://perpendicular.institute/static/team_emoji/test.png"
    discord_basic_log(event_type, {'embeds': [{
        'description': message,
        'color': int(hashlib.sha1(event_type.encode('utf8')).hexdigest(), 16) % 0xffffff,
        'author': {
            'name': team.name,
            'url': # can't get actual domain without the request object
                'https://perpendicular.institute' +
                reverse('one_team', args=(team.url,)),
            'icon_url': emoji,
        },
    }]})

def discord_queue(qid, team, message, link=None):
    DOMAIN = 'https://perpendicular.institute'
    emoji = team.y2021teamdata.emoji
    webhook = settings.DISCORD_WEBHOOKS[HUNT_QUEUE]
    if message and link:
        message = '[%s](%s)' % (message, DOMAIN + link)
    data = {
        'embeds': [{
            'description': message,
            'color': int(hashlib.sha1(qid.encode('utf8')).hexdigest(), 16) % 0xffffff,
            'author': {
                'name': team.name,
                'url': DOMAIN + reverse('one_team', args=(team.url,)),
                'icon_url': emoji,
            }
        }],
        'username': qid
    }
    if not message:
        data = {'content': 'DELETE', 'username': qid}
    requests.post(webhook, json=data)



def system_log(event_type, message, team=None, object_id=''):
    logger.debug('Hunt System Log: type=%s message="%s" team=%s object=%s', event_type, message, team, object_id)
    SystemLog.objects.create(event_type=event_type, message=message, team=team, object_id=object_id)
    discord_basic_log(event_type, {'content': ('**%s**: %s' % (team, message) if team else message)})

def team_log(team, event_type, message, object_id='', link='', time=None):
    if not time:
        time = now()
    SystemLog.objects.create(event_type=event_type, message='Team Log (%s): %s' % (time, message), team=team, object_id=object_id)
    if team:
        TeamLog.objects.create(event_type=event_type, message=message, team=team, object_id=object_id, link=link, timestamp=time)
        emit(team_log_message, team, event_type, message, object_id, link, time)
    discord_log(event_type, team, message)


def team_log_round_access(team, round, reason, time):
    rs = ''
    if reason:
        rs = ' (%s)' % (reason)
    team_log(team, ROUND_ACCESS, 'Released round "%s"%s' % (round.name, rs), object_id=round.url, link="/round/%s/" % round.url, time=time)

def team_log_puzzle_access(team, puzzle, reason, time):
    rs = ''
    if reason:
        rs = ' (%s)' % (reason)
    log_type = METAPUZZLE_ACCESS if puzzle.is_meta else PUZZLE_ACCESS
    team_log(team, log_type, u'Found %s%s' % (puzzle, rs), object_id=puzzle.url, link="/puzzle/%s/" % puzzle.url, time=time)

def team_log_interaction_access(team, interaction, reason, time):
    rs = ''
    if reason:
        rs = ' (%s)' % (reason)
    team_log(team, INTERACTION, 'Ready for interaction "%s"%s' % (interaction.name, rs), object_id=interaction.url, time=time)

def team_log_puzzle_solved(team, puzzle):
    log_type = METAPUZZLE_SOLVED if puzzle.is_meta else PUZZLE_SOLVED
    team_log(team, log_type, u'Solved %s' % (puzzle,), object_id=puzzle.url, link="/puzzle/%s/" % puzzle.url)

def team_log_puzzle_incorrect(team, puzzle, answer):
    log_type = METAPUZZLE_INCORRECT if puzzle.is_meta else PUZZLE_INCORRECT
    system_log(log_type, u'Incorrect answer `%s` for %s' % (answer, puzzle), team=team, object_id=puzzle.url)

def team_log_interaction_accomplished(team, interaction):
    team_log(team, INTERACTION, 'Completed interaction "%s"' % interaction.name, object_id=interaction.url)

@staff_member_required
def system_log_view(request, limit):
    entries = SystemLog.objects.select_related('team').order_by('-id')
    if limit: entries = entries[:int(limit)]
    return HttpResponse(render(request, 'hq/log.html', {
        'limit': limit,
        'entries': entries,
    }))

@staff_member_required
def survey_log_view(request, limit):
    entries = PuzzleSurvey.objects.select_related('team', 'puzzle').order_by('-id')
    if limit: entries = entries[:int(limit)]
    return HttpResponse(render(request, 'hq/survey-log.html', {
        'limit': limit,
        'entries': entries,
    }))

@staff_member_required
def hint_log_view(request, limit):
    entries = HintSubmission.objects.select_related('team', 'puzzle').order_by('-id')
    if limit: entries = entries[:int(limit)]
    return HttpResponse(render(request, 'hq/hint-log.html', {
        'limit': limit,
        'entries': entries,
    }))
