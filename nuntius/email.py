import requests

from django.conf import settings

def send_mail(subject, body, to_addrs, from_addr=settings.DEFAULT_SENDER):
    data = {
        "from": "%s <%s>" % (from_addr[0], from_addr[1]),
        "to": to_addrs,
        "subject": subject,
        "html": body.replace('\n', '<br/>'),
        "recipient-variables": '{}'
    }
    return requests.post("https://api.mailgun.net/v3/%s/messages" % (settings.DEFAULT_DOMAIN), auth=("api", settings.MAILGUN_API_KEY), data=data)

def send_team_mail(subject, body, teams, from_addr=settings.DEFAULT_SENDER):
    emails = [t.email for t in teams if '@' in t.email]
    return send_mail(subject, body, emails, from_addr)
