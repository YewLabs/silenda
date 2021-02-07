import collections
import json
import time
import colorsys

from django.http import HttpResponse
from django.template import Context, loader
from django.shortcuts import redirect, render, get_object_or_404
from django.core.cache import cache
from django.db.models import Count, Max
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.gzip import gzip_page

import datetime

from .models import *

import logging
logger = logging.getLogger(__name__)

DASHBOARD_CACHE_TIME = 20

@staff_member_required
def all_teams_update(request):
    logger.info("updating all teams dashboard...")

    all_team = list(Team.objects.filter(is_admin=False, is_special=False).select_related('y2021teamdata'))
    all_log_id = TeamLog.objects.values('team_id').annotate(mid=Max('id')).values_list('mid', flat=True)
    all_log = {log.team_id: log for log in TeamLog.objects.filter(id__in=all_log_id)}
    all_puzzle_found = collections.defaultdict(dict)
    all_puzzle_released = collections.defaultdict(dict)
    team_solved = collections.defaultdict(int)
    all_puzzle_detail = collections.defaultdict(
        lambda: collections.defaultdict(lambda: collections.defaultdict(dict)))
    nonAdmin = PuzzleAccess.objects.filter(team__is_admin=False)
    accesses = (nonAdmin.exclude(puzzle__round__url='infinite') | nonAdmin.filter(puzzle__round__url='infinite', puzzle__is_meta=True))
    for team_id, puzzle_id, round_id, found, solved, is_meta in (accesses
        .values_list('team_id', 'puzzle_id', 'puzzle__round_id', 'found', 'solved', 'puzzle__is_meta')):
        if 'counts' not in all_puzzle_detail[team_id][round_id]:
            all_puzzle_detail[team_id][round_id]['counts'] = {'found': 0, 'released': 0}
        if found:
            all_puzzle_found[team_id][puzzle_id] = solved
            all_puzzle_detail[team_id][round_id]['counts']['found'] += 1
        all_puzzle_released[team_id][puzzle_id] = solved
        all_puzzle_detail[team_id][round_id]['counts']['released'] += 1
        all_puzzle_detail[team_id][round_id][is_meta][puzzle_id] = solved
        if solved:
            team_solved[team_id] += 1
    all_puzzle_survey = dict(PuzzleSurvey.objects
        .filter(team__is_admin=False)
        .values_list('team_id')
        .annotate(Count('puzzle_id', distinct=True))
        .order_by())
    all_contact_request = dict(ContactRequest.objects
        .filter(team__is_admin=False, resolved=False)
        .values_list('team_id')
        .annotate(Count('team_id'))
        .order_by())
    all_interaction = list(Interaction.objects.order_by('order'))
    all_interaction_access = collections.defaultdict(dict)
    all_interaction_pending = collections.defaultdict(int)
    for team_id, interaction_id, accomplished in (InteractionAccess.objects
        .filter(team__is_admin=False)
        .values_list('team_id', 'interaction_id', 'accomplished')):
        all_interaction_access[team_id][interaction_id] = accomplished
        if not accomplished: all_interaction_pending[team_id] += 1
    all_round = list(Round.objects.order_by('order').select_related('y2021rounddata'))
    all_round_access = set(RoundAccess.objects.values_list('team_id', 'round_id'))
    all_puzzle = (Puzzle.objects.exclude(round__url='infinite') | Puzzle.objects.filter(round__url='infinite', is_meta=True)).order_by(
        'is_meta', 'y2021puzzledata__points_req', 'y2021puzzledata__feeder_req')
    all_puzzle_by_round = collections.defaultdict(list)
    for puzzle in all_puzzle:
        all_puzzle_by_round[puzzle.round_id].append(puzzle)

    def get_encoded_interaction(interaction, solved):
        ret = 'ip'
        if solved:
            ret += 's'
        elif solved is not None:
            ret += 'f'
        else:
            ret += 'u'
        return ret + str(interaction.id)
    def get_encoded_puzzle(puzzle, found, solved):
        ret = 'p'
        if puzzle.is_meta:
            ret += 'r'
        else:
            ret += 'p'
        if solved:
            ret += 's'
        elif found is not None:
            ret += 'f'
        elif solved is not None:
            ret += 'r'
        else:
            ret += 'u'
        return ret + str(puzzle.id)

    teams = []
    for team in all_team:
        interactions = []
        for interaction in all_interaction:
            solved = all_interaction_access[team.id].get(interaction.id)
            interactions.append(get_encoded_interaction(interaction, solved))
        rounds = []
        for round in all_round:
            puzzles = []
            if (team.id, round.id) in all_round_access:
                for puzzle in all_puzzle_by_round[round.id]:
                    found = all_puzzle_found[team.id].get(puzzle.id)
                    solved = all_puzzle_released[team.id].get(puzzle.id)
                    puzzles.append(get_encoded_puzzle(puzzle, found, solved))
            rounds.append({
                'round': round,
                'puzzles': puzzles,
                'released': (team.id, round.id) in all_round_access,
                'solved': all(all_puzzle_detail[team.id][round.id][True].values()) \
                        and len(all_puzzle_detail[team.id][round.id][True]) \
                        == sum(int(p.is_meta) for p in all_puzzle_by_round[round.id]) \
                        and len(all_puzzle_detail[team.id][round.id][True]) > 0,
                'num_solved': sum(all_puzzle_detail[team.id][round.id][False].values()) + sum(all_puzzle_detail[team.id][round.id][True].values()),
                'num_found': all_puzzle_detail[team.id][round.id]['counts'].get('found', 0),
                'num_released': all_puzzle_detail[team.id][round.id]['counts'].get('released', 0),
                'juice': team.y2021teamdata.get_juice(round.y2021rounddata.tempest_id)
            })
        p_found = len(all_puzzle_found[team.id])
        p_released = len(all_puzzle_released[team.id])
        p_solved = team_solved[team.id]
        i_released = len(all_interaction_access[team.id])
        i_solved = sum(all_interaction_access[team.id].values())
        teams.append({
            'team': team,
            'rounds': rounds,
            'interactions': interactions,
            'log1': all_log.get(team.id),
            'r_released': sum(1 for x in rounds if x['released']),
            'r_solved': sum(1 for x in rounds if x['solved']),
            'p_found': p_found,
            'p_released': p_released,
            'p_solved': p_solved,
            'p_open': p_released - p_solved,
            'p_surveyed': all_puzzle_survey.get(team.id, 0),
            'q_submissions': all_contact_request.get(team.id, 0),
            'i_released': i_released,
            'i_solved': i_solved,
            'i_open': i_released - i_solved
        })

    context = {
        'updated': datetime.datetime.now(),
        'teams': sorted(teams, key=lambda x: (-x['r_solved'], -x['p_solved'])),
        'q_total': sum(all_contact_request.values()),
        'q_teams': len(all_contact_request),
        'r_total': len(all_round),
        'p_total': len(all_puzzle),
        'i_pending': sum(all_interaction_pending.values()),
        'i_teams': len(all_interaction_pending),
        'i_total': len(all_interaction),
        'all_interaction': all_interaction,
        'all_puzzle': all_puzzle,
    }
    result = render(request, 'hq/all-teams.html', context)

    cache.set('all_teams', result, DASHBOARD_CACHE_TIME)
    logger.info("...done")
    return result

@gzip_page
@staff_member_required
def all_teams_view(request):
    return HttpResponse(cache.get('all_teams') or all_teams_update(request))


def percent(n, d):
    if d == 0:
        return '-'
    return n*100//d

@staff_member_required
def all_puzzles_update(request):
    logger.info("updating all puzzles dashboard...")

    all_round = Round.objects.exclude(url='infinite').order_by('order')
    all_puzzle = Puzzle.objects.exclude(round__url='infinite').order_by(
        'is_meta', 'y2021puzzledata__points_req', 'y2021puzzledata__feeder_req')
    all_puzzle_found = collections.defaultdict(dict)
    all_puzzle_released = collections.defaultdict(dict)
    all_puzzle_first = dict()
    for team_id, puzzle_id, found, solved, timestamp in (PuzzleAccess.objects
        .filter(team__is_admin=False)
        .exclude(puzzle__round__url='infinite')
        .order_by('id')
        .values_list('team_id', 'puzzle_id', 'found', 'solved', 'timestamp')):
        if found:
            all_puzzle_found[puzzle_id][team_id] = solved
        all_puzzle_released[puzzle_id][team_id] = solved
        all_puzzle_first.setdefault(puzzle_id, timestamp)
    all_puzzle_survey = dict(PuzzleSurvey.objects
        .filter(team__is_admin=False)
        .values_list('puzzle_id')
        .annotate(Count('team_id', distinct=True))
        .order_by())
    all_interaction = Interaction.objects.order_by('order')
    all_interaction_access = collections.defaultdict(dict)
    for team_id, interaction_id, accomplished in (InteractionAccess.objects
        .filter(team__is_admin=False)
        .values_list('team_id', 'interaction_id', 'accomplished')):
        all_interaction_access[interaction_id][team_id] = accomplished
    t_total = Team.objects.filter(is_admin=False).count()
    p_total = len(all_puzzle)
    m_total = 0
    p_found = 0
    p_released = 0
    p_solved = 0

    rounds = []
    for round in all_round:
        puzzles = []
        for puzzle in all_puzzle:
            if puzzle.round_id == round.id:
                found = len(all_puzzle_found[puzzle.id])
                released = len(all_puzzle_released[puzzle.id])
                solved = sum(all_puzzle_found[puzzle.id].values())
                if found > 0: p_found += 1
                if released > 0: p_released += 1
                if solved > 0: p_solved += 1
                if puzzle.is_meta: m_total += 1
                puzzles.append({
                    'puzzle': puzzle,
                    'first': all_puzzle_first.get(puzzle.id, None),
                    'surveys': all_puzzle_survey.get(puzzle.id, 0),
                    'found': found,
                    'foundp': percent(found, t_total),
                    'released': released,
                    'releasedp': percent(released, t_total),
                    'solved': solved,
                    'solvedp': percent(solved, released),
                })
        rounds.append({
            'round': round,
            'puzzles': puzzles,
        })
    interactions = []
    for interaction in all_interaction:
        released = len(all_interaction_access[interaction.id])
        solved = sum(all_interaction_access[interaction.id].values())
        interactions.append({
            'puzzle': interaction,
            'is_meta': False,
            'released': released,
            'releasedp': percent(released, t_total),
            'found': released,
            'foundp': percent(released, t_total),
            'solved': solved,
            'solvedp': percent(solved, released),
        })
    rounds.append({
        'name': 'Interactions',
        'puzzles': interactions,
    })

    context = {
        'updated': datetime.datetime.now(),
        'rounds': rounds,
        't_total': t_total,
        'i_total': len(all_interaction),
        'p_total': p_total,
        'm_total': m_total,
        'p_released': p_released,
        'p_releasedp': percent(p_released, p_total),
        'p_found': p_found,
        'p_foundp': percent(p_found, p_total),
        'p_solved': p_solved,
        'p_solvedp': percent(p_solved, p_released),
    }
    result = render(request, 'hq/all-puzzles.html', context)
    cache.set('all_puzzles', result, DASHBOARD_CACHE_TIME)
    logger.info("...done")
    return result

@staff_member_required
def all_puzzles_view(request):
    return HttpResponse(cache.get('all_puzzles') or all_puzzles_update(request))

@staff_member_required
def one_team_view(request, team_url):
    team = Team.objects.select_related('y2021teamdata').get(url=team_url)
    all_round = Round.objects.select_related('y2021rounddata').order_by('order')
    all_round_access = {x.round_id: x for x in team.roundaccess_set.all()}
    all_puzzle = ((Puzzle.objects.exclude(round__url='infinite') | Puzzle.objects.filter(round__url='infinite', is_meta=True)).select_related('round').order_by(
        'round__order', 'order', 'y2021puzzledata__points_req', 'y2021puzzledata__feeder_req'))
    all_puzzle_access = {x.puzzle_id: x for x in team.puzzleaccess_set.all()}
    all_interaction = Interaction.objects.order_by('order')
    all_interaction_access = {x.interaction_id: x for x in team.interactionaccess_set.all()}
    all_hint_submission = dict(team.hintsubmission_set
        .values_list('puzzle_id')
        .annotate(Count('puzzle_id'))
        .order_by())
    all_puzzle_survey = team.puzzlesurvey_set.select_related('puzzle')

    rounds = []
    for round in all_round:
        rounds.append({
            'round': round,
            'access': all_round_access.get(round.id, None),
            'juice': team.y2021teamdata.get_juice(round.y2021rounddata.tempest_id)
        })
    puzzles = []
    for puzzle in all_puzzle:
        access = all_puzzle_access.get(puzzle.id, None)
        stime = None
        if access and access.solved:
            stime = access.solved_time - access.found_timestamp
        puzzles.append({
            'puzzle': puzzle,
            'access': access,
            'hints': all_hint_submission.get(puzzle.id, 0),
            'stime': stime,
        })
    interactions = []
    for interaction in all_interaction:
        interactions.append({
            'interaction': interaction,
            'access': all_interaction_access.get(interaction.id, None),
        })

    context = {
        'team': team,
        'rounds': rounds,
        'puzzles': puzzles,
        'interactions': interactions,
        'hints': sum(all_hint_submission.values()),
        'surveys': all_puzzle_survey,
    }
    return render(request, 'hq/one-team.html', context)

@staff_member_required
def dashboard(request):
    return render(request, 'hq/main.html', {})

def team_id_to_line_color(team_id):
    oldSeed = random.random()
    random.seed(team_id+50)
    r, g, b = colorsys.hls_to_rgb(random.random(), random.random() * 0.5 + 0.25, random.random() * 0.5 + 0.3)
    random.seed(oldSeed)
    return 'rgba({}, {}, {}, {})'.format(
        int(r*255),
        int(g*255),
        int(b*255),
        1,
    )

@staff_member_required
def solve_graph_update(request):
    teams_by_id = {
        team.id: team
        for team in Team.objects.filter(is_admin=False, is_special=False).select_related('y2021teamdata')
    }
    puzzles_by_id = {
        puzzle.id: puzzle
        for puzzle in (Puzzle.objects.exclude(round__url='infinite') | Puzzle.objects.filter(round__url='infinite', is_meta=True))
    }

    puzzle_accesses = (
        PuzzleAccess.objects
        .filter(team__is_admin=False, team__is_special=False, solved=True)
        .values_list('team_id', 'puzzle_id', 'solved_time')
        .order_by('solved_time')
    )
    puzzle_accesses = (
        puzzle_accesses.exclude(puzzle__round__url='infinite') |
        puzzle_accesses.filter(puzzle__round__url='infinite', puzzle__is_meta=True)
    )

    solve_counts_by_team = collections.defaultdict(int)

    solve_counts_time_series_by_team = collections.defaultdict(list)

    for team_id, puzzle_id, solved_time in puzzle_accesses:
        if solved_time is None:
            continue
        solve_counts_by_team[team_id] += 1
        puzzle_name = puzzles_by_id[puzzle_id].name
        solved_time_as_unix = int(time.mktime(solved_time.timetuple())*1000)
        solve_counts_time_series_by_team[team_id].append((solved_time_as_unix, solve_counts_by_team[team_id], puzzle_name))

    result = render(request, 'hq/solvegraph.html', {
        'solve_counts_for_chartjs': {
            'datasets': [
                {
                    'label': teams_by_id[team_id].name,
                    'data': [
                        {
                            'x': solve_count[0],
                            'y': solve_count[1],
                        } for solve_count in solve_counts
                    ],
                    'borderColor': team_id_to_line_color(team_id),
                    'fill': False,
                }
                for team_id, solve_counts in solve_counts_time_series_by_team.items()
            ],
            'point_labels': [
                [
                    '{} solved {}, {} {} solved'.format(teams_by_id[team_id].name, solve_count[2], solve_count[1], 'puzzle' if solve_count[1] == 1 else 'puzzles')
                    for solve_count in solve_counts
                ]
                for team_id, solve_counts in solve_counts_time_series_by_team.items()
            ],
        },
    })

    cache.set('solve_graph_page', result, DASHBOARD_CACHE_TIME)
    return result

@staff_member_required
def solve_graph(request):
    return HttpResponse(cache.get('solve_graph_page') or solve_graph_update(request))
