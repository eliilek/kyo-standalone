import json
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from channels.db import database_sync_to_async
from kyoapp.models import *
from django.db.models import Q
from asgiref.sync import async_to_sync

#async def connect(self):
#   self.username = await self.get_name()

#@database_sync_to_async
#def get_name(self):
#    return User.objects.all()[0].name

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.slug = self.scope['url_route']['kwargs']['slug']
        self.room_group_name = 'chat_%s' % self.slug

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        self.user_seat = await database_sync_to_async(self.user_seat)()

        await self.accept()

    def user_seat(self):
        try:
            return self.scope['user'].seatedplayer_set.first().seat
        except:
            return None

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        try:
            target = text_data_json['target']
        except:
            target = "all"
        
        await self.log_message(message, target)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'target': target,
                'sender': self.scope['user'].username
            }
            )

    @database_sync_to_async
    def log_message(self, message, target):
        log = ChatMessage(message=message, sender=self.scope['user'], slug=self.slug, target=target)
        log.save()
        return True

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        target = event['target']
        sender = event['sender']
        # Send message to WebSocket
        try:
            if self.scope['user'].is_superuser or target == "all" or (target != "admin" and ((int(target) == self.user_seat) or (sender == self.scope['user'].username))):
                await self.send(text_data=json.dumps({
                    'message': message
                }))
        except Exception as e:
            print(e)

class SuperConsumer(WebsocketConsumer):
    def connect(self):
        print("Test")
        if self.scope['user'].is_superuser or self.scope['user'].is_staff:
            self.accept()
        else:
            self.close()

    def receive(self, text_data):
        games = Game.objects.filter(finished__isnull=True)
        user = self.scope['user']
        if not user.is_superuser:
            games = games.filter(Q(allowed_users=user) | Q(allowed_groups__in=user.groups.all())).distinct()
        send_list = []
        for game in games:
            send_list.append({'slug':game.slug, 'max_players':game.player_count, 'current_players':game.players.count(), 'name':game.name})
        self.send(json.dumps(send_list))

class MoveConsumer(WebsocketConsumer):
    def connect(self):
        self.slug = self.scope['url_route']['kwargs']['slug']
        self.room_group_name = 'results_%s' % self.slug
        self.user_seat = self.user_seat()

        self.accept()
        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

    def user_seat(self):
        try:
            return self.scope['user'].seatedplayer_set.first().seat
        except:
            return None

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    def receive(self, text_data):
        print(text_data)
        if "error" in text_data:
            user = self.scope['user']
            new_capture = ErrorCapture(user=user, message=text_data['message'], source=text_data['source'], lineno=text_data['lineno'], colno=text_data['colno'], error=text_data['error'])
            new_capture.save()
        elif "refresh_results" in text_data:
            game = Game.objects.get(slug=self.slug)
            cycles = Cycle.objects.filter(block_instance__game=game, complete=True).order_by("-timestamp")
            data_dict = {}
            if cycles.count() > 0:
                last_complete_cycle = cycles[0]
                data_dict['results'] = last_complete_cycle.results_list()
            point_instances = PointInstance.objects.filter(game=game)
            points = {}
            for instance in point_instances:
                points[instance.name()] = instance.value
            data_dict['points'] = points
            if game.latest_cycle().move_set.count() > 0:
                data_dict['current_choices'] = {}
                for move in game.latest_cycle().move_set.all():
                    data_dict['current_choices'][move.seat_number] = move.choice.pk
            try:
                if game.enforce_choice_order and game.latest_cycle().next_seat() == self.user_seat:
                    data_dict['your_move'] = True
            except:
                pass
            if game.manually_stopped:
                data_dict['paused'] = True
            try:
                data_dict['instructions'] = game.current_instructions(self.user_seat)
            except:
                pass
            if game.started:
                data_dict['total_cycle'] = game.total_cycles()
                data_dict['current_cycle'] = game.current_block_cycles()
            self.send(text_data=json.dumps(data_dict))
        elif "start_game" in text_data:
            game = Game.objects.get(slug=self.slug)
            game.start()
        elif "pause_game" in text_data:
            game = Game.objects.get(slug=self.slug)
            game.pause()
        elif "resume_game" in text_data:
            game = Game.objects.get(slug=self.slug)
            game.resume()
        elif "end_game" in text_data or "game_end" in text_data:
            game = Game.objects.get(slug=self.slug)
            game.end()
        else:
            text_data_json = json.loads(text_data)
            try:
                choice = Choice.objects.get(pk=int(text_data_json['choice']))
            except:
                #TODO handle?
                pass
            results = self.log_move(choice)
            if results:
                #Send messages to group
                async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'results',
                    'results': results
                })
                #self.send(text_data=json.dumps({
                #'results': results
                #}))
            else:
                async_to_sync(self.channel_layer.group_send)(
                    self.room_group_name,
                    {
                        'type': 'choice',
                        'choice_pk': choice.pk,
                        'seat': self.user_seat
                    })

    def choice(self, event):
        if self.user_seat and (self.user_seat == int(event['seat']) + 1):
            self.send(text_data=json.dumps({
                    'choice_pk': event['choice_pk'],
                    'seat': event['seat'],
                    'your_move': True
                }))
        else:
            self.send(text_data=json.dumps({
                    'choice_pk': event['choice_pk'],
                    'seat': event['seat']
                }))

    def results(self, event):
        message = event['results']
        game = Game.objects.get(slug=self.slug)
        try:
            instructions = game.current_instructions(self.scope['user'].seatedplayer_set.first().seat)
        except:
            instructions = ""
        try:
            background = game.current_background()
        except:
            background = ""
        to_dump = {'results':message, 'instructions':instructions, 'background':background}
        # Send message to WebSocket
        if self.scope['user'].seatedplayer_set.count() != 0 and self.scope['user'].seatedplayer_set.first().seat == 1:
            to_dump['your_move'] = True
        to_dump['current_cycle'] = game.current_block_cycles()
        to_dump['total_cycle'] = game.total_cycles()
        self.send(text_data=json.dumps(to_dump))

    def game_start(self, event):
        game = Game.objects.get(slug=self.slug)
        try:
            instructions = game.current_instructions(self.scope['user'].seatedplayer_set.first().seat)
        except:
            instructions = ""
        try:
            background = game.current_background()
        except:
            background = ""

        if self.scope['user'].seatedplayer_set.first().seat == 1:
            self.send(text_data=json.dumps({'game_start':True, 'your_move':True, 'instructions':instructions, 'background':background}))
        else:
            self.send(text_data=json.dumps({'game_start':True, 'instructions':instructions, 'background':background}))

    def game_pause(self, event):
        self.send(text_data=json.dumps({'game_pause':True}))

    def game_resume(self, event):
        self.send(text_data=json.dumps({'game_resume':True}))

    def game_end(self, event):
        self.send(text_data=json.dumps({'game_end':True}))

    def log_move(self, choice):
        game = Game.objects.get(slug=self.slug)
        cycle = game.latest_cycle()
        move = Move(choice=choice, player=self.scope['user'], cycle=cycle, seat_number=self.scope['user'].seatedplayer_set.first().seat)
        move.save()

        if cycle.is_complete():
            return cycle.process()
        return None
