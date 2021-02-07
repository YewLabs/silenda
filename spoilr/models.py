from django.db import models, transaction
from django.conf import settings
from django.utils.crypto import get_random_string
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save, pre_delete, post_delete

from django.utils import timezone
import os.path
import random
import string

from .signals import *

CACHE_TIME = 60*60  # cache time in seconds for hq pages and logs

import logging
logger = logging.getLogger(__name__)

def now():
    return timezone.localtime(timezone.now())

class Round(models.Model):
    url = models.CharField(max_length=200, unique=True, verbose_name="slug")
    name = models.CharField(max_length=200, unique=True)
    order = models.IntegerField(unique=True)

    def __str__(self):
        return 'Infinite Corridor' if self.url == 'infinite-template' else self.name

    class Meta:
        ordering = ['order']

class Puzzle(models.Model):
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    url = models.CharField(max_length=200, unique=True, verbose_name="slug")
    name = models.CharField(max_length=200, unique=True)
    answer = models.CharField(max_length=100)
    credits = models.TextField(default='')
    order = models.IntegerField()
    handler_info = models.CharField(max_length=1000, blank=True, null=True)
    is_meta = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        prefix = 'metapuzzle' if self.is_meta else 'puzzle'
        rname = self.round
        NANO_NAMES = ['⊥IW.giga', '⊥IW.giga', '⊥IW.kilo', '⊥IW.milli', '⊥IW.nano']
        if self.round.url == 'nano':
            rname = NANO_NAMES[self.y2021puzzledata.level]
        return '%s "%s" (%s)' % (prefix, self.name, rname)

    def hash(self):
        return hash(self.url)  #XXX obfuscate this for security

    class Meta:
        unique_together = ('round', 'order')
        ordering = ['round__order', 'order']

Round.puzzles = models.ManyToManyField(Puzzle)

class Interaction(models.Model):
    url = models.CharField(max_length=200, unique=True, verbose_name="slug")
    name = models.CharField(max_length=200, unique=True)
    order = models.IntegerField(unique=True)
    show_team = models.BooleanField(default=False)
    puzzle = models.ForeignKey(Puzzle, related_name='interaction', blank=True, null=True, on_delete=models.SET_NULL)
    unlock_type = models.CharField(max_length=64, null=True, blank=True)
    email_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    message_template = models.TextField(null=True, blank=True)

    def __str__(self):
        return '%s' % (self.name)

    class Meta:
        ordering = ['order']

class PseudoAnswer(models.Model):
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    answer = models.CharField(max_length=100)
    response = models.TextField()

    def __str__(self):
        return '"%s" (%s)' % (self.puzzle.name, self.answer)

    class Meta:
        unique_together = ('puzzle', 'answer')
        ordering = ['puzzle']

class PuzzleExtraData(models.Model):
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    data = models.TextField(default='')

    def __str__(self):
        return '"%s" (%s)' % (self.puzzle.name, self.name)

    class Meta:
        unique_together = ('puzzle', 'name')
        ordering = ['puzzle']

class Team(models.Model):
    url = models.CharField(max_length=50, unique=True, verbose_name="slug")
    username = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    password = models.CharField(max_length=200)
    rounds = models.ManyToManyField(Round, through='RoundAccess')
    puzzles = models.ManyToManyField(Puzzle, through='PuzzleAccess')
    email = models.CharField(max_length=100)
    phone = models.CharField(max_length=100, default='')
    size_desc = models.CharField(max_length=50)
    is_admin = models.BooleanField(default=False)
    is_special = models.BooleanField(default=False)
    is_limited = models.BooleanField(default=False)

    def get_team_dir(self, suffix=None):
        path = os.path.join(settings.TEAMS_DIR, self.url)
        if suffix:
            path = path + suffix
        return path

    def get_user_symlink(self):
        symlink = os.path.join(settings.USERS_DIR, self.username)
        return symlink

    @property
    def solved_puzzles(self):
        return self.puzzles.filter(puzzleaccess__solved=True)

    # Returns the size as an int
    @property
    def size_int(self):
        try:
            return int(self.size_desc)
        except ValueError:
            return 0

    def __str__(self):
        return '%s' % (self.name)

class TeamExtraData(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    data = models.TextField(default='')

    def __str__(self):
        return '"%s" (%s)' % (self.team.name, self.name)

Team.extras = models.ManyToManyField(TeamExtraData)

class SystemLog(models.Model):
    timestamp = models.DateTimeField(default=now)
    event_type = models.CharField(max_length=50)
    team = models.ForeignKey(Team, blank=True, null=True, on_delete=models.SET_NULL)
    object_id = models.CharField(max_length=200, blank=True)
    message = models.TextField()

    def __str__(self):
        return '%s: %s' % (self.timestamp, self.message)

    class Meta:
        verbose_name_plural = "System log"

class TeamLog(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=now)
    event_type = models.CharField(max_length=50)
    object_id = models.CharField(max_length=50, blank=True)
    link = models.CharField(max_length=200, blank=True)
    message = models.TextField()

    def __str__(self):
        return '[%s] %s: %s' % (self.team, self.timestamp, self.message)

class InteractionAccess(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    interaction = models.ForeignKey(Interaction, on_delete=models.CASCADE)
    accomplished = models.BooleanField(default=False)
    timestamp = models.DateTimeField(default=now)
    last_snooze_time = models.DateTimeField(null=True, blank=True)
    snooze_time = models.DateTimeField(null=True, blank=True)
    accomplished_time = models.DateTimeField(null=True, blank=True)
    snooze_ack = models.BooleanField(default=False)

    def __str__(self):
        s = 'can accomplish'
        if self.snooze_time and self.snooze_time < now():
            s = 'can accomplish (snoozed)'
        if self.accomplished:
            s = 'has accomplished'
        return '%s %s %s' % (self.team, s, self.interaction)

    class Meta:
        unique_together = ('team', 'interaction')

class RoundAccess(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=now)

    def __str__(self):
        return '%s can see %s' % (self.team, self.round)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        emit(round_released_message, self.team, self.round)

    class Meta:
        unique_together = ('team', 'round')
        verbose_name_plural = 'Round access'

class PuzzleAccess(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    found = models.BooleanField(default=False)
    solved = models.BooleanField(default=False)
    timestamp = models.DateTimeField(default=now)
    found_timestamp = models.DateTimeField(null=True, blank=True)
    solved_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        s = 'can access'
        if self.found:
            s = 'can see'
        if self.solved:
            s = 'has solved'
        return '%s %s %s' % (self.team, s, self.puzzle)

    def save(self, *args, **kwargs):
        newObject = False
        if self.pk is None:
            newObject = True
        super().save(*args, **kwargs)
        if newObject:
            logger.info("Release %s" % (self.puzzle))
            emit(puzzle_released_message, self.team, self.puzzle)
        if self.solved:
            if self.puzzle.is_meta:
                emit(metapuzzle_answer_correct_message, self.team, self.puzzle)
            else:
                emit(puzzle_answer_correct_message, self.team, self.puzzle)

    class Meta:
        unique_together = ('team', 'puzzle')
        verbose_name_plural = 'Puzzle access'

class PuzzleSubmission(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=now)
    answer = models.CharField(max_length=100)
    resolved = models.BooleanField(default=False)
    correct = models.BooleanField(default=False)

    def __str__(self):
        return '%s: %s submitted for %s' % (self.timestamp, self.team, self.puzzle)

    class Meta:
        unique_together = ('team', 'puzzle', 'answer')
        ordering = ['-timestamp']

class HintSubmission(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    email = models.CharField(max_length=100)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=now)
    valid = models.BooleanField(default=True)
    question = models.TextField()
    result = models.TextField()
    resolved = models.BooleanField(default=False)

    claimant = models.CharField(max_length=100, null=True, blank=True)
    claim_time = models.DateTimeField(default=now)

    def __str__(self):
        return '%s: %s asked for %s; result %s' % (self.timestamp, self.team, self.puzzle, self.result)

    class Meta:
        unique_together = ('team', 'puzzle', 'question')
        ordering = ['-timestamp']



class ContactRequest(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    contact = models.CharField(max_length=100)
    timestamp = models.DateTimeField(default=now)
    comment = models.CharField(max_length=1000, blank=True)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return '%s: %s wants to talk to HQ' % (self.timestamp, self.team)

    class Meta:
        ordering = ['-timestamp']

class QueueHandler(models.Model):
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100, unique=True)
    activity = models.DateTimeField(default=now)
    team = models.OneToOneField(Team, blank=True, null=True, on_delete=models.CASCADE)
    team_timestamp = models.DateTimeField(blank=True, null=True)
    contact_team = models.OneToOneField(Team, blank=True, null=True, related_name="contact_queuehandler_set", on_delete=models.CASCADE)
    contact_team_timestamp = models.DateTimeField(blank=True, null=True)
    hq_phone = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        status = []
        if self.team:
            status.append('handling %s since %s' % (self.team, self.team_timestamp))
        if self.contact_team:
            status.append('handling contact for %s since %s' % (self.contact_team, self.contact_team_timestamp))
        elif (now() - self.activity).seconds > 5 * 60:
            status.append('off duty')
        else:
            status.append('on duty, idle')
        ret = '\n'.join(status)
        return '%s: %s' % (self.name, ret)

class PuzzleSurvey(models.Model):
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    fun = models.IntegerField(blank=True, null=True)
    difficulty = models.IntegerField(blank=True, null=True)
    comment = models.CharField(max_length=2000, blank=True)
    timestamp = models.DateTimeField(default=now)

    def __str__(self):
        return '%s submitted the survey for %s' % (self.team.name, self.puzzle)

    class Meta:
        ordering = ['timestamp']

class PuzzleSession(models.Model):
    """
    Poor man's session implementation.  Like Django's sessions, but instead of
    storing the session ID in a cookie, must be manually managed by the
    browser and view, e.g. to allow the user to have separate sessions in
    separate browser tabs.
    """

    SESSION_ID_LENGTH = 32
    SESSION_ID_CHARSET = string.ascii_letters + string.digits

    session_id = models.CharField(max_length=SESSION_ID_LENGTH, unique=True, null=False)
    session_data = models.TextField()

    # Not currently used, but could be used for clearing out old, expired
    # sessions, since this table would otherwise grow without bound
    accessed = models.DateTimeField(auto_now=True)

    @classmethod
    def create(clazz):
        session = clazz()
        session.session_id = get_random_string(clazz.SESSION_ID_LENGTH, clazz.SESSION_ID_CHARSET)
        session.session_data = '{}'

        return session


class HQUpdate(models.Model):
    """
    Represent a message from headquarters to all teams. Shows up on an "updates" page as well as going out by
    email
    """

    subject = models.CharField(max_length=200)
    body = models.TextField()
    published = models.BooleanField(default=False)
    creation_time = models.DateTimeField(default=now)
    modification_time = models.DateTimeField(blank=True)
    publish_time = models.DateTimeField(blank=True, null=True)
    team = models.ForeignKey(Team, blank=True, null=True, on_delete=models.SET_NULL)
    puzzle = models.ForeignKey(Puzzle, blank=True, null=True, on_delete=models.CASCADE, verbose_name='Errata for Puzzle')
    send_email = models.BooleanField(default=True)

    def __str__(self):
        return '%s' % (self.subject)

@receiver(pre_save, sender=HQUpdate)
def update_hqupdate_timestamps(sender, **kwargs):
    kwargs['instance'].modification_time = now()

class IncomingMessage(models.Model):
    subject = models.CharField(max_length=200)
    body_text = models.TextField()
    body_html = models.TextField()
    sender = models.CharField(max_length=200)
    recipient = models.CharField(max_length=200)
    received_time = models.DateTimeField(default=now)
    team = models.ForeignKey(Team, blank=True, null=True, on_delete=models.SET_NULL)
    interaction = models.ForeignKey(Interaction, blank=True, null=True, on_delete=models.SET_NULL)
    hidden = models.BooleanField(default=False)

    def __str__(self):
        return '%s from %s' % (self.subject, self.sender)

    class Meta:
        ordering = ['-received_time']

class OutgoingMessage(models.Model):
    subject = models.CharField(max_length=200)
    body = models.TextField()
    sender = models.CharField(max_length=200)
    recipient = models.CharField(max_length=200)
    sent_time = models.DateTimeField(default=now)

    def __str__(self):
        return '%s to %s' % (self.subject, self.recipient)

    class Meta:
        ordering = ['-sent_time']
