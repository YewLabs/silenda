from django.core.cache import cache
import spoilr.signals_register as signals

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

import json

from django_redis import get_redis_connection

def local_unlock_update(team, unlock_id, msg):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("puzzle-updates", {
        "type": "channel.receive_update",
        "unlock_id": unlock_id,
        "team_id": team.y2021teamdata.tempest_id,
        "data": msg
    })

signals.register(signals.unlock_update_message, local_unlock_update)
