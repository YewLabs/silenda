from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from spoilr.log import discord_basic_log

from spoilr.models import Interaction, Team, PuzzleAccess, IncomingMessage
from spoilr.actions import release_interaction

from nuntius.email import send_mail

@require_POST
@csrf_exempt
def incoming_email_view(request):
    to = request.POST.get('recipient')
    frm = request.POST.get('sender')
    subject = request.POST.get('subject')
    msg = ''

    body_plain = request.POST.get('body-plain', '')
    body_html = request.POST.get('body-html', '')

    team = None
    interaction = None

    if 'submission' in to:
        try:
            ikey, tkey = subject.strip().lower().rsplit(' for ', 1)
            interaction = Interaction.objects.get(email_key__iexact=ikey)
            team = Team.objects.get(username__iexact=tkey)
            msg += '\nSubmission for %s' % (interaction.name)
            if interaction.puzzle:
                if PuzzleAccess.objects.filter(team=team, puzzle=interaction.puzzle, found=True).exists():
                    release_interaction(team, interaction, 'Received email')
                else:
                    msg += '\nTeam does not have access to puzzle "%s"' % (interaction.puzzle.name)
        except Interaction.DoesNotExist:
            msg += '\nSubmission for unknown interaction, please manually triage.'
        except Team.DoesNotExist:
            msg += '\nSubmission for unknown team, please manually triage.'

    discord_basic_log('email', {'embeds': [{
        'description': msg,
        'footer': {'text': subject},
        'fields': [
            {'name': 'From', 'value': frm, 'inline': True},
            {'name': 'To', 'value': to, 'inline': True},
        ],
    }]})

    IncomingMessage.objects.create(subject=subject, body_text=body_plain, body_html=body_html, sender=frm, recipient=to, team=team, interaction=interaction)
    return HttpResponse('OK')
