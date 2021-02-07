import json

from channels.generic.websocket import WebsocketConsumer
from spoilr.actions import find_puzzle, solve_puzzle
from spoilr.models import *
from django.urls import reverse
from django.conf import settings

from hunt.actions import get_puzzle, get_puzzle_access, discover_puzzle
import hunt.mmo_unlock as mu

from asgiref.sync import async_to_sync

import logging
logger = logging.getLogger(__name__)

class TempestConsumer(WebsocketConsumer):
    def connect(self):
        self.identity = None
        self.authed = False
        async_to_sync(self.channel_layer.group_add)("puzzle-updates", self.channel_name)
        self.accept()

    def channel_receive_update(self, event):
        if 'unlock_id' in event:
            self.send_to_tempest('UnlockUpdate', event['data'])

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)("puzzle-updates", self.channel_name)

    def send_to_tempest(self, msgType, data):
        '''
        Wrapper method to send dict data to tempest
        '''
        identity = 'Tempest'
        if self.identity:
            identity = self.identity
        logger.info('Send to %s (%s): %s' % (identity, msgType, data))
        self.send(text_data=json.dumps({'MsgType': msgType, 'Data': data}))

    def send_updates(self, updates):
        for u in updates:
            self.channel_receive_update({
                "type": "channel.receive_update",
                "unlock_id": u['unlock'],
                "team_id": u['team'],
                "data": u
            })

    def receive(self, text_data):
        logger.info('Received message: %s' % (text_data))
        text_data_json = json.loads(text_data)
        action = text_data_json['action']
        if action == 'AUTH':
            if text_data_json['auth'] == settings.SECRET_AUTH:
                self.authed = True
                if 'identity' in text_data_json:
                    self.identity = text_data_json['identity']
                self.send_to_tempest('Success', text_data)
            else:
                self.send_to_tempest('Error', text_data + ': Invalid authentication')
        if not self.authed:
            self.send_to_tempest('Error', text_data + ': Requires authentication')
            return
        if action == 'GET_TEAM':
            try:
                team = Team.objects.get(y2021teamdata__auth=text_data_json['auth'])
                self.send_to_tempest('TeamStatus', {'team': team.y2021teamdata.tempest_id, 'auth': team.y2021teamdata.auth})
            except Team.DoesNotExist:
                self.send_to_tempest('TeamStatus', {'team': -1, 'auth': text_data_json['auth']})
        if action == 'GET_UNLOCK_STATE':
            try:
                team = Team.objects.get(y2021teamdata__tempest_id=text_data_json['team'])
            except Team.DoesNotExist:
                self.send_to_tempest('Error', text_data + ': Unknown team \'%s\'' % (text_data_json['team']))
                return
            unlock_id = text_data_json['unlock']
            updates = mu.get_state(team, unlock_id, True)
            self.send_updates(updates)
            if not updates:
                self.send_to_tempest('Error', text_data + ': Unknown unlock \'%s\'' % (unlock_id))
            else:
                self.send_to_tempest('Success', text_data)
        if action == 'GET_UNLOCKS':
            self.send_to_tempest('UnlockList', {'unlocks': mu.get_unlock_list()})
        if action == 'GET_TEAMS':
            teams = []
            for t in Team.objects.select_related('y2021teamdata').all():
                teams.append((t.y2021teamdata.tempest_id, t.y2021teamdata.emoji, t.name))
            self.send_to_tempest('TeamData', {'teams': teams})
        if action == 'DISCOVER_PUZZLE':
            try:
                team = Team.objects.get(y2021teamdata__tempest_id=text_data_json['team'])
            except Team.DoesNotExist:
                self.send_to_tempest('Error', text_data + ': Unknown team \'%s\'' % (text_data_json['team']))
                return
            puzzle = get_puzzle(text_data_json['puzzle'])
            if not discover_puzzle(team, puzzle):
                self.send_to_tempest('Error', text_data + ': Inaccessible Puzzle')
            else:
                mu.get_puzzle_update(team, puzzle)
                self.send_to_tempest('Success', text_data)
