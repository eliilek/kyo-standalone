from kyoapp.models import *
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
import datetime
from django.utils import timezone
import csv

def create_csv(args):
	new_file = default_storage.open(args['filename'], 'wb')
	writer = csv.writer(new_file)
	game = Game.objects.get(pk=args['game_pk'])
	writer.writerow([game.name, 'Started: ' + game.started.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y")])
	writer.writerow([])

	#Each block instance
	for block_instance in game.blockinstance_set.all().order_by("created"):
		if block_instance.cycle_set.count() == 0:
			continue
		writer.writerow(['Started: ' + block_instance.created.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), block_instance.block.name, block_instance.cycle_set.count()])
		first = True
		for cycle in block_instance.cycle_set.all().order_by('timestamp'):
			if first:
				first_row = []
			row = []
			for move in cycle.move_set.all().order_by('seat_number'):
				row += [move.choice.name, move.timestamp.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y")]
				if first:
					first_row += ['P' + str(move.seat_number) + " Choice", "Choice Time"]
			final_points = cycle.final_points_list()
			#Point Log Structure - Dict with "individual" dict and "group" dict
			#Individual dict has {name:{seat_number: value}}
			#Group dict has {name:value}
			if final_points:
				for point_name in final_points['individual']:
					#HERE
					for seat_number in final_points['individual'][point_name]:
						if first:
							first_row += [point_name + "-P" + str(seat_number)]
						row += [str(final_points['individual'][point_name][seat_number])]
				row += [cycle.timestamp, cycle.finish_time]
				if first:
					first_row += ["Cycle Start Time", "Cycle End Time"]
					writer.writerow(first_row)
					first = False
			writer.writerow(row)
		writer.writerow([])

	#Chat logs
	writer.writerow(["Chat Logs"])
	messages = ChatMessage.objects.filter(slug=game.slug).order_by('timestamp')
	for message in messages:
		writer.writerow([message.timestamp.astimezone(timezone.get_default_timezone()).strftime("%H:%M:%S %b %d, %Y"), message.sender.username, message.target, message.message])
	new_file.close()
	#Trick git
