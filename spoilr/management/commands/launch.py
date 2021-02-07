import logging

from django.db import models, transaction
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from spoilr.models import Team
import spoilr.signals as signals

from hunt.models import Y2021Settings
from hunt.mmo_unlock import reset_global_state
from spoilr.actions import set_in_setup, clear_redis

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Launch hunt."""

    @transaction.atomic
    def reset_state(self):
        clear_redis()
        reset_global_state()

    def handle(self, *args, **options):
        set_in_setup()
        self.reset_state()
        teams = Team.objects.all()
        logger.info('Starting hunt for %d teams...', len(teams))
        signals.emit(signals.start_all_message)
        logger.info('Done starting hunt')
        setting = Y2021Settings.objects.get_or_create(name='prelaunched')[0]
        setting.value = 'TRUE'
        setting.save()
        setting = Y2021Settings.objects.get_or_create(name='is_it_hunt_yet')[0]
        setting.value = 'TRUE'
        setting.save()
