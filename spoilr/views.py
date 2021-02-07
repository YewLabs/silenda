from django.shortcuts import render
import spoilr.models as models
from django.db import transaction
from django import forms
#import spoilr.tasks as tasks
from django.http import HttpResponse, HttpResponseBadRequest
from django.template import RequestContext, loader
from django.shortcuts import redirect, render
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .models import Team, PuzzleAccess
from .decorators import require_prelaunch_team
from .signals import emit, hq_update_message
from .log import system_log, HQ_UPDATE

from hunt.actions import get_mmo_unlocked
from nuntius.email import send_team_mail

@staff_member_required
def updates_view(request):
    if request.method == "POST":
        updates_to_publish = models.HQUpdate.objects.filter(id__in=request.POST.getlist('update_ids'))
        for update in updates_to_publish:
            teams = []
            if update.team:
                teams = [update.team]
            elif update.puzzle:
                pa_teams = PuzzleAccess.objects.filter(puzzle=update.puzzle, found=True).select_related('team')
                teams = [pa.team for pa in pa_teams]
            else:
                teams = Team.objects.all()
            update.publish_time = models.now()
            update.published = True
            update.save()
            if update.send_email:
                send_team_mail('HQ Update: %s' % (update.subject), update.body, teams)
            system_log(HQ_UPDATE, 'HQ Update: %s' % update.subject)
            emit(hq_update_message, update, teams)
        return redirect(request.path)

    hqupdates = models.HQUpdate.objects.order_by('-creation_time')
    context = { 'updates': hqupdates }
    return render(request, 'hq/updates.html', context)

def login(request):
    if request.method == "POST":
        if 'public' in request.POST:
            t = Team.objects.get(username='public')
            request.session['team'] = t.username
            request.session.save()
            return redirect(request.POST.get('next', '/'))
        try:
            t = Team.objects.get(username=request.POST.get('team', None), password=request.POST.get('pass', None))
            request.session['team'] = t.username
            request.session.save()
            return redirect(request.POST.get('next', '/'))
        except Exception as e:
            return render(request, 'hunt/login.html', {'next': request.POST.get('next', '/'), 'error': 'Unknown Login'})
    return render(request, 'hunt/login.html', {'next': request.GET.get('next', '/'), 'error': None})

def logout(request):
    try:
        del request.session['team']
    except KeyError:
        pass
    return redirect(request.GET.get('next', '/'))

@require_prelaunch_team
@xframe_options_sameorigin
def update_team(request):
    team = request.team
    context = {
        'embedded': request.path.startswith('/embed/'),
        'team': team,
        'puzzle': None,
        'mmo_unlocked': get_mmo_unlocked(team),
        'status': None,
    }
    if request.method == "POST":
        team.email = request.POST.get('email', team.email)
        team.phone = request.POST.get('phone', team.phone)
        team.save()
        context['status'] = 'Team information updated.'
    return render(request, 'hunt/update_team.html', context)

@staff_member_required
def impersonate(request, team_url):
    team = Team.objects.get(url=team_url)
    try:
        request.session['team'] = team.username
        request.session.save()
        return redirect(request.POST.get('next', '/'))
    except Exception as e:
        return redirect('/hq/')

@staff_member_required
def end_impersonate(request):
    try:
        del request.session['team']
        team = Team.objects.get(url='admin')
        request.session['team'] = team.username
        request.session.save()
        return redirect('/hq/')
    except Exception as e:
        return redirect('/hq/')

def warmup(request):
    return HttpResponse('ACK', content_type='text/plain')

@staff_member_required
@transaction.atomic
def cafe_admin(request, team_url):
    team = Team.objects.get(url=team_url)
    from hunt.special_puzzles.puzzle179 import Puzzle179TeamData
    from hunt.actions import get_infinite
    data = None
    status = ''
    try:
        data = Puzzle179TeamData.objects.select_for_update().get(team=team)
    except Puzzle179TeamData.DoesNotExist:
        status = 'This team does not have access to the Cafe'
    if not data:
        context = {
            'team': team,
            'completions': 0,
            'redemptions': 0,
            'available': False,
            'status': status,
            'available': False,
        }
        return render(request, 'cafe_admin.html', context)


    if request.method == "POST":
        if 'redeem' in request.POST:
            if data.redemptions < data.completions:
                data.redemptions += 1
                data.save()
                status = 'Token redeemed'
            else:
                status = 'Insufficient tokens'
        elif 'lookup' in request.POST:
            status = 'Unknown Cafe Five Puzzle'
            try:
                infinite_id = int(request.POST['infinite'])
                infPuzzle = get_infinite(42000000+infinite_id)
                if infPuzzle.y2021puzzledata.parent.y2021puzzledata.tempest_id == 179:
                    status = 'Infinite #%d Answer: %s' % (infinite_id, infPuzzle.answer)
            except:
                pass

    context = {
        'team': team,
        'completions': data.completions,
        'redemptions': data.redemptions,
        'available': data.redemptions < data.completions,
        'status': status,
        'available': True,
    }
    return render(request, 'cafe_admin.html', context)
