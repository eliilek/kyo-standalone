from django.shortcuts import render, redirect, HttpResponse
from kyoapp.models import *
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.core.files.storage import default_storage
import django_rq
from kyoapp.utils import create_csv

# Create your views here.
def index(request):
	if request.user.is_superuser or request.user.is_staff:
		return render(request, "super.html")
	if SeatedPlayer.objects.filter(player=request.user, game__finished__isnull=True).count() != 0:
		seated_object = SeatedPlayer.objects.filter(player=request.user, game__finished__isnull=True)[0]
		return render(request, "game.html", {"game":seated_object.game, "player_seat_num":seated_object.seat, "background":seated_object.game.current_background()})
	return render(request, "lobby.html")

def join(request):
	if not request.method == "POST":
		return redirect("index")
	try:
		game = Game.objects.get(slug=request.POST['slug'])
		if game.finished:
			return render(request, "lobby.html", {"error":True})
	except:
		return render(request, "lobby.html", {"error":True})
	if SeatedPlayer.objects.filter(player=request.user).count() != 0:
		if SeatedPlayer.objects.filter(player=request.user, game__finished__isnull=True).count() == 0:
			for seated in SeatedPlayer.objects.filter(player=request.user):
				seated.delete()
		else:
			return redirect("index")
	try:
		if 'seat' in request.POST and request.POST['seat'] != "":
			game.join(request.user, int(request.POST['seat']))
		else:
			game.join(request.user)
	except:
		return render(request, "lobby.html", {"error":True})
	return redirect("index")

def signup(request):
	if request.method == 'POST':
		form = UserCreationForm(request.POST)
		if form.is_valid():
			form.save()
			username = form.cleaned_data.get('username')
			raw_password = form.cleaned_data.get('password1')
			user = authenticate(username=username, password=raw_password)
			login(request, user)
			return redirect('index')
	else:
		form = UserCreationForm()
	return render(request, 'registration/signup.html', {'form': form})

def download_select(request):
	if not request.user.is_superuser:
		return redirect("index")
	return render(request, 'download_select.html', {"participants":Game.objects.filter(finished__isnull=False)})

def download(request, game_pk):
	if not request.user.is_superuser:
		return redirect("index")
	print("Test")
	try:
		game = Game.objects.get(pk=game_pk)
	except:
		return render(request, "error.html", {"msg":"I couldn't find the game you're looking for."})
	args = {"game_pk":game_pk, "filename":str(timezone.now()).replace(":", "").replace(".", "") + '_game_' + game.slug + ".csv"}
	django_rq.enqueue(create_csv, args)
	new_file = File(name=args['filename'])
	new_file.save()

	return redirect("queued")

def manage_game(request, slug):
	if not request.user.is_superuser:
		return redirect("admin:index")
	try:
		game = Game.objects.get(slug=slug)
	except:
		return render(request, "error.html", {"msg":"I couldn't find the game you're looking for."})
	if game.started:
		return render(request, "manage.html", {"game":game, "total_cycle":game.total_cycles(), "current_cycle":game.current_block_cycles()})
	return render(request, "manage.html", {"game":game})

def queued(request):
	if not request.user.is_superuser:
		return render(request, "error.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or return to the menu."})
	files = File.objects.all()
	args = []
	for file in files:
		#Check if the file exists and is finished
		args.append({'name':file.name, 'created':file.created, 'ready':default_storage.exists(file.name)})
	return render(request, "queued.html", {"files":args})

def retrieve(request, filename):
	if not request.user.is_superuser:
		return render(request, "error.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		file = File.objects.get(name=filename)
	except:
		return render(request, "error.html", {"msg":"I couldn't find the file you're looking for.\nUse the above link to return to the main menu."})
	if not default_storage.exists(filename):
		return redirect("queued")

	retrieved_file = default_storage.open(filename, 'r')

	response = HttpResponse(retrieved_file, content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename=' + filename.replace(" ", "_").replace(",", "_")

	return response

def delete(request, filename):
	if not request.user.is_superuser:
		return render(request, "error.html", {"msg":"You are not authorized to view this page.\nPlease login as a superuser or use the above link to return to the menu."})
	try:
		file = File.objects.get(name=filename)
	except:
		return render(request, "error.html", {"msg":"I couldn't find the file you're looking for.\nUse the above link to return to the main menu."})
	default_storage.delete(filename)
	file.delete()
	return redirect("queued")