from django.core.cache import cache
from django.http import HttpResponse, HttpResponseBadRequest
from django.template import loader
from django.shortcuts import redirect, render
from django.db import IntegrityError
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required


import re
import datetime
from collections import defaultdict

from .models import *
from .actions import *
from .log import *
from .decorators import *

from hunt.views import CACHE_TIME
from hunt.actions import get_mmo_unlocked

from hunt.interactions import submission_instructions

import logging
logger = logging.getLogger(__name__)

PUZZLE_FREEBIES = 2
PUZZLE_LIMIT = 3 # Number of incorrect answers.
PUZZLE_TIMELIMIT = 5 * 60

PUZZLE_QUEUE_LIMIT = 2
QUEUE_LIMIT = 10
CONTACT_LIMIT = 5

def cleanup_answer(answer):
    return re.sub(r'[^ A-Z0-9]', '', answer.upper())

def cleanup_answer_better(answer):
    return re.sub(r'[^A-Z0-9]', '', answer.upper())

def compare_answers(a, b):
    return re.sub(r'[^A-Z0-9]', '', a.upper()) == re.sub(r'[^A-Z0-9]', '', b.upper())

def count_queue(team, queue_type):
    q = None
    if queue_type == "answer":
        q = PuzzleSubmission.objects.filter(team=team, resolved=False).count()
    elif queue_type == "contact":
        q = ContactRequest.objects.filter(team=team, resolved=False).count()
    return q

def claim_team_submission(handler, team, sub_type):
    if sub_type == "answer":
        handler.team = team
        handler.team_timestamp = now()
    elif sub_type == "contact":
        handler.contact_team = team
        handler.contact_team_timestamp = now()

def handler_timed_out(handler, queue_type):
    if queue_type == "answer":
        handler.team = None
        handler.team_timestamp = None
    elif queue_type == "contact":
        handler.contact_team = None
        handler.contact_team_timestamp = None


def release_team_submission(handler, team, sub_type):
    if sub_type == "answer":
        handler.team = None
        handler.team_timestamp = None
    elif sub_type == "contact":
        handler.contact_team = None
        handler.contact_team_timestamp = None

def submission_team(handler, queue_type):
    if queue_type == "answer":
        return handler.team
    elif queue_type == "contact":
        return handler.contact_team

def submission_team_timestamp(handler, queue_type):
    if queue_type == "answer":
        return handler.team_timestamp
    elif queue_type == "contact":
        return handler.contact_team_timestamp

def submit_puzzle_answer(team, puzzle, answer):
    if len(answer) == 0:
        return False
    for sub in PuzzleSubmission.objects.filter(team=team, puzzle=puzzle):
        if compare_answers(sub.answer, answer):
            return compare_answers(answer, puzzle.answer)
    if PuzzleAccess.objects.filter(team=team, puzzle=puzzle, solved=True).exists():
        return False
    system_log(SUBMIT_PUZZLE, u"%s submitted '%s' for %s" % (team.name, answer, str(puzzle)), team=team, object_id=puzzle.url)
    try:
        p = PuzzleSubmission(team=team, puzzle=puzzle, answer=answer)
        p.resolved = True
        system_log(QUEUE_RESOLUTION, u"'Resolved answer '%s' for puzzle '%s' for team '%s'" % (p.answer, str(p.puzzle), team.name), team=team)
        if compare_answers(p.answer, p.puzzle.answer):
            puzzle_answer_correct(team, p.puzzle)
            p.correct = True
        else:
            puzzle_answer_incorrect(team, p.puzzle, p.answer)
            p.correct = False
        p.save()
    except IntegrityError:
        logger.warning(u'integrity error adding puzzle submission - this is probably because the team submitted the same answer twice with very little time in between - team:%s puzzle:%s answer:%s', team, puzzle, answer)
    return compare_answers(answer, puzzle.answer)

@require_puzzle_access
@xframe_options_sameorigin
def submit_puzzle(request):
    team = request.team
    puzzle = request.puzzle
    KEY = 'team%03d:submit-puzzle-%d' % (team.id, puzzle.id)
    context = cache.get(KEY)

    if not context:
        ignoreLimit = False
        answers = list(PuzzleSubmission.objects.filter(team=team, puzzle=puzzle).order_by('-timestamp'))
        try:
            extra_attempts = PuzzleExtraData.objects.get(puzzle=puzzle, name='extra_attempts').data
            ignoreLimit = True
        except PuzzleExtraData.DoesNotExist:
            extra_attempts = None
        context = {
            'team': team,
            'puzzle': puzzle,
            'solved': request.puzzle_access.solved,
            'answers': answers,
            'mmo_unlocked': get_mmo_unlocked(team),
            'time_left': None,
            'response': None,
            'extra_attempts': extra_attempts,
            'ignore_limit': ignoreLimit,
        }
        cache.set(KEY, context, CACHE_TIME)
    context['embedded'] = request.path.startswith('/embed/')
    if not context['ignore_limit'] and not request.puzzle_access.solved and len(context['answers']) >= PUZZLE_FREEBIES:
        cutoffTime = now() - datetime.timedelta(seconds=PUZZLE_TIMELIMIT)
        roundAnswers = PuzzleSubmission.objects.filter(team=team, puzzle__round=puzzle.round, correct=False).select_related('puzzle').order_by('timestamp')
        ignoredCount = defaultdict(int)
        badOnes = []
        for ra in roundAnswers:
            ignoredCount[ra.puzzle.id] += 1
            if ra.timestamp > cutoffTime and ignoredCount[ra.puzzle.id] > PUZZLE_FREEBIES:
                badOnes.append(ra)
        if len(badOnes) >= PUZZLE_LIMIT:
            context['time_left'] = badOnes[-PUZZLE_LIMIT].timestamp - cutoffTime

    if request.method == 'POST':
        maxlen = Puzzle._meta.get_field('answer').max_length
        answer = cleanup_answer(request.POST['answer'])[:maxlen]
        if team.is_admin and compare_answers(answer, 'ANSWER'):
            answer = puzzle.answer
        pseudoanswers = PseudoAnswer.objects.filter(puzzle=puzzle)
        for pa in pseudoanswers:
            if compare_answers(answer, pa.answer):
                context['response'] = pa.response
                if '{{ submission_instructions }}' in context['response'] and puzzle.interaction.exists():
                    context['response'] = context['response'].replace('{{ submission_instructions }}', submission_instructions(puzzle.interaction.first(), team)).replace('{{ submission_email }}', submission_instructions(puzzle.interaction.first(), team, False))
        if team.is_limited:
            if not context['response']:
                if compare_answers(answer, puzzle.answer):
                    context['response'] = '%s is correct.' % (puzzle.answer)
                    try:
                        dest = PuzzleExtraData.objects.get(puzzle=puzzle, name='solve_redirect').data
                        context['response'] += ' <a href="%s?solved=1" target="_top">Post Solve Content</a>' % (dest)
                    except PuzzleExtraData.DoesNotExist:
                        pass
                else:
                    context['response'] = '%s is incorrect.' % (answer)
        elif context['response']:
            system_log(SUBMIT_PUZZLE, u"%s submitted '%s' for %s" % (team.name, answer, str(puzzle)), team=team, object_id=puzzle.url)
        elif not context['time_left']:
            correctAnswer = submit_puzzle_answer(team, puzzle, answer)
            cache.delete(KEY)
            if correctAnswer:
                try:
                    dest = PuzzleExtraData.objects.get(puzzle=puzzle, name='solve_redirect').data
                    if context['embedded']:
                        return render(request, 'submit/redirect.html', {'redirect': dest})
                    else:
                        return redirect(dest)
                except PuzzleExtraData.DoesNotExist:
                    pass
                #if context['embedded']:
                #    return render(request, 'submit/redirect.html', {'redirect': reverse('puzzle_view', args=(puzzle.url,))})
            return redirect(request.path)

    return render(request, 'submit/puzzle.html', context)

@require_team
@xframe_options_sameorigin
def submit_survey(request, puzzle_url):
    team = request.team
    try:
        puzzle = Puzzle.objects.get(url=puzzle_url)
    except Puzzle.DoesNotExist:
        logger.exception('cannot find puzzle %s', puzzle_url)
        return HttpResponseBadRequest('cannot find puzzle '+puzzle_url)
    #try:
    #    access = PuzzleAccess.objects.get(team=team, puzzle=puzzle)
    #except PuzzleAccess.DoesNotExist:
    #    logger.exception('team %s submitted for puzzle %s, but does not have access to it - shenanigans?', team, puzzle)
    #    return HttpResponseBadRequest('cannot find puzzle '+puzzle_url)
    #if not access.solved:
    #    logger.exception('team %s requesting survey for puzzle %s, but has not solved it - shenanigans?', team, puzzle)
    #    return HttpResponseBadRequest('cannot request survey until the puzzle is solved')

    commentlen = PuzzleSurvey._meta.get_field('comment').max_length
    complete = False
    if request.method == 'POST':
        comment = request.POST['comment'][:commentlen]
        fun = request.POST['fun']
        if fun not in ('1','2','3','4','5'):
            fun = None
        difficulty = request.POST['difficulty']
        if difficulty not in ('1','2','3','4','5'):
            difficulty = None
        PuzzleSurvey.objects.create(team=team, puzzle=puzzle, fun=fun, difficulty=difficulty, comment=comment)
        complete = True

    count = PuzzleSurvey.objects.filter(team=team, puzzle=puzzle).count()
    context = {
        'embedded': request.path.startswith('/embed/'),
        'team': team,
        'puzzle': puzzle,
        'mmo_unlocked': get_mmo_unlocked(team),
        'count': count,
        'commentlen': commentlen,
        'complete': complete,
    }
    return render(request, 'submit/survey.html', context)

def submit_contact_actual(team, contact, comment):
    system_log(SUBMIT_CONTACT, "%s wants to talk to HQ: '%s'" % (team.name, comment), team=team)
    cr = ContactRequest.objects.create(team=team, contact=contact, comment=comment)
    discord_queue('cr%04d' % (cr.id), team, 'Contact HQ Request: "%s"' % (comment), reverse('hq_queue', args=('contact',)))

@require_prelaunch_team
@xframe_options_sameorigin
def submit_contact(request):
    team = request.team
    # these don't count toward the QUEUE_LIMIT
    q_full2 = ContactRequest.objects.filter(team=team, resolved=False).count() >= CONTACT_LIMIT
    if not q_full2 and request.method == 'POST':
        maxlen = ContactRequest._meta.get_field('comment').max_length
        comment = request.POST['comment'][:maxlen]
        contact = request.POST['contact']
        submit_contact_actual(team, contact, comment)
        return redirect(request.path)
    requests = ContactRequest.objects.filter(team=team, resolved=False)
    context = {
        'embedded': request.path.startswith('/embed/'),
        'team': team,
        'puzzle': None,
        'mmo_unlocked': get_mmo_unlocked(team),
        'requests': requests,
        'q_full2': q_full2,
        'q_lim2': CONTACT_LIMIT,
    }
    return render(request, 'submit/contact.html', context)

@staff_member_required
def queue(request, queue_type="contact"):
    for h in QueueHandler.objects.all():
        a_team = submission_team(h, queue_type)
        if a_team:
            delta = now() - submission_team_timestamp(h, queue_type)
            if delta.seconds > 60*10:
                team = a_team
                handler_timed_out(h, queue_type)
                h.save()
                logger.warning(u"handler '%s' (%s) timed out while handling '%s'", h.name, h.email, team.name)
                system_log(QUEUE_TIMEOUT, u"'%s' (%s) had been handling '%s' for %s seconds, but timed out" % (h.name, h.email, team.name, delta.seconds), team=team)

    handler_email = request.session.get('handler_email')
    handler = None
    if handler_email:
        handler = QueueHandler.objects.get(email=handler_email)
    if request.method == 'POST':
        if "offduty" in request.POST:
            handler.hq_phone = None
            del request.session['handler_email']
        elif "claim" in request.POST:
            team = Team.objects.get(url=request.POST['claim'])
            if count_queue(team, queue_type) == 0:
                template = 'queue/yoinked.html'
                return render(request, template, {})
            claim_team_submission(handler, team, queue_type)
            try:
                handler.save()
            except IntegrityError:
                template = 'queue/yoinked.html'
                return render(request, template, {})
            system_log(QUEUE_CLAIM, u"'%s' (%s) claimed '%s'" % (handler.name, handler.email, team.name), team=team)
        elif handler and submission_team(handler, queue_type) and "handled" in request.POST:
            handled_team = submission_team(handler,queue_type)
            for key in request.POST:
                if key[:2] == 'p_' and handler.team:
                    p = PuzzleSubmission.objects.get(team=handler.team, resolved=False, id=key[2:])
                    p.resolved = True
                    system_log(QUEUE_RESOLUTION, u"'%s' (%s) resolved answer '%s' for puzzle '%s' for team '%s'" % (handler.name, handler.email, p.answer, str(p.puzzle), handler.team.name), team=handler.team)
                    if compare_answers(p.answer, p.puzzle.answer):
                        puzzle_answer_correct(handler.team, p.puzzle)
                        p.correct = True
                    else:
                        puzzle_answer_incorrect(handler.team, p.puzzle, p.answer)
                        p.correct = False
                    p.save()
                if key[:2] == 'c_' and handler.contact_team:
                    p = ContactRequest.objects.get(team=handler.contact_team, resolved=False, id=key[2:])
                    p.resolved = True
                    system_log(QUEUE_RESOLUTION, u"'%s' (%s) resolved hq-contact '%s' for team '%s'" % (handler.name, handler.email, p.comment, handler.contact_team.name), team=handler.contact_team)
                    discord_queue('cr%04d' % (p.id), p.team, '')
                    p.save()
            if handled_team:
                system_log(QUEUE_CLAIM, u"'%s' (%s) released claim on team '%s'" % (handler.name, handler.email, handled_team.name), team=handled_team)
                release_team_submission(handler, handled_team, queue_type)
                handler.save()
        elif handler and "handled" in request.POST:
            template = 'queue/timedout.html'
            return render(request, template, {})
        elif not handler and "email" in request.POST:
            handler_email = request.POST["email"]
            handler_phone = request.POST["phone"]
            next_loc = request.POST["next"]
            if QueueHandler.objects.filter(email=handler_email).exists():
                QueueHandler.objects.filter(email=handler_email).update(hq_phone=handler_phone)
            elif "name" in request.POST:
                handler_name = request.POST["name"]
                QueueHandler.objects.create(email=handler_email,name=handler_name, hq_phone=handler_phone)
            else:
                template = 'queue/signup.html'
                context = {
                    'email': handler_email,
                    'phone': handler_phone,
                    'next': next_loc,
                }
                return render(request, template, context)
            request.session['handler_email'] = handler_email
            return redirect(next_loc)
        return redirect(request.path)

    handling_team = None
    if handler:
        handling_team = submission_team(handler, queue_type)

    if handler and handling_team:
        contacts_other = []
        contacts = set()
        def add_contact(p):
            contacts.add(p)
            try:
                contacts_other.remove(p)
            except ValueError:
                pass

        puzzle = []
        if queue_type == "answer":
            team = handler.team
            team_timestamp = handler.team_timestamp
            contacts_other = [team.phone, team.email]
            for p in PuzzleSubmission.objects.filter(team=team, resolved=False):
                puzzle.append({'submission': p, 'correct': compare_answers(p.answer, p.puzzle.answer)})
            puzzle.sort(key=lambda p: p['correct'])
            puzzle.sort(key=lambda p: p['submission'].puzzle.url)
        contact = []
        if queue_type == "contact":
            team = handler.contact_team
            team_timestamp = handler.contact_team_timestamp
            contacts_other = [team.phone, team.email]
            for p in ContactRequest.objects.filter(team=team, resolved=False):
                contact.append({'submission': p})
                add_contact(p.contact)

        template = 'queue/handling.html'
        context = {
            'timer': (60*10 - (now() - team_timestamp).seconds - 3),
            'handler': handler,
            'contacts_other': contacts_other,
            'contacts_now': contacts,
            'puzzle': puzzle,
            'contact': contact,
            'team': team,
        }

        return render(request, template, context)

    t_total = Team.objects.filter(is_special=False).count()
    q_teams = set()
    if queue_type == "answer":
        q_total = PuzzleSubmission.objects.filter(resolved=False).count()
        for x in PuzzleSubmission.objects.filter(resolved=False):
            q_teams.add(x.team.url)
    if queue_type == "contact":
        q_total = ContactRequest.objects.filter(resolved=False).count()
        for x in ContactRequest.objects.filter(resolved=False):
            q_teams.add(x.team.url)

    teams_dict = dict()
    teams = []

    def team_obj(team, timestamp):
        sec = (now() - timestamp).total_seconds()
        if not team.url in teams_dict:
            team_obj = {"team": team, "youngest": sec, "oldest": sec, "submissions": []}
            teams_dict[team.url] = team_obj
            teams.append(team_obj)
        else:
            team_obj = teams_dict[team.url]
            team_obj["youngest"] = min(sec, team_obj["youngest"])
            team_obj["oldest"] = max(sec, team_obj["oldest"])
        return team_obj

    if queue_type == "answer":
        for sub in PuzzleSubmission.objects.filter(resolved=False):
            team_obj(sub.team, sub.timestamp)["submissions"].append({"type": "puzzle", "thing": str(sub.puzzle), "timestamp": sub.timestamp, "info": '(Special)' if sub.puzzle.handler_info else ''})
        for team_obj in teams:
            team_obj["submissions"].sort(key=lambda sub: sub["timestamp"])
            handlers = list(QueueHandler.objects.filter(team=team_obj["team"]))
            if len(handlers) > 0:
                team_obj["handler"] = handlers[0]

    if queue_type == "contact":
        for sub in ContactRequest.objects.filter(resolved=False):
            team_obj(sub.team, sub.timestamp)["submissions"].append({"type": "contact", "thing": sub.comment, "timestamp": sub.timestamp})
        for team_obj in teams:
            team_obj["submissions"].sort(key=lambda sub: sub["timestamp"])
            handlers = list(QueueHandler.objects.filter(contact_team=team_obj["team"]))
            if len(handlers) > 0:
                team_obj["contact_handler"] = handlers[0]

    teams.sort(key=lambda team: -team["oldest"])

    template = 'queue/queue.html'
    context = {
        'tq_max': QUEUE_LIMIT,
        't_total': t_total,
        'q_total': q_total,
        'q_teams': len(q_teams),
        'handler': handler,
        'teams': teams,
        'queue_type': queue_type
    }

    if handler:
        handler.activity = now()
        handler.save()
    return render(request, template, context)
