from .log import *
from .models import *
#from .publish import *
from .signals import *
from django.db.models import Q
from django.conf import settings
from django.core.cache import cache
#import tasks
#from celery import using_celery

import logging
logger = logging.getLogger(__name__)

def release_round(team, round, reason=None, utime=None, team_log=True):
    if RoundAccess.objects.filter(team=team, round=round).exists():
        return
    logger.info("release %s/round/%s (%s)", team.url, round.url, reason)
    if not utime:
        utime = now()
    RoundAccess.objects.create(team=team, round=round, timestamp=utime)
    if team_log:
        team_log_round_access(team, round, reason, utime)

def release_all_puzzles_in_round(team, round, reason=None, utime=None):
    with block_team_top(team):
        release_round(team, round, reason)
        for puzzle in round.puzzle_set.all():
            release_puzzle(team, puzzle, reason, utime)

def release_all_puzzles_in_round_to_all_teams(round, reason=None, utime=None):
    for team in Team.objects.all():
        release_all_puzzles_in_round(team, round, reason, utime)


def release_puzzle(team, puzzle, reason=None, utime=None, team_log=True):
    if PuzzleAccess.objects.filter(team=team, puzzle=puzzle).exists():
        return
    logger.info("release %s/puzzle/%s (%s)", team.url, puzzle.url, reason)
    if not utime:
        utime = now()
    PuzzleAccess.objects.create(team=team, puzzle=puzzle, timestamp=utime)

def find_puzzle(team, puzzle, reason=None, utime=None, team_log=True):
    from hunt.actions import get_puzzle_access
    access = get_puzzle_access(team, puzzle)
    if not access:
        return False
    if access.found:
        return True
    logger.info("found %s/puzzle/%s (%s)", team.url, puzzle.url, reason)
    access.found = True
    if not utime:
        utime = now()
    access.found_timestamp = utime
    access.save()
    if team_log:
        team_log_puzzle_access(team, puzzle, reason, utime)
    emit(puzzle_found_message, team, puzzle)
    return True

def release_interaction(team, interaction, reason=None, utime=None):
    if InteractionAccess.objects.filter(team=team, interaction=interaction).exists():
        return
    logger.info("release %s/interaction/%s (%s)", team.url, interaction.url, reason)
    if not utime:
        utime = now()
    ia = InteractionAccess.objects.create(team=team, interaction=interaction, timestamp=utime)
    if interaction.show_team:
        team_log_interaction_access(team, interaction, reason, utime)
    if interaction.url != 'mmo-unlock':
        discord_queue('interaction%04d' % (ia.id), ia.team, 'Ready for interaction "%s"' % (interaction.name), reverse('interaction_queue', args=(ia.interaction.url,)))
    emit(interaction_released_message, team, interaction)

def puzzle_answer_correct(team, puzzle, team_log=True):
    try:
        pa = PuzzleAccess.objects.get(team=team, puzzle=puzzle)
    except PuzzleAccess.DoesNotExist:
        return
    if pa.solved:
        return
    logger.info("puzzle answer correct %s/puzzle/%s", team.url, puzzle.url)
    pa.solved = True
    pa.solved_time = now()
    if team_log:
        team_log_puzzle_solved(team, puzzle)
    pa.save()

def solve_puzzle(team, puzzle, reason=None, team_log=True):
    if not PuzzleAccess.objects.filter(team=team, puzzle=puzzle).exists():
        return False
    p = PuzzleSubmission(team=team, puzzle=puzzle, answer=puzzle.answer)
    p.resolved = True
    p.correct = True
    p.save()
    puzzle_answer_correct(team, puzzle, team_log)
    return True

def puzzle_answer_incorrect(team, puzzle, answer):
    if not PuzzleAccess.objects.filter(team=team, puzzle=puzzle).exists():
        return
    team_log_puzzle_incorrect(team, puzzle, answer)

def interaction_accomplished(team, interaction, utime=None):
    try:
        ia = InteractionAccess.objects.get(team=team, interaction=interaction)
    except InteractionAccess.DoesNotExist:
        return
    if ia.accomplished:
        return
    if not utime:
        utime = now()
    logger.info("interaction accomplished %s/interaction/%s", team.url, interaction.url)
    ia.accomplished = True
    ia.accomplished_time = utime
    if interaction.show_team:
        team_log_interaction_accomplished(team, interaction)
    ia.save()
    discord_queue('interaction%04d' % (ia.id), ia.team, '')
    emit(interaction_accomplished_message, team, interaction)

from django_redis import get_redis_connection

IN_SETUP = False

def set_in_setup():
    global IN_SETUP
    IN_SETUP = True

def set_done_setup():
    global IN_SETUP
    IN_SETUP = False

def clear_cache(team):
    global IN_SETUP
    if IN_SETUP:
        return
    try:
        rcache = get_redis_connection()
        keyPattern = ':1:team*'
        keys = None
        if team != None:
            keyPattern = ':1:team%03d:*' % (team.id)
            keys = rcache.keys(keyPattern)
        else:
            keys = rcache.scan_iter(keyPattern)
        for k in keys:
            rcache.delete(k)
    except:
        cache.clear()

def clear_redis():
    try:
        rcache = get_redis_connection()
        rcache.flushdb()
    except:
        cache.clear()
