from django.db import models
from django.utils import timezone
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User, Group
import datetime
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.models import CloudinaryField
import string
import random
import json
import re
player_number_pattern = re.compile(r"[pP]?(\d)")
max_pattern = re.compile(r"[Mm][Aa][Xx]:\s*(\w+)")
min_pattern = re.compile(r"[Mm][Ii][Nn]:\s*(\w+)")
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
def id_generator(size=6, chars=string.ascii_letters + string.digits):
	return ''.join(random.choice(chars) for _ in range(size))

# Create your models here.
#class Subject(models.Model):
#	user = models.OneToOneField(User, on_delete=models.CASCADE, editable=False)

#Container for rules governing how feedback should be given in a game
class FeedbackModule(models.Model):
	name = models.CharField(max_length=50)
	increase_message = models.TextField(blank=True)
	decrease_message = models.TextField(blank=True)

	def __str__(self):
		return self.name

	def feedback_message(self, point, player, change):
		try:
			change = int(change)
		except:
			return "ERROR"
		if change > 0:
			message = self.increase_message
		else:
			message = self.decrease_message
		message = message.replace("{Point}", str(point)).replace("{Player}", str(player))
		if change < 0:
			change = change * -1
		message = message.replace("{Change}", str(change))
		return message

class AccessRestrictedModel(models.Model):
	allowed_users = models.ManyToManyField(User, related_name="+", blank=True)
	allowed_groups = models.ManyToManyField(Group, blank=True)

	class Meta:
		abstract = True

#A set of rules to map participant responses to actions
class Block(AccessRestrictedModel):
	name = models.CharField(max_length=100)
	instructions = models.TextField(default="", blank=True)
	background = models.CharField(verbose_name="Background color - accepts javascript keywords or #RRGGBB.", max_length=25, blank=True, default="")
	mute_feedback = models.BooleanField(default=False, verbose_name="Mute all feedback messages for this condition.")
	feedback_module = models.ForeignKey(FeedbackModule, default=None, blank=True, null=True, on_delete=models.SET_NULL)
	min_cycles = models.PositiveSmallIntegerField(verbose_name="Minimum number of cycles before checking any end rules", default=0)

	class Meta:
		verbose_name = "Condition"
		verbose_name_plural = "Conditions"

	def __str__(self):
		return self.name

	def start(self, game, old_instance=None):
		instance = BlockInstance(block=self, game=game)
		instance.save()
		if old_instance:
			for rule_instance in old_instance.ruleinstance_set.all():
				rule_instance.block_instance = instance
				rule_instance.save()
		else:
				instance.start()
		return instance

	def block_instructions(self, seat_number=None):
		if seat_number:
			try:
				spec = self.blockplayerinstructions_set.get(seat_number=seat_number)
				return spec.instructions
			except:
				pass
		if self.instructions != "":
			return self.instructions
		raise Exception("No block instructions")

	def block_background(self):
		if self.background != "":
			return self.background
		raise Exception("No block background")

#Significantly simpler execution if block instance only goes through once
#Restarting should just create another block instance with updated rules
#Look at current app usage, do we need to worry about memory? We do not
class BlockInstance(models.Model):
	block = models.ForeignKey(Block, on_delete=models.CASCADE)
	game = models.ForeignKey('Game', on_delete=models.CASCADE)
	created = models.DateTimeField(auto_now_add=True)
	elapsed_cycles = models.PositiveSmallIntegerField(default=0, editable=False)

	class Meta:
		verbose_name = "Condition Instance"
		verbose_name_plural = "Condition Instances"

	def start(self):
		for rule in self.block.singlerule_set.all():
			rule.instantiate(self)
		for rule in self.block.comborule_set.all():
			rule.instantiate(self)

	def previous_20_cycles(self):
		if self.elapsed_cycles < 20:
			return False
		return self.cycle_set.filter(processed=True).order_by("-finish_time")[:20]

	#Returns dict
	def ended(self):
		if self.elapsed_cycles < self.block.min_cycles:
			return False
		for rule in self.block.blockendrule_set.filter(max_cycles=0):
			if rule.rule_met(self):
				return rule.rule_met(self)
		try:
			temp = self.block.blockendrule_set.get(max_cycles__gt=0)
			if temp.rule_met(self):
				return temp.rule_met(self)
		except:
			pass
		return False

	#def __str__(self):
		#hash to differentiate same block different rules
		#return self.
		#Actually I don't think we need to do that at all

class Point(AccessRestrictedModel):
	name = models.CharField(max_length=100, unique=True, verbose_name="Name (Please don't name anything just 'points', it will break things.)")
	display_name = models.CharField(max_length=100, blank=True, verbose_name="Display Name (Leave blank if same as name)")
	individual = models.BooleanField(default=False, blank=True, verbose_name="Individual Points (if not defaults to group/shared)")
	hidden = models.BooleanField(default=False, blank=True, verbose_name="Hidden (allows points/counters for logic the players can't see)")
	starting_value = models.SmallIntegerField(default=0, blank=True, verbose_name="Starting Value (0 if not specified)")

	def __str__(self):
		return self.name.replace(" ", "-")

	def display(self):
		if self.display_name != "":
			return self.display_name
		return self.name

class Choice(AccessRestrictedModel):
	name = models.CharField(max_length=100)
	image = CloudinaryField('image')

	def __str__(self):
		return self.name

class Game(AccessRestrictedModel):
	name = models.CharField(max_length=100)
	slug = models.CharField(max_length=6, verbose_name="Code participants will use to join (5 characters max)", unique=True)
	player_count = models.PositiveSmallIntegerField()
	players = models.ManyToManyField(User, editable=False, through="SeatedPlayer")
	previous_cycle_displayed = models.BooleanField(default=False, blank=True, verbose_name="Display the previous cycle choices")
	current_cycle_displayed = models.BooleanField(default=False, blank=True, verbose_name="Display the current cycle choices of other players")
	enforce_choice_order = models.BooleanField(default=False, blank=True, verbose_name="Participants choose sequentially (if unselected, everyone can register choices simultaneously)")
	chat = models.BooleanField(default=True, blank=True, verbose_name="Chat client enabled")
	show_others_points = models.BooleanField(default=False, blank=True, verbose_name="Show all player's points to everyone (uncheck to see only your points and group points)")
	points = models.ManyToManyField(Point, blank=True)
	choices = models.ManyToManyField(Choice)
	started = models.DateTimeField(null=True, editable=False)
	finished = models.DateTimeField(null=True, editable=False)
	manually_stopped = models.BooleanField(default=False, editable=False)
	starting_block = models.ForeignKey(Block, on_delete=models.CASCADE, verbose_name="Starting Condition")
	current_block_instance = models.ForeignKey(BlockInstance, blank=True, null=True, on_delete=models.SET_NULL, editable=False, related_name="current_block_instance")
	#current_block_order = models.PositiveSmallIntegerField(editable=False, default=0)
	instructions = models.TextField(default="You and others will play a game to earn points in this experiment. During the game, you will be asked to make choices that will give a certain amount of points to either other players or to yourself. You can play however you want to play this game. You will receive additional instructions throughout the game from the experimenter. The game will take approximately two hours to complete. We will let you know when the experiment is over. At the end of the experiment, your points will be exchanged for money (1 pt = 1 cent).")
	background = models.CharField(verbose_name="Background color - accepts javascript keywords or #RRGGBB. This is overridden by a specific color for a block.", max_length=25, blank=True, default="white")
	mute_feedback = models.BooleanField(default=False, verbose_name="Mute all feedback messages for this game")
	feedback_module = models.ForeignKey(FeedbackModule, on_delete=models.SET_NULL, null=True, blank=True, default=None)

	def __str__(self):
		return self.name + " - " + self.slug

	def debug_restart(self):
		for block_instance in BlockInstance.objects.filter(game=self):
			block_instance.delete()
		for instance in PointInstance.objects.filter(game=self):
			instance.delete()
		self.started = None
		self.finished = None
		self.manually_stopped = False
		self.current_block_instance = None
		self.save()

	def start(self):
		if self.players.count() != self.player_count:
			return False
		self.started = timezone.now()
		for point in self.points.all():
			if point.individual:
				for seated_player in self.seatedplayer_set.all():
					#point_instance = PointInstance(game=self, player=player, point=point, value=point.starting_value)
					point_instance = PointInstance(game=self, seat_number=seated_player.seat, point=point, value=point.starting_value)
					point_instance.save()
			else:
				point_instance = PointInstance(game=self, point=point, value=point.starting_value)
				point_instance.save()
		#self.current_block_order = 0
		self.current_block_instance = self.starting_block.start(self)
		self.save()
		new_cycle = Cycle(block_instance=self.current_block_instance)
		new_cycle.save()
		channel_layer = get_channel_layer()
		async_to_sync(channel_layer.group_send)("results_" + self.slug, {"type": "game_start"})

	def pause(self):
		if self.manually_stopped:
			return False
		channel_layer = get_channel_layer()
		self.manually_stopped = True
		self.save()
		async_to_sync(channel_layer.group_send)("results_" + self.slug, {"type": "game_pause"})

	def resume(self):
		if self.manually_stopped:
			channel_layer = get_channel_layer()
			self.manually_stopped = False
			self.save()
			async_to_sync(channel_layer.group_send)("results_" + self.slug, {"type": "game_resume"})

	def end(self):
		channel_layer = get_channel_layer()
		if not self.finished:
			self.finished = timezone.now()
			self.save()
		for seated in SeatedPlayer.objects.filter(game=self):
			seated.delete()
		async_to_sync(channel_layer.group_send)("results_" + self.slug, {"type": "game_end"})

	def join(self, player, seat=None):
		if seat == None or seat <= 0 or SeatedPlayer.objects.filter(game=self, seat=seat).count() != 0:
			possible_seats = [num + 1 for num in range(self.player_count)]
			for seat in [seatedplayer.seat for seatedplayer in self.seatedplayer_set.all()]:
				if seat in possible_seats:
					possible_seats.remove(seat)
			seat = min(possible_seats)
		seatedplayer = SeatedPlayer(player=player, seat=seat, game=self)
		seatedplayer.save()

	def latest_cycle(self):
		return Cycle.objects.filter(block_instance__game=self).order_by('-timestamp')[0]

	def current_instructions(self, seat_number):
		if self.started:
			try:
				return self.current_block_instance.block.block_instructions(seat_number)
			except:
				pass
		return self.instructions

	def current_background(self):
		if self.started:
			try:
				background = self.current_block_instance.block.block_background()
			except:
				background = self.background
		else:
			background = self.background
		if background == "":
			return "white"
		return background

	def next_block(self, block, hard_refresh):
		if hard_refresh:
			for rule_instance in self.current_block_instance.ruleinstance_set.all():
				rule_instance.delete()
			try:
				self.current_block_instance = block.start(self)
			except:
				self.current_block_instance = Block.objects.get(pk=block).start(self)
		else:
			old_instance = self.current_block_instance
			try:
				self.current_block_instance = block.start(self, old_instance)
			except:
				self.current_block_instance = Block.objects.get(pk=block).start(self, old_instance)
		self.save()
		return self.current_block_instance

	def total_cycles(self):
		return Cycle.objects.filter(block_instance__game=self).count()

	def current_block_cycles(self):
		return Cycle.objects.filter(block_instance=self.current_block_instance).count()

class PointInstance(models.Model):
	game = models.ForeignKey(Game, on_delete=models.CASCADE)
	#player = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
	point = models.ForeignKey(Point, on_delete=models.CASCADE)
	value = models.SmallIntegerField(default=0)
	seat_number = models.PositiveSmallIntegerField(null=True)

	def name(self):
		if self.point.individual:
			return str(self.seat_number) + "-" + str(self.point)
		return str(self.point)

	def display(self):
		if self.point.individual:
			return "P" + str(self.seat_number) + " " + self.point.display()
		return self.point.display()

class SeatedPlayer(models.Model):
	player = models.ForeignKey(User, on_delete=models.CASCADE)
	game = models.ForeignKey(Game, on_delete=models.CASCADE)
	seat = models.PositiveSmallIntegerField()

#Block can no longer have max cycles, where would it go?
#EndRule needs to have points optional, if no associated point assume it's default
class BlockEndRule(AccessRestrictedModel):
	name = models.CharField(max_length=100, blank=True, default="")
	block = models.ForeignKey(Block, on_delete=models.CASCADE, related_name="blockendrule_set")
	min_cycles = models.PositiveSmallIntegerField(verbose_name="Minimum number of cycles before checking, if greater than condition's minimum cycles", default=0, blank=True)
	max_cycles = models.PositiveSmallIntegerField(verbose_name="Maximum number of cycles before next condition (Only use for default)", default=0, blank=True)
	next_block = models.ForeignKey(Block, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Next Condition - Leave blank to repeat this block or end the game", related_name="next_block")
	end_game_after_block = models.BooleanField(default=False, verbose_name="End the game after this condition if this rule is met?")
	point = models.ForeignKey(Point, on_delete=models.CASCADE, null=True, blank=True)
	point_min_value = models.SmallIntegerField(verbose_name="Trigger the next condition if points below: ", null=True, blank=True)
	point_max_value = models.SmallIntegerField(verbose_name="Trigger the next condition if points above: ", null=True, blank=True)
	stable_lookback_pattern = models.BooleanField(default=False, verbose_name="Trigger if the same choices have been made for 80% of previous 20 cycles")
	stable_lookback_points = models.BooleanField(default=False, verbose_name="Trigger if the same player has had the most points for 80% of previous 20 cycles")

	def __str__(self):
		if self.name:
			return self.name
		return "Condition End Rule (" + str(self.pk) + ")"

	def return_dict(self):
		if self.end_game_after_block:
			return_dict = {"destination":None}
		elif self.next_block:
			return_dict = {"destination":self.next_block, "hard_refresh":True}
		else:
			return_dict = {"destination":self.block, "hard_refresh":False}
		return_dict['single_rule_modifications'] = self.singlerulemodification_set.all()
		return_dict['combo_rule_modifications'] = self.comborulemodification_set.all()
		return return_dict

	def rule_met(self, block_instance):
		try:
			block_instance = BlockInstance.objects.get(pk=block_instance)
		except:
			pass
		if self.max_cycles > 0 and block_instance.elapsed_cycles >= self.max_cycles:
			return self.return_dict()
		if self.min_cycles > 0 and block_instance.elapsed_cycles < self.min_cycles:
			return False
		#80% of 20 is 16
		if self.stable_lookback_pattern:
			temp = block_instance.previous_20_cycles()
			if temp:
				patterns = {}
				for cycle in temp:
					pattern = cycle.pattern()
					if pattern in patterns:
						patterns[pattern] += 1
					else:
						patterns[pattern] = 1
				for key in patterns:
					if patterns[key] >= 16:
						return self.return_dict()
		if self.stable_lookback_points:
			temp = block_instance.previous_20_cycles()
			if temp:
				max_point_seats = {}
				for cycle in temp:
					max_point_seat = cycle.max_point_seat(self.point)
					print(max_point_seat)
					if not max_point_seat:
						continue
					if max_point_seat in max_point_seats:
						max_point_seats[max_point_seat] += 1
					else:
						max_point_seats[max_point_seat] = 1
				for key in max_point_seats:
					if max_point_seats[key] >= 16:
						return self.return_dict()
		point_instances = PointInstance.objects.filter(game=block_instance.game, point=self.point)
		if point_instances.count() == 0:
			return False
		for point_instance in point_instances:
			if self.point_max_value and point_instance.value > self.point_max_value:
				#Return dict, rule mods
				return self.return_dict()
			if self.point_min_value and point_instance.value < self.point_min_value:
				#Return dict, rule mods
				return self.return_dict()
		return False

	class Meta:
		verbose_name = "Condition End Rule"
		verbose_name_plural = "Condition End Rules"

class BlockPlayerInstructions(AccessRestrictedModel):
	block = models.ForeignKey(Block, on_delete=models.CASCADE)
	seat_number = models.PositiveSmallIntegerField()
	instructions = models.TextField(default="", blank=True)

	class Meta:
		verbose_name = "Player Specific Instructions"
		verbose_name_plural = "Player Specific Instructions"

class RuleInstance(models.Model):
	single_rule = models.ForeignKey('SingleRule', on_delete=models.CASCADE, null=True)
	combo_rule = models.ForeignKey('ComboRule', on_delete=models.CASCADE, null=True)
	player_number = models.PositiveSmallIntegerField(default=0)
	num_points = models.SmallIntegerField()
	target = models.CharField(max_length=5)
	schedule_number = models.PositiveSmallIntegerField(default=1)
	ratio_delay_number = models.PositiveSmallIntegerField(null=True)
	interval_next_trigger_time = models.DateTimeField(null=True)
	block_instance = models.ForeignKey(BlockInstance, on_delete=models.CASCADE)

	def __str__(self):
		if self.single_rule:
			return str(self.single_rule)
		if self.combo_rule:
			return str(self.combo_rule)
		return "ERROR"
	
	def feedback(self, game, player, point, change):
		if self.single_rule:
			return self.single_rule.feedback(game=game, player=player, point=point, change=change)
		if self.combo_rule:
			return self.combo_rule.feedback(game=game, player=player, point=point, change=change)
		return "ERROR"

	def refresh(self):
		self.ratio_delay_number = None
		self.interval_next_trigger_time = None
		if self.single_rule:
			rule = self.single_rule
		elif self.combo_rule:
			rule = self.combo_rule
		else:
			return "ERROR"
		#TODO Check if this is correct or it should always fire once before adding delay.
		if rule.schedule == "FI":
			self.interval_next_trigger_time = timezone.now() + datetime.timedelta(seconds=self.schedule_number)
		elif rule.schedule == "VI":
			random_bound = max(15, int(self.schedule_number / 6))
			self.interval_next_trigger_time = timezone.now() + datetime.timedelta(seconds=random.randint(self.schedule_number - random_bound, self.schedule_number + random_bound))
		elif rule.schedule == "FR":
			self.ratio_delay_number = self.schedule_number
		else:
			random_bound = min(5, self.schedule_number - 1)
			self.ratio_delay_number = random.randint(self.schedule_number - random_bound, self.schedule_number + random_bound)
		self.save()
		return None

	def trigger(self):
		if self.single_rule:
			rule = self.single_rule
		elif self.combo_rule:
			rule = self.combo_rule
		else:
			return "ERROR"
		if rule.schedule == "FI":
			if timezone.now() >= self.interval_next_trigger_time:
				#Set up next time
				self.interval_next_trigger_time = timezone.now() + datetime.timedelta(seconds = self.schedule_number)
				self.save()
				return True
			return False
		elif rule.schedule == "VI":
			if timezone.now() >= self.interval_next_trigger_time:
				#Set up next time
				random_bound = max(15, int(self.schedule_number / 6))
				self.interval_next_trigger_time = timezone.now() + datetime.timedelta(seconds=random.randint(self.schedule_number - random_bound, self.schedule_number + random_bound))
				self.save()
				return True
			return False
		elif rule.schedule == "FR":
			if self.ratio_delay_number == 1:
				#Reset ratio delay number
				self.ratio_delay_number = self.schedule_number
				self.save()
				return True
			self.ratio_delay_number -= 1
			self.save()
			return False
		else:
			if self.ratio_delay_number == 1:
				#Reset ratio delay number
				random_bound = min(5, self.schedule_number - 1)
				self.ratio_delay_number = random.randint(self.schedule_number - random_bound, self.schedule_number + random_bound)
				self.save()
				return True
			self.ratio_delay_number -= 1
			self.save()
			return False

	def real_target(self, seat_number, player_count):
		if self.target == "" or self.target == "0":
			return seat_number
		try:
			if "+" in self.target:
				add_amount = int(self.target.replace("+", ""))
				new_target = seat_number + add_amount
				if new_target > player_count:
					return (new_target % player_count if new_target % player_count else player_count)
				return new_target
			elif "-" in self.target:
				sub_amount = int(self.target.replace("-", ""))
				new_target = seat_number - sub_amount
				if new_target <= 0:
					return new_target + player_count
				return new_target
			else:
				return int(self.target)
		except:
			#TODO handle
			return None

	def compare_choices(self, choices):
		if self.combo_rule:
			temp = self.combo_rule.compare_choices(choices)
			if temp:
				return self.trigger()
		return False

class SingleRule(AccessRestrictedModel):
	block = models.ForeignKey(Block, on_delete=models.CASCADE, verbose_name="Condition")
	choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
	point = models.ForeignKey(Point, on_delete=models.CASCADE)
	name = models.CharField(blank=True, max_length=200)
	player_number = models.PositiveSmallIntegerField(verbose_name="Player Number this rule applies to. If 0, applies to all players.", default=0)
	num_points = models.SmallIntegerField(verbose_name="Number of points to add. Can be negative to subtract points.")
	target = models.CharField(blank=True, max_length=5, verbose_name="Which player's points should be affected? Numbers indicate a seat, '+1' or '-1' indicate the player 1 seat to the right or left. Leave blank for group points or to indicate the player themselves.")
	schedule = models.CharField(max_length=2, choices=[("FR", "FR"), ("VR", "VR"), ("FI", "FI"), ("VI", "VI")], default="FR")
	schedule_number = models.PositiveSmallIntegerField(verbose_name="Schedule Number (indicates times for Ratio schedule, indicates seconds for Interval schedule", default=1)
	mute_feedback = models.BooleanField(default=False, verbose_name="Mute feedback messages from this rule")
	feedback_module = models.ForeignKey(FeedbackModule, default=None, blank=True, null=True, on_delete=models.SET_NULL)

	def __str__(self):
		if self.name:
			return self.name + " - " + str(self.block)
		return "Single Rule " + str(self.pk)

	def instantiate(self, block_instance):
		for seated_player in block_instance.game.seatedplayer_set.all():
			new_instance = RuleInstance(single_rule=self,
										player_number=seated_player.seat,
										num_points=self.num_points,
										target=self.target,
										schedule_number=self.schedule_number,
										block_instance=block_instance)
			new_instance.save()
			if new_instance.refresh():
				#TODO Handle/report error
				pass

	def feedback(self, game, player, point, change):
		if self.mute_feedback:
			return False
		if self.block.mute_feedback:
			return False
		if game.mute_feedback:
			return False
		if self.feedback_module:
			return self.feedback_module.feedback_message(player=player, point=point, change=change)
		elif self.block.feedback_module:
			return self.block.feedback_module.feedback_message(player=player, point=point, change=change)
		elif game.feedback_module:
			return game.feedback_module.feedback_message(player=player, point=point, change=change)
		return True

	#Should only be called for individ points
	def real_target(self, seat_number, player_count):
		#Self
		if self.target == "" or self.target == "0":
			return seat_number
		try:
			if "+" in self.target:
				add_amount = int(self.target.replace("+", ""))
				new_target = seat_number + add_amount
				if new_target > player_count:
					return (new_target % player_count if new_target % player_count else player_count)
				return new_target
			elif "-" in self.target:
				sub_amount = int(self.target.replace("-", ""))
				new_target = seat_number - sub_amount
				if new_target <= 0:
					return new_target + player_count
				return new_target
			else:
				return int(self.target)
		except:
			#TODO Handle
			return None

class SingleRuleModification(AccessRestrictedModel):
	parent_rule = models.ForeignKey(SingleRule, on_delete=models.CASCADE)
	block_end_rule = models.ForeignKey(BlockEndRule, on_delete=models.CASCADE, verbose_name="Condition End Rule where we apply this modification")
	#Does this make sense? How to indicate "Most Points" or w/e
	new_player_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="New Player Number - leave blank if not changing/applies to everyone. If you specify a player for a rule that applies to everyone, it will only change for that player. 'max:point_name','min:point_name' are supported.")
	new_num_points = models.CharField(max_length=10, verbose_name="New Num Points - leave blank if not changed, supports '+:5' or '-:5' to adjust previous value up or down", blank=True)
	new_target = models.CharField(max_length=5, blank=True)
	new_schedule_number = models.CharField(max_length=10, verbose_name="New schedule number - leave blank if not changed, supports '+:5' or '-:5'", blank=True)
	once_per_player = models.BooleanField(verbose_name="Can only apply once per player", default=False)

	#For each rule instance with appropriate parent rule, checks if it can/should apply
	def apply(self, game):
		parent_instance_filter = RuleInstance.objects.filter(single_rule=self.parent_rule)
		if self.new_player_number:
			try:
				clean_new_player_number = int(self.new_player_number)
			except:
				if player_number_pattern.match(self.new_player_number):
					clean_new_player_number = int(player_number_pattern.match(self.new_player_number).group(1))
				elif max_pattern.match(self.new_player_number):
					maxed_point = max_pattern.match(self.new_player_number).group(1)
					point_instances = PointInstance.objects.filter(point__name=maxed_point, game=game)
					if self.once_per_player:
						seat_numbers = []
						for instance in self.singlerulemodificationinstance_set.all():
							seat_numbers.append(instance.seat_number)
						point_instances = point_instances.exclude(seat_number__in=seat_numbers)
					max_instance = point_instances.order_by('-value').first()
					clean_new_player_number = max_instance.seat_number
				elif min_pattern.match(self.new_player_number):
					mined_point = min_pattern.match(self.new_player_number).group(1)
					point_instances = PointInstance.objects.filter(point__name=mined_point, game=game)
					if self.once_per_player:
						seat_numbers = []
						for instance in self.singlerulemodificationinstance_set.all():
							seat_numbers.append(instance.seat_number)
						point_instances = point_instances.exclude(seat_number__in=seat_numbers)
					min_instance = point_instances.order_by('value').first()
					clean_new_player_number = min_instance.seat_number
				else:
					clean_new_player_number = None
		else:
			clean_new_player_number = None

		for rule_instance in parent_instance_filter:
			if clean_new_player_number and rule_instance.player_number != clean_new_player_number:
				continue
			#Doesn't conflict with seat number, should apply
			if self.new_num_points:
				if "+:" in self.new_num_points:
					rule_instance.num_points = rule_instance.num_points + int(self.new_num_points.replace("+:",""))
				elif "-:" in self.new_num_points:
					rule_instance.num_points = rule_instance.num_points - int(self.new_num_points.replace("-:",""))
				else:
					rule_instance.num_points = int(self.new_num_points)
			if self.new_target:
				rule_instance.target = self.new_target
			if self.new_schedule_number:
				if "+:" in self.new_schedule_number:
					rule_instance.schedule_number = rule_instance.schedule_number + int(self.new_schedule_number.replace("+:",""))
				elif "-:" in self.new_schedule_number:
					rule_instance.schedule_number = rule_instance.schedule_number - int(self.new_schedule_number.replace("-:",""))
				else:
					rule_instance.schedule_number = int(self.new_schedule_number)
			rule_instance.save()
			if self.once_per_player:
				new_instance = SingleRuleModificationInstance(modification=self, rule_instance=rule_instance, seat_number=rule_instance.player_number)
				new_instance.save()

class SingleRuleModificationInstance(models.Model):
	modification = models.ForeignKey(SingleRuleModification, on_delete=models.CASCADE)
	rule_instance = models.ForeignKey(RuleInstance, on_delete=models.CASCADE)
	seat_number = models.PositiveSmallIntegerField()

class ComboRule(AccessRestrictedModel):
	block = models.ForeignKey(Block, on_delete=models.CASCADE)
	choices = models.ManyToManyField(Choice, through="IntermediaryRule")
	point = models.ForeignKey(Point, on_delete=models.CASCADE)
	num_points = models.SmallIntegerField(verbose_name="Number of points to add. Can be negative to subtract points.")
	target = models.CharField(editable=False, default="", blank=True, max_length=5, verbose_name="Which player's points should be affected? Numbers indicate a seat, '+1' or '-1' indicate the player 1 seat to the right or left. Leave blank for group points or to indicate the player themselves.")
	schedule = models.CharField(max_length=2, choices=[("FR", "FR"), ("VR", "VR"), ("FI", "FI"), ("VI", "VI")], default="FR")
	schedule_number = models.PositiveSmallIntegerField(verbose_name="Schedule Number (indicates times for Ratio schedule, indicates seconds for Interval schedule", default=1)
	name = models.CharField(max_length=200, blank=True)
	ratio_delay_number = models.PositiveSmallIntegerField(editable=False, null=True)
	interval_next_trigger_time = models.DateTimeField(editable=False, null=True)
	mute_feedback = models.BooleanField(default=False, verbose_name="Mute feedback messages from this rule")
	feedback_module = models.ForeignKey(FeedbackModule, default=None, blank=True, null=True, on_delete=models.SET_NULL)

	def __str__(self):
		if self.name:
			return self.name
		return "Combo Rule " + str(self.pk)

	def instantiate(self, block_instance):
		new_instance = RuleInstance(combo_rule=self,
									num_points=self.num_points,
									target=self.target,
									schedule_number=self.schedule_number,
									block_instance=block_instance)
		new_instance.save()
		if new_instance.refresh():
			#TODO Handle/log error
			pass

	def feedback(self, game, player, point, change):
		if self.mute_feedback:
			return False
		if self.block.mute_feedback:
			return False
		if game.mute_feedback:
			return False
		if self.feedback_module:
			return self.feedback_module.feedback_message(player=player, point=point, change=change)
		elif self.block.feedback_module:
			return self.block.feedback_module.feedback_message(player=player, point=point, change=change)
		elif game.feedback_module:
			return game.feedback_module.feedback_message(player=player, point=point, change=change)
		return True

	#Should only be called for individ points
	def real_target(self, seat_number, player_count):
		#Self
		if self.target == "" or self.target == "0":
			return seat_number
		try:
			return_target = int(self.target)
			return return_target
		except:
			pass
		try:
			if "+" in self.target:
				add_amount = int(self.target.replace("+", ""))
				new_target = seat_number + add_amount
				if new_target > player_count:
					return (new_target % player_count if new_target % player_count else player_count)
				return new_target
			else:
				sub_amount = int(self.target.replace("-", ""))
				new_target = seat_number - sub_amount
				if new_target >= 0:
					return new_target + player_count
				return new_target
		except:
			#TODO Handle
			return None

	#Expects a list of choice PKs
	def compare_choices(self, choices):
		local_choices = []
		for choice in self.choices.all():
			if choice.pk in choices:
				choices.remove(choice.pk)
			else:
				return False
		return True

class ComboRuleModification(AccessRestrictedModel):
	parent_rule = models.ForeignKey(ComboRule, on_delete=models.CASCADE)
	block_end_rule = models.ForeignKey(BlockEndRule, on_delete=models.CASCADE)
	new_num_points = models.CharField(max_length=10, verbose_name="New Num Points - leave blank if not changed, supports '+:5' or '-:5'", blank=True)
	new_target = models.CharField(max_length=5, blank=True)
	new_schedule_number = models.CharField(max_length=10, verbose_name="New schedule number - leave blank if not changed, supports '+:5' or '-:5'", blank=True)

	def apply(self, game):
		parent_instance_filter = RuleInstance.objects.filter(combo_rule=self.parent_rule)

		for rule_instance in parent_instance_filter:
			if self.new_num_points:
				if "+:" in self.new_num_points:
					rule_instance.num_points = rule_instance.num_points + int(self.new_num_points.replace("+:",""))
				elif "-:" in self.new_num_points:
					rule_instance.num_points = rule_instance.num_points - int(self.new_num_points.replace("-:",""))
				else:
					rule_instance.num_points = int(self.new_num_points)
			if self.new_target:
				rule_instance.target = self.new_target
			if self.new_schedule_number:
				if "+:" in self.new_schedule_number:
					rule_instance.schedule_number = rule_instance.schedule_number + int(self.new_schedule_number.replace("+:",""))
				elif "-:" in self.new_schedule_number:
					rule_instance.schedule_number = rule_instance.schedule_number - int(self.new_schedule_number.replace("-:",""))
				else:
					rule_instance.schedule_number = int(self.new_schedule_number)
			rule_instance.save()

class IntermediaryRule(models.Model):
	rule = models.ForeignKey(ComboRule, on_delete=models.CASCADE)
	choice = models.ForeignKey(Choice, on_delete=models.CASCADE)

class ChatMessage(models.Model):
	timestamp = models.DateTimeField(auto_now_add=True)
	message = models.TextField()
	sender = models.ForeignKey(User, on_delete=models.CASCADE)
	slug = models.CharField(max_length=6)
	target = models.CharField(max_length=10, default="all")

class Cycle(models.Model):
	#block = models.ForeignKey(BlockGameOrdering, on_delete=models.CASCADE)
	block_instance = models.ForeignKey(BlockInstance, on_delete=models.CASCADE)
	timestamp = models.DateTimeField(auto_now_add=True)
	finish_time = models.DateTimeField(null=True)
	complete = models.BooleanField(default=False)
	processed = models.BooleanField(default=False)
	results = models.TextField(default="")
	final_points = models.TextField(default="")

	def next_seat(self):
		if self.move_set.count() == 0:
			return 1
		return self.move_set.order_by("-seat_number")[0].seat_number + 1

	def results_list(self):
		if self.results == "":
			return None
		return json.loads(self.results)

	#Point Log Structure - Dict with "individual" dict and "group" dict
	#Individual dict has {name:{seat_number: value}}
	#Group dict has {name:value}
	def final_points_list(self):
		if self.final_points == "":
			return None
		return json.loads(self.final_points)

	def is_complete(self):
		if self.complete:
			return True
		if self.move_set.count() == self.block_instance.game.player_count:
			self.complete=True
			self.finish_time = timezone.now()
			self.save()
			return True
		return False

	def pattern(self):
		result = [None for i in range(self.move_set.count())]
		for move in self.move_set.all().order_by("seat_number"):
			result[move.seat_number-1] = str(move.choice.pk)
		return ",".join(result)

	def max_point_seat(self, point):
		if not self.final_points:
			return None
		point_log = json.loads(self.final_points)
		try:
			if not point.individual:
				return None
			max_points = max(point_log['individual'][point.name].values())
			max_seats = [seat for seat, points in point_log['individual'][point.name].items() if points == max_points]
			if len(max_seats) == 1:
				return max_seats[0]
			return None
			#return max(point_log['individual'][point.name], key=point_log['individual'][point.name].get)
		except Exception as e:
			print(e)
			return None
	#results[point_name] = [(change, source seat), (change, source seat)]
	#results['moves'] = [(choice, seat_number)]
	#comes through to JS as data['results'][blah]

	def process(self):
		if self.processed or not self.is_complete():
			return None
		results = {'moves':[]}
		choices = []
		for move in self.move_set.all():
			results['moves'].append((move.choice.pk, move.seat_number))
			choices.append(move.choice.pk)
			for rule_instance in RuleInstance.objects.filter(block_instance=self.block_instance, single_rule__isnull=False, single_rule__choice=move.choice):
				if rule_instance.player_number != 0 and rule_instance.player_number != move.seat_number:
					continue
				if not rule_instance.trigger():
					continue
				point_instances = PointInstance.objects.filter(game=self.block_instance.game, point=rule_instance.single_rule.point)
				if rule_instance.single_rule.point.individual:
					target_seat = rule_instance.real_target(move.seat_number, self.block_instance.game.player_count)
					point_instance = point_instances.get(seat_number=target_seat)
				else:
					point_instance = point_instances.first()
				if not point_instance.name() in results.keys():
					results[point_instance.name()] = []
				feedback = rule_instance.feedback(game=self.block_instance.game, change=rule_instance.num_points, player="P" + str(move.seat_number), point=point_instance.point.display())
				print(feedback)
				results[point_instance.name()].append((rule_instance.num_points, move.seat_number, feedback))
				point_instance.value += rule_instance.num_points
				point_instance.save()
		for rule_instance in RuleInstance.objects.filter(block_instance=self.block_instance, combo_rule__isnull=False):
			if rule_instance.compare_choices(choices):
				point_instances = PointInstance.objects.filter(game=self.block_instance.game, point=rule_instance.combo_rule.point)
				for point_instance in point_instances:
					if not point_instance.name() in results.keys():
						results[point_instance.name()] = []
					feedback = rule_instance.feedback(game=self.block_instance.game, change=rule_instance.num_points, player="the group", point=point_instance.point.display())
					results[point_instance.name()].append((rule_instance.num_points, "the group", feedback))
					point_instance.value += rule_instance.num_points
					point_instance.save()
		#Point Log Structure - Dict with "individual" dict and "group" dict
		#Individual dict has {name:{seat_number: value}}
		#Group dict has {name:value}
		self.processed = True
		self.results = json.dumps(results)
		point_log = {"individual":{}, "group":{}}
		for point_instance in PointInstance.objects.filter(game=self.block_instance.game):
			if point_instance.point.individual:
				if point_instance.point.name in point_log["individual"]:
					point_log["individual"][point_instance.point.name][point_instance.seat_number] = point_instance.value
				else:
					point_log["individual"][point_instance.point.name] = {point_instance.seat_number: point_instance.value}
			else:
				point_log["group"][point_instance.point.name] = point_instance.value
		self.final_points = json.dumps(point_log)
		self.save()
		self.block_instance.elapsed_cycles += 1
		self.block_instance.save()
		end_dict = self.block_instance.ended()
		if end_dict:
			#This call adjusts game values
			if end_dict['destination'] == None:
				for rule_instance in self.block_instance.ruleinstance_set.all():
					rule_instance.delete()
				results['game_end'] = True
				self.results = json.dumps(results)
				self.save()
				self.block_instance.game.end()
				return results
			next_block_instance = self.block_instance.game.next_block(end_dict['destination'], end_dict['hard_refresh'])
			if not end_dict['hard_refresh']:
				for modification in end_dict['single_rule_modifications']:
					modification.apply(self.block_instance.game)
				for modification in end_dict['combo_rule_modifications']:
					modification.apply(self.block_instance.game)
			new_cycle = Cycle(block_instance=next_block_instance)
		else:
			new_cycle = Cycle(block_instance=self.block_instance)
		new_cycle.save()
		return results

class Move(models.Model):
	timestamp = models.DateTimeField(auto_now_add=True)
	choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
	player = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
	seat_number = models.PositiveSmallIntegerField()
	cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE)

class File(AccessRestrictedModel):
    created = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=200)

class ErrorCapture(models.Model):
	created = models.DateTimeField(auto_now_add=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	message = models.TextField()
	source = models.TextField()
	lineno = models.TextField()
	colno = models.TextField()
	error = models.TextField()