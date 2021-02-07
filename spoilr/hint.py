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

def hint_puzzle_post(request, team, puzzle):
    question = request.POST["question"]
    email = request.POST["email"]

    if len(question) == 0:
        return redirect(request.path)
    for sub in HintSubmission.objects.filter(team=team, puzzle=puzzle):
        if sub.question.strip() == question.strip():
            return redirect(request.path)

    system_log(HINT_PUZZLE, "%s asked '%s' about %s" % (team.name, question, str(puzzle)), team=team, object_id=puzzle.url)
    try:
        p = HintSubmission.objects.create(team=team, puzzle=puzzle, email=email, question=question)
        discord_queue('hint%04d' % (p.id), team, 'Hint request for "%s" by "%s": %s' % (p.puzzle.name, team.name, question), reverse('hint_queue', args=(p.puzzle.url, p.team.url)))
    except IntegrityError:
        logger.warning('integrity error adding puzzle question - this is probably because the team asked the same question twice with very little time in between - team:%s puzzle:%s question:%s', team, puzzle, question)
    return redirect(request.path)

@require_team
@xframe_options_sameorigin
def hint_puzzle(request, puzzle_url):
    team = request.team
    try:
        puzzle = Puzzle.objects.get(url=puzzle_url)
    except Puzzle.DoesNotExist:
        logger.exception('cannot find puzzle %s', puzzle_url)
        return HttpResponseBadRequest('cannot find puzzle '+puzzle_url)
    try:
        access = PuzzleAccess.objects.get(team=team, puzzle=puzzle)
    except PuzzleAccess.DoesNotExist:
        logger.exception(u'team %s submitted for puzzle %s, but does not have access to it - shenanigans?', team, puzzle)
        return HttpResponseBadRequest('cannot find puzzle '+puzzle_url)

    hint_available = False
    time_left = None
    hit_quota = False
    p21 = puzzle.y2021puzzledata
    if p21.hint_stuck_duration is None:
        if p21.infinite and p21.parent.y2021puzzledata.hint_stuck_duration is not None:
            p21.hint_stuck_duration = p21.parent.y2021puzzledata.hint_stuck_duration
            p21.save()
    if access.found_timestamp and p21.hint_stuck_duration is not None:
        time_left = access.found_timestamp + p21.hint_stuck_duration - now()
        if time_left.total_seconds() <= 0:
            time_left = None
            hint_available = True
    if HintSubmission.objects.filter(team=team, resolved=False).exists():
        hint_available = False
        hit_quota = True
    if request.method == 'POST':
        if not hint_available:
            return HttpResponseBadRequest('No more questions available.')
        return hint_puzzle_post(request, team, puzzle)

    hints = HintSubmission.objects.filter(team=team, puzzle=puzzle)
    context = {
        'embedded': request.path[:7] == '/embed/',
        'team': team,
        'mmo_unlocked': get_mmo_unlocked(team),
        'puzzle': puzzle,
        'solved': access.solved,
        'hints': hints,
        'hint_available': hint_available,
        'time_left': time_left,
        'hit_quota': hit_quota,
    }
    return render(request, 'hint/puzzle.html', context)

@staff_member_required
def hint_queue_claim(request):
    submission_id = request.POST["id"]
    handler_email = request.POST["claimant"]
    claim_time = request.POST["lastclaim"]
    submission = HintSubmission.objects.get(id=submission_id)
    if claim_time != submission.claim_time.isoformat():
        return HttpResponseBadRequest('Yoinked by %s at %s' % (submission.claimant, str(submission.claim_time),), request.POST)
    submission.claimant = handler_email
    submission.claim_time = now()
    submission.save()
    return redirect(request.path)

@staff_member_required
def hint_queue_unclaim(request):
    submission_id = request.POST["id"]
    submission = HintSubmission.objects.get(id=submission_id)
    submission.claimant = None
    submission.save()
    return redirect(request.path)

@staff_member_required
def hint_queue_post(request):
    if request.POST.get('Claim'):
        return hint_queue_claim(request)
    if request.POST.get('Unclaim'):
        return hint_queue_unclaim(request)
    if request.POST.get('offduty'):
        handler_email = request.session.get('handler_email')
        handler = None
        if handler_email:
            handler = QueueHandler.objects.get(email=handler_email)
            handler.hq_phone = None
        del request.session['handler_email']
        return redirect(request.path)

    response = request.POST["response"]
    submission_id = request.POST["id"]
    claim_time = request.POST.get("lastclaim")
    submission = HintSubmission.objects.get(id=submission_id)
    if submission.resolved:
        return HttpResponseBadRequest(u'ERROR: this submission has already been resolved as %s' % (submission,))
    if claim_time != submission.claim_time.isoformat():
        return HttpResponseBadRequest('Yoinked by %s at %s' % (submission.claimant, str(submission.claim_time),), request.POST)
    logger.info("Submitting %s to %s" % (response, submission))
    submission.result = response
    submission.resolved = True
    handler_email = request.session.get('handler_email')
    submission.claimant = handler_email
    submission.save()
    discord_queue('hint%04d' % (submission.id), submission.team, '')
    if submission.email:
        send_mail("Hint Response for '%s'" % (submission.puzzle.name), submission.result, submission.email)
    return redirect(request.path)

@staff_member_required
def hint_queue(request, puzzle_url=None, team_url=None):
    if request.method == 'POST':
        return hint_queue_post(request)
    handler = None
    handler_email = request.session.get('handler_email')
    if handler_email:
        handler = QueueHandler.objects.get(email=handler_email)
    questions = HintSubmission.objects.select_related('puzzle', 'team')
    limit = None
    puzzle = None
    if puzzle_url:
        if puzzle_url.lower() == 'all':
            pass
        elif puzzle_url.isdigit():
            limit = int(puzzle_url)
            puzzle_url = None
        else:
            puzzle = get_object_or_404(Puzzle, url=puzzle_url)
            questions = questions.filter(puzzle=puzzle)

    team = None
    if team_url:
        team = get_object_or_404(Team, url=team_url)
        questions = questions.filter(team=team)

    if not puzzle_url and not team_url:
        questions = questions.filter(resolved=False)

    questions = questions.order_by('resolved', '-timestamp')
    if limit:
        questions = questions[:limit]

    context = {
        'questions': questions,
        'puzzle': puzzle,
        'team': team,
        'handler': handler,
    }
    return render(request, 'hint/queue.html', context)
