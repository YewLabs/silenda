import json
import logging

from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseServerError,
)
from functools import wraps

from spoilr.models import (
    Interaction,
    InteractionAccess,
    Puzzle,
    PuzzleAccess,
    PuzzleSession,
    Round,
    RoundAccess,
    Team,
)

from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode

logger = logging.getLogger(__name__)


def json_view(view_func):
    """
    Decorator which returns a JSON response as "application/json".  The
    wrapped view function should return a dictionary.
    """

    @wraps(view_func)
    def _wrapped_view_func(request, *args, **kwargs):
        response = {}
        status_code = 200
        try:
            result = view_func(request, *args, **kwargs)
            if not isinstance(result, dict):
                raise Exception('JSON view %s did not return a dict, got %s instead', view_func, result)
            if 'status_code' in result:
                status_code = int(result['status_code'])
            response['result'] = result
            if status_code <= 399:
                response['success'] = True
            else:
                response['success'] = False
        except:
            logger.exception('Internal error')
            response['success'] = False

        return HttpResponse(json.dumps(response), content_type='application/json', status=status_code)

    return _wrapped_view_func

def require_prelaunch_team(view_func):
    """
    Decorator which requires the given request to be from a user which is a
    member of a Team.  Adds the request.team property to the request
    indicating the Team object.
    """

    @wraps(view_func)
    def _wrapped_view_func(request, *args, **kwargs):
        username = request.session.get('team', None)
        if not username:
            return redirect(reverse('login') + '?' + urlencode({'next': request.path}))
        try:
            request.team = Team.objects.get(username=username)
        except:
            logger.exception('cannot find team for user %s', username)
            return redirect(reverse('login') + '?' + urlencode({'next': request.path}))
        request.is_it_hunt_yet = is_it_hunt_yet(request)
        return view_func(request, *args, **kwargs)

    return _wrapped_view_func

def require_team(view_func):
    return require_hunt(require_prelaunch_team(view_func))

def require_admin(view_func):
    """
    Decorator which requires the given request to be from a user which is a
    member of a Team for which is_admin is True.  Also runs the require_team
    decorator.
    """
    @wraps(view_func)
    def _wrapped_view_func(request, *args, **kwargs):
        if not request.team.is_admin:
            logger.error("Team is not an admin: %s", request.team)
            return HttpResponseForbidden("Access denied")
        return view_func(request, *args, **kwargs)

    return require_prelaunch_team(_wrapped_view_func)

def is_it_hunt_yet(request):
    if hasattr(request, 'is_it_hunt_yet'):
        return request.is_it_hunt_yet
    from hunt.models import Y2021Settings
    setting = Y2021Settings.objects.get_or_create(name='is_it_hunt_yet')[0]
    result = setting.value == 'TRUE'
    if result:
        return True
    try:
        username = request.session.get('team', None)
        if username:
            team = Team.objects.get(username=username)
            return team.is_admin or team.is_special
    except:
        pass
    return False

def require_hunt(view_func):
    """
    Decorator which requires hunt.
    """

    @wraps(view_func)
    def _wrapped_view_func(request, *args, **kwargs):
        if not is_it_hunt_yet(request):
            return redirect(reverse('prelaunch'))
        return view_func(request, *args, **kwargs)

    return _wrapped_view_func

def require_puzzle_url(view_func):
    """
    Decorator which requires the given request to contain a puzzle ID in its
    URL, via the 'puzzle' kwarg from the URL view.  Adds the request.puzzle
    property to the request indicating the Puzzle object.
    """

    @wraps(view_func)
    def _wrapped_view_func(request, *args, **kwargs):
        try:
            puzzle_url = kwargs['puzzle']
            request.puzzle = Puzzle.objects.get(url=puzzle_url)
            del kwargs['puzzle']
        except:
            logger.exception('Cannot find puzzle %s', puzzle_url)
            return HttpResponseBadRequest('Cannot find puzzle ' + puzzle_url)

        return view_func(request, *args, **kwargs)

    return require_hunt(_wrapped_view_func)


def require_puzzle_access(view_func):
    """
    Decorator which requires the given user's team to have access to the
    puzzle referred to in the ID in the URL (i.e. the puzzle is unlocked).
    This decorator also applies the require_team and require_puzzle_slug
    decorators in before it.

    If the puzzle exists but the team does not have access to the puzzle, an
    identical error response is returned as if the puzzle didn't exist.
    """

    @wraps(view_func)
    def _wrapped_view_func(request, *args, **kwargs):
        team = request.team
        puzzle = request.puzzle
        try:
            request.puzzle_access = PuzzleAccess.objects.get(team=team, puzzle=puzzle, found=True)
        except:
            logger.exception('Team %s does not have access to puzzle %s', team, puzzle)
            return HttpResponseBadRequest('Cannot find puzzle ' + puzzle.url)

        return view_func(request, *args, **kwargs)

    return require_team(require_puzzle_url(_wrapped_view_func))


def require_puzzle_known(view_func):
    """
    Decorator which requires the given user's team to have access to the
    puzzle referred to in the ID in the URL (i.e. the puzzle is unlocked).
    This decorator also applies the require_team and require_puzzle_slug
    decorators in before it.

    If the puzzle exists but the team does not have access to the puzzle, an
    identical error response is returned as if the puzzle didn't exist.
    """

    @wraps(view_func)
    def _wrapped_view_func(request, *args, **kwargs):
        team = request.team
        puzzle = request.puzzle
        try:
            request.puzzle_access = PuzzleAccess.objects.get(team=team, puzzle=puzzle)
        except:
            logger.exception('Team %s does not have access to puzzle %s', team, puzzle)
            return HttpResponseBadRequest('Cannot find puzzle ' + puzzle.url)

        return view_func(request, *args, **kwargs)

    return require_team(require_puzzle_url(_wrapped_view_func))


def require_round_url(view_func):
    @wraps(view_func)
    def _wrapped_view_func(request, *args, **kwargs):
        try:
            round_url = kwargs['round']
            if round_url in ('exa', 'peta', 'tera', 'giga', 'mega', 'kilo', 'hecto', 'deca', 'deci', 'centi', 'milli', 'micro', 'nano', 'pico', 'femto', 'atto'):
                round_url = 'nano'
            request.round = Round.objects.get(url=round_url)
            del kwargs['round']
        except:
            logger.exception('Cannot find round %s', round_url)
            return HttpResponseBadRequest('Cannot find round ' + round_url)

        return view_func(request, *args, **kwargs)

    return require_hunt(_wrapped_view_func)

def require_round_access(view_func):
    @wraps(view_func)
    def _wrapped_view_func(request, *args, **kwargs):
        team = request.team
        round = request.round
        try:
            request.round_access = RoundAccess.objects.get(team=team, round=round)
        except:
            logger.exception('Team %s does not have access to round %s', team, round)
            return HttpResponseBadRequest('Cannot find round ' + round.url)

        return view_func(request, *args, **kwargs)

    return require_team(require_round_url(_wrapped_view_func))


def puzzle_session(view_func):
    """
    Decorator which extracts the puzzle session ID from the request and
    attaches that session's session data to the request, if such a session
    exists.  If no session exists, a new empty session is created.

    Currently, only POST requests are supported, and the response must be
    JSON (using the json_view decorator); the session ID is returned back to
    the client via the "session_id" in the JSON response, and the client
    must manually manage the session ID.
    """

    @wraps(view_func)
    def _wrapped_view_func(request, *args, **kwargs):
        session_id = request.POST.get('session_id')
        session = None

        if session_id:
            try:
                session = PuzzleSession.objects.get(session_id=session_id)
            except:
                pass

        if not session:
            session = PuzzleSession.create()

        request.puzzle_session = json.loads(session.session_data)

        response = view_func(request, *args, **kwargs)
        response['session_id'] = session.session_id

        session.session_data = json.dumps(request.puzzle_session)
        session.save()

        return response

    return _wrapped_view_func

def require_interaction_access(interaction_name):
    """
    Decorator which requires the given user's team to have access to the
    interaction passed to the decorator.  This decorator also applies the
    require_team decorators in before it.

    If the interaction exists but the team does not have access to it, a
    404 is returned.
    """

    def _decorator(view_func):
        @wraps(view_func)
        def _wrapped_view_func(request, *args, **kwargs):
            team = request.team
            try:
                request.interaction = Interaction.objects.get(name=interaction_name)
            except Exception:
                logger.exception("No such interaction: %s", interaction_name)
                return HttpResponseServerError()

            try:
                request.interaction_access = InteractionAccess.objects.get(
                    interaction=request.interaction,
                    team=request.team
                )
            except Exception:
                logger.exception('Team %s does not have access to interaction %s',
                                 team, request.interaction)
                return HttpResponseNotFound("Not found")

            return view_func(request, *args, **kwargs)
        return require_team(_wrapped_view_func)

    return _decorator
