import json
import mimetypes
import os
import random

from django.shortcuts import redirect, render, reverse
from django.http import FileResponse, HttpResponse
from django.contrib.staticfiles.views import serve
from django.conf import settings
from django.template import Template, Context

import puzzleviewer.utils as utils

from spoilr.models import Team

DISABLE_VIEWER = True

def load_metadata(puzzle_slug):
    filename = os.path.join(settings.PUZZLE_DATA, puzzle_slug, 'metadata.json')
    if not os.path.exists(filename):
        return None
    return json.load(open(filename))

def puzzle(request, puzzle_slug):
    if DISABLE_VIEWER:
        t = Team.objects.get(username='factcheck')
        request.session['team'] = t.username
        request.session.save()
        return redirect(reverse('puzzle_view', args=(puzzle_slug,)))
    filename = os.path.join(settings.PUZZLE_DATA, puzzle_slug, 'index.html')
    if not os.path.exists(filename):
        return HttpResponse('Unknown puzzle \'%s\'' % (puzzle_slug))
    metadata = load_metadata(puzzle_slug)
    html = None
    with open(filename) as f:
        html = f.read()
    metadata = load_metadata(puzzle_slug)
    posthunt = os.path.join(settings.PUZZLE_DATA, puzzle_slug, 'posthunt/index.html')
    has_posthunt = os.path.exists(posthunt)
    solved = []
    if 'solved' in request.GET:
        solved = request.GET['solved'].split(',')
    context = {
        'puzzle_slug': puzzle_slug,
        'title': metadata['puzzle_title'],
        'rand': str(random.random()),
        'answer': metadata['answer'],
        'normalized_answer': utils.normalize_answer(metadata['answer']),
        'puzzlord_id': metadata['puzzle_idea_id'],
        'has_posthunt': has_posthunt,
        'solved': solved,
        'round_solved': len(solved),
        'sroot': '',
        'sproot': '',
    }
    context['index_html'] = Template(html).render(Context(context))
    return render(request, 'puzzlepage.html', context)

def solution(request, puzzle_slug):
    if DISABLE_VIEWER:
        t = Team.objects.get(username='factcheck')
        request.session['team'] = t.username
        request.session.save()
        return redirect(reverse('puzzle_solution', args=(puzzle_slug,)))
    filename = os.path.join(settings.PUZZLE_DATA, puzzle_slug, 'solution/index.html')
    if not os.path.exists(filename):
        return HttpResponse('Unknown puzzle \'%s\'' % (puzzle_slug))
    metadata = load_metadata(puzzle_slug)
    html = None
    with open(filename) as f:
        html = f.read()

    context = {
        'puzzle_slug': puzzle_slug,
        'title': metadata['puzzle_title'],
        'answer': metadata['answer'],
        'credits': metadata['credits'],
        'rand': str(random.random()),
        'sroot': '',
        'sproot': '../',
    }
    context['index_html'] = Template(html).render(Context(context))
    return render(request, 'solution.html', context)

def posthunt(request, puzzle_slug):
    filename = os.path.join(settings.PUZZLE_DATA, puzzle_slug, 'posthunt/index.html')
    if not os.path.exists(filename):
        return HttpResponse('Unknown puzzle \'%s\'' % (puzzle_slug))
    metadata = load_metadata(puzzle_slug)
    html = None
    with open(filename) as f:
        html = f.read()
    metadata = load_metadata(puzzle_slug)
    context = {
        'puzzle_slug': puzzle_slug,
        'title': metadata['puzzle_title'],
        'rand': str(random.random()),
        'answer': metadata['answer'],
        'puzzlord_id': metadata['puzzle_idea_id'],
        'has_hunt': True,
        'sroot': '',
        'sproot': '',
    }
    context['index_html'] = Template(html).render(Context(context))
    return render(request, 'puzzlepage.html', context)

def resource(request, puzzle_slug, resource):
    filename = os.path.join(settings.PUZZLE_DATA, puzzle_slug, resource)
    if not os.path.exists(filename):
        return HttpResponse('Unknown file \'%s\'' % (filename))
    data = None
    if filename.endswith('.js') or filename.endswith('.json') or filename.endswith('.css') or filename.endswith('.html'):
        ctype = 'text/plain'
        if filename.endswith('.css'):
            ctype = 'text/css'
        elif filename.endswith('.html'):
            ctype = 'text/html'
        else:
            ctype = 'application/javascript'
        return HttpResponse(open(filename).read().replace('{{sroot}}', ''), content_type=ctype)
    return FileResponse(open(filename, 'rb'))
