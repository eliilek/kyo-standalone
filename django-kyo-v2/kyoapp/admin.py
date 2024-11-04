from django.contrib import admin
from django.db.models import *
from kyoapp.models import *

class AccessRestrictedModelAdmin(admin.ModelAdmin):
	def save_model(self, request, obj, form, change):
		try:
			if not request.user in form.cleaned_data['allowed_users'].all():
				form.cleaned_data['allowed_users'] = list(form.cleaned_data['allowed_users']) + [request.user,]
			if request.user.groups.count() > 0:
				form.cleaned_data['allowed_groups'] = list(form.cleaned_data['allowed_groups'])
				for group in request.user.groups.all():
					if not group in form.cleaned_data['allowed_groups']:
						form.cleaned_data['allowed_groups'] += [group,]
		except Exception as e:
			print(e)
		super().save_model(request, obj, form, change)

	def changelist_view(self, request, extra_context=None):
		response = super().changelist_view(request, extra_context)
		#Below WORKS! We have access to request.user, if they aren't a superuser remove any where they are not an allowed_user and not in an allowed_group
		#response.context_data['cl'].result_list = response.context_data['cl'].result_list.filter(slug=None)
		if not request.user.is_superuser:
			response.context_data['cl'].result_list = response.context_data['cl'].result_list.filter(Q(allowed_users=request.user) | Q(allowed_groups__in=request.user.groups.all())).distinct()
		response.render()
		return response

	filter_horizontal = ['allowed_users','allowed_groups']

class SingleRuleModificationInline(admin.TabularInline):
	model = SingleRuleModification
	fields = ['parent_rule', 'once_per_player', 'block_end_rule', 'new_player_number', 'new_num_points', 'new_target', 'new_schedule_number']

class IntermediaryRuleInline(admin.TabularInline):
	model = IntermediaryRule
	fields = ['choice',]

class ComboRuleModificationInline(admin.TabularInline):
	model = ComboRuleModification
	fields = ['parent_rule', 'block_end_rule', 'new_num_points', 'new_target', 'new_schedule_number']

class ComboRuleAdmin(AccessRestrictedModelAdmin):
	inlines = [
		IntermediaryRuleInline,
	]

class BlockPlayerInstructionsInline(admin.TabularInline):
	model = BlockPlayerInstructions
	fields = ['block', 'seat_number', 'instructions']

class BlockEndRuleAdmin(AccessRestrictedModelAdmin):
	inlines = [
		SingleRuleModificationInline,
		ComboRuleModificationInline,
	]

class BlockAdmin(AccessRestrictedModelAdmin):
	inlines = [
		BlockPlayerInstructionsInline,
	]

class GameAdmin(AccessRestrictedModelAdmin):
	filter_horizontal = ['choices','points'] + AccessRestrictedModelAdmin.filter_horizontal

class FeedbackModuleAdmin(admin.ModelAdmin):
	fieldsets = [
		(None, {"fields":["name"]}),
		(None, {"fields":["increase_message", "decrease_message"], "description":"You can use the following shortcuts in your feedback messages: {Player} is replaced with the player number who made the choice, or 'the group' for combo rules. {Point} is replaced with the name of the point. {Change} is replaced with the number of points gained or lost."})
	]

# Register your models here.
admin.site.register(Game, GameAdmin)
admin.site.register(Block, BlockAdmin)
admin.site.register(Choice, AccessRestrictedModelAdmin)
admin.site.register(Point, AccessRestrictedModelAdmin)
admin.site.register(SingleRule, AccessRestrictedModelAdmin)
admin.site.register(ComboRule, ComboRuleAdmin)
admin.site.register(BlockEndRule, BlockEndRuleAdmin)
admin.site.register(FeedbackModule, FeedbackModuleAdmin)