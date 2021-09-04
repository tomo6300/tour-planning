from django.shortcuts import render
from django.http import HttpResponse
from . import nn


def index(request):
    return render(request, 'pathfinding/index.html')


def result(request):
    place_list = ["京都駅", "伏見稲荷大社", "金閣寺", "清水寺", "二条城"]  # デフォルト
    if request.method == 'POST':
        departure_destination = request.POST['departure_destination']
        leg1 = request.POST['leg1']
        leg2 = request.POST['leg2']
        leg3 = request.POST['leg3']
        leg4 = request.POST['leg4']
        place_list = [departure_destination, leg1, leg2, leg3, leg4]
    route, time = nn.calc_route(place_list)
    return render(request, 'pathfinding/result.html', {'route': route, 'times': time})
