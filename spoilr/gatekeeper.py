from django.http import HttpResponse, HttpResponseBadRequest, StreamingHttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Count

from .models import *
from .actions import *
from .log import *

import datetime

from spoilr.models import Team
import spoilr.signals as signals
from hunt.models import Y2021Settings
from hunt.mmo_unlock import reset_global_state
from hunt.actions import start_all, unlock_mmo, disable_mmo, force_unlock, launch_hunt

import logging
logger = logging.getLogger(__name__)

@staff_member_required
def interactions_queue(request):
    interactions = []
    any_pending = False
    all_pending = InteractionAccess.objects.filter(accomplished=False).filter(Q(snooze_time__isnull=True) | Q(snooze_time__lte=now()))
    for interaction in Interaction.objects.all():
        pending = [i for i in all_pending if i.interaction_id == interaction.id]
        if interaction.url != 'mmo-unlock' and len(pending) > 0:
            any_pending = True
        interactions.append({
            'interaction': interaction,
            'pending': pending,
        })
    context = {
        'interactions': interactions,
        'pending': any_pending,
    }
    return render(request, 'gatekeeper/interactions.html', context)

@staff_member_required
def gatekeeper_interaction_view(request, interaction_url):
    interaction = Interaction.objects.get(url=interaction_url)
    if 'go' in request.POST:
        ias = list(interaction.interactionaccess_set.filter(team__url__in=[
            key[2:] for key in request.POST if key[:2] == 't_']))
        system_log(ADMIN_INTERACTION, 'Registering %d teams as having completed "%s"' % (len(ias), interaction.name))
        if 'accomplish' in request.POST:
            for ia in ias:
                interaction_accomplished(ia.team, ia.interaction)
        else:
            snooze = 0
            if 'snooze30' in request.POST:
                snooze = 0.5
            if 'snooze1' in request.POST:
                snooze = 1
            if 'snooze4' in request.POST:
                snooze = 4
            if 'snooze6' in request.POST:
                snooze = 6
            if 'snooze12' in request.POST:
                snooze = 12
            if 'snooze23' in request.POST:
                snooze = 23
            if snooze:
                snooze_time = now() + datetime.timedelta(hours=snooze)
                for ia in ias:
                    ia.last_snooze_time = now()
                    ia.snooze_time = snooze_time
                    ia.snooze_ack = False
                    ia.save()
                    discord_queue('interaction%04d' % (ia.id), ia.team, '')
        context = {
            'interaction': interaction,
            'done': True,
            'ias': ias,
        }
    else:
        teams_ready = []
        teams_accomplished = []
        teams_snoozed = []
        teams_not_ready = list(Team.objects.all())
        ias = interaction.interactionaccess_set.select_related('team', 'team__y2021teamdata')
        all_solves = {}
        for (team_id, is_meta, count) in (PuzzleAccess.objects
            .filter(solved=True, team_id__in=[ia.team_id for ia in ias])
            .values_list('team_id', 'puzzle__is_meta')
            .annotate(count=Count('*'))
            .order_by()):
            all_solves[team_id, is_meta] = count
        for ia in ias:
            teams_not_ready.remove(ia.team)
            if ia.accomplished:
                teams_accomplished.append(ia.team)
            else:
                if ia.snooze_time and ia.snooze_time > now():
                    teams_snoozed.append({'team': ia.team, 'time': ia.snooze_time, 'last_time': ia.last_snooze_time})
                else:
                    metaSolves = all_solves.get((ia.team_id, True), 0)
                    puzzleSolves = all_solves.get((ia.team_id, False), 0)
                    teams_ready.append({'team': ia.team, 'last_time': ia.last_snooze_time, 'metas_solved': metaSolves, 'puzzles_solved': puzzleSolves})
        if interaction.unlock_type == 'TIME':
            def snoozeAndPuzzleSort(val):
                num = 1000 * val['metas_solved'] + val['puzzles_solved']
                if val['last_time']:
                    num += (1696444120 - val['last_time'].timestamp()) * 10000
                return num
            teams_ready.sort(key=snoozeAndPuzzleSort, reverse=True)

        context = {
            'interaction': interaction,
            'done': False,
            'teams_not_ready': teams_not_ready,
            'teams_snoozed': teams_snoozed,
            'teams_ready': teams_ready,
            'teams_accomplished': teams_accomplished,
        }
    return render(request, 'gatekeeper/interaction.html', context)

COUNT = 50

@staff_member_required
def gatekeeper_view(request):
    interactions = []
    total = Team.objects.count()
    counts = {
        (interaction_id, accomplished): count for (interaction_id, accomplished, count) in
        InteractionAccess.objects.values_list('interaction_id', 'accomplished').annotate(count=Count('*'))}
    for interaction in Interaction.objects.all():
        done = counts.get((interaction.id, True), 0)
        queued = counts.get((interaction.id, False), 0)
        interactions.append({
            'interaction': interaction,
            'done': done,
            'queued': queued,
            'rest': total - done - queued,
        })
    context = {
        'interactions': interactions,
        'total': total,
    }
    return render(request, 'gatekeeper/start.html', context)

@staff_member_required
def gatekeeper_release_interactions_view(request):
    if 'release' not in request.GET:
        return HttpResponseBadRequest()
    interaction = Interaction.objects.get(url=request.GET['interaction'])
    teams = Team.objects.all()
    total = teams.count()
    utime = now()
    for t in teams:
        release_interaction(t, interaction, reason=None, utime=utime)
    return render(request, 'gatekeeper/result.html', {'result': 'Released "%s" for %d teams' % (interaction.name, total)})

@staff_member_required
def gatekeeper_complete_interactions_view(request):
    if 'complete' not in request.GET:
        return HttpResponseBadRequest()
    interaction = Interaction.objects.get(url=request.GET['interaction'])
    teams = Team.objects.all()
    total = teams.count()
    utime = now()
    for t in teams:
        release_interaction(t, interaction, reason=None, utime=utime)
        interaction_accomplished(t, interaction, utime=utime)
    return render(request, 'gatekeeper/result.html', {'result': 'Completed "%s" for %d teams' % (interaction.name, total)})

@staff_member_required
def gatekeeper_quiet_complete_interactions_view(request):
    if 'complete' not in request.GET:
        return HttpResponseBadRequest()
    interaction = Interaction.objects.get(url=request.GET['interaction'])
    teams = Team.objects.all()
    total = teams.count()
    utime = now()
    for t in teams:
        if not InteractionAccess.objects.filter(interaction=interaction, team=t).exists():
            InteractionAccess.objects.create(team=team, interaction=interaction, timestamp=utime, accomplished=True, accomplished_time=utime)
        else:
            ia = InteractionAccess.objects.get(interaction=interaction, team=t)
            if ia.accomplished:
                continue
            ia.accomplished = True
            ia.accomplished_time = utime
            ia.save()
    return render(request, 'gatekeeper/result.html', {'result': 'Quietly completed "%s" for %d teams' % (interaction.name, total)})

@staff_member_required
def gatekeeper_prelaunch_view(request):
    if 'prelaunch' not in request.GET:
        return HttpResponseBadRequest()
    teams = Team.objects.all()
    total = teams.count()
    start = 0
    if 'offset' in request.GET:
        start = int(request.GET['offset'])
    else:
        clear_redis()
        reset_global_state()
    teams = teams[start:start + COUNT]
    utime = datetime.datetime.fromtimestamp(settings.UNLOCK_TIME, tz=datetime.timezone.utc)
    start_all(utime=utime, teams=teams)
    setting = Y2021Settings.objects.get_or_create(name='prelaunched')[0]
    setting.value = 'TRUE'
    setting.save()
    logger.info('Prelaunched %03d/%03d.' % (min(start + COUNT, total), total))
    if total > start + COUNT:
        return HttpResponseRedirect(request.path + '?prelaunch=1&offset=%d' % (start + COUNT))
    return render(request, 'gatekeeper/result.html', {'result': 'Prelaunched %d teams.' % (total)})

@staff_member_required
@transaction.atomic
def gatekeeper_launch_view(request):
    setting = Y2021Settings.objects.get_or_create(name='prelaunched')[0]
    if setting.value != 'TRUE':
        return HttpResponse("You need to prelaunch first.")
    launch_hunt()
    return render(request, 'gatekeeper/result.html', {'result': 'Launched.'})

@staff_member_required
def gatekeeper_unlock_mmo_view(request):
    if 'unlock' not in request.GET:
        return HttpResponseBadRequest()
    teams = Team.objects.all()
    total = teams.count()
    unlock_mmo()
    return render(request, 'gatekeeper/result.html', {'result': 'Unlocked %d teams' % (total)})

@staff_member_required
def gatekeeper_force_unlock_view(request):
    if 'unlock' not in request.GET:
        return HttpResponseBadRequest()
    teams = Team.objects.all()
    total = teams.count()
    start = 0
    if 'offset' in request.GET:
        start = int(request.GET['offset'])
        utime = datetime.datetime.fromtimestamp(int(request.GET['utime']), tz=datetime.timezone.utc)
    else:
        utime = now()
    teams = teams[start:start + COUNT]
    force_unlock(utime=utime, teams=teams)
    logger.info('Force unlocked %03d/%03d.' % (min(start + COUNT, total), total))
    if total > start + COUNT:
        return HttpResponseRedirect(request.path + '?unlock=1&offset=%d&utime=%d' % (start + COUNT, int(utime.timestamp())))
    unlock_mmo()
    return render(request, 'gatekeeper/result.html', {'result': 'Unlocked %d teams.' % (total)})

@staff_member_required
def gatekeeper_disable_mmo_view(request):
    if 'disable' not in request.GET:
        return HttpResponseBadRequest()
    utime = now()
    disable_mmo(utime)
    return render(request, 'gatekeeper/result.html', {'result': 'Disabled MMO.'})

@staff_member_required
def gatekeeper_nuke_cache_view(request):
    if 'nuke_cache' not in request.GET:
        return HttpResponseBadRequest()
    clear_redis()
    requests.post(settings.CLEAR_TEMPEST_URL, data='all', verify=False)
    return render(request, 'gatekeeper/result.html', {'result': 'Nuked cache.'})
