from django import template

register = template.Library()

@register.filter
def solvedpuzzle(team, puzzle_slug):
    if not team:
        return 0
    return team.solved_puzzles.filter(url=puzzle_slug).count()
