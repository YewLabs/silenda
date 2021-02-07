from django.http import HttpResponse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from .actions import clear_cache
from .decorators import require_admin
from .submit import now
from . import models


def get_shortcuts():
    for action, callback in Shortcuts.__dict__.items():
        if action.startswith('__'):
            continue
        yield {'action': action, 'name': callback.__doc__}

@require_POST
@require_admin
@xframe_options_sameorigin
def shortcuts(request):
    response = HttpResponse(content_type='text/html')
    callback = getattr(Shortcuts, request.POST.get('action'))
    puzzle = models.Puzzle.objects.get(url=request.POST.get('puzzle'))
    callback(puzzle, request.team)
    clear_cache(request.team)
    response.write('<script>top.location.reload()</script>')
    return response


class Shortcuts:
    def solve(puzzle, team):
        'Solve this puzzle'
        team.puzzlesubmission_set.create(
            puzzle=puzzle, answer=puzzle.answer, resolved=True, correct=True)
        team.puzzleaccess_set.filter(puzzle=puzzle).update(
            solved=True, solved_time=now())

    def unsolve(puzzle, team):
        'Unsolve this puzzle'
        team.puzzlesubmission_set.filter(puzzle=puzzle, correct=True).delete()
        team.puzzleaccess_set.filter(puzzle=puzzle).update(solved=False)

    def delete_guesses(puzzle, team):
        'Clear guesses'
        team.puzzlesubmission_set.filter(puzzle=puzzle).delete()

    def unanswered_hint(puzzle, team):
        'Request hint'
        team.hintsubmission_set.create(
            puzzle=puzzle, question='Halp', resolved=False)

    def answered_hint(puzzle, team):
        'Answered hint'
        team.hintsubmission_set.create(
            puzzle=puzzle, question='Halp', resolved=True, result='Ok')

    def delete_hints(puzzle, team):
        'Clear hints'
        team.hintsubmission_set.filter(puzzle=puzzle).delete()
