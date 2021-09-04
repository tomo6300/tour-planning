import urllib.request, json
import urllib.parse
import itertools
import pandas as pd
from django.conf.locale import nn
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import display
from pandas import DataFrame
import pulp as pp


class GoogleMapAPI:

    def __init__(self, origin,
                 destination,
                 mode="walking",
                 lang="ja",
                 region="ja",
                 units="metric",
                 api_key=""):
        self.origin = origin
        self.destination = destination
        self.request = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&mode={mode}&language={lang}&units={units}&region={region}&key={api_key}"
        self.request = urllib.parse.quote_plus(self.request, safe=':/=&?')

    def get_navigation_information(self):
        response = urllib.request.urlopen(self.request).read()
        directions = json.loads(response)
        origin_coordinate = directions["routes"][0]["legs"][0]["start_location"]
        destination_coordinate = directions["routes"][0]["legs"][0]["end_location"]
        distance = directions["routes"][0]["legs"][0]["distance"]["value"]
        duration = directions["routes"][0]["legs"][0]["duration"]["value"]
        return origin_coordinate, destination_coordinate, distance, duration


class Place:
    def __init__(self, place_list):
        self.place_list = place_list

    def get_place_table(self, save_flag=False):
        place_name_list = list()
        latitude_list = list()
        longitude_list = list()

        for place in self.place_list:
            origin_coordinate, destination_coordinate, distance, duration = GoogleMapAPI(origin=place,
                                                                                         destination=place).get_navigation_information()
            place_name_list.append(place)
            latitude_list.append(round(origin_coordinate["lat"], 2))
            longitude_list.append(round(origin_coordinate["lng"], 2))

        place_table_dict = {"place_name": place_name_list,
                            "latitude": latitude_list,
                            "longitude": longitude_list, }

        place_table_df = pd.DataFrame(place_table_dict)
        if save_flag:
            place_table_df.to_csv("place.csv", index=None, encoding='utf_8_sig')
        return place_table_df


class Route:
    def __init__(self, place_list):
        self.place_list = itertools.combinations(place_list, 2)

    def get_route_table(self, save_flag=False):
        origin_list = list()
        origin_latitude_list = list()
        origin_longitude_list = list()
        destination_list = list()
        destination_latitude_list = list()
        destination_longitude_list = list()
        distance_list = list()
        duration_list = list()

        for origin, destination in self.place_list:
            origin_coordinate, destination_coordinate, distance, duration = GoogleMapAPI(origin=origin,
                                                                                         destination=destination).get_navigation_information()
            origin_list.append(origin)
            origin_latitude_list.append(round(origin_coordinate["lat"], 2))
            origin_longitude_list.append(round(origin_coordinate["lng"], 2))

            destination_list.append(destination)
            destination_latitude_list.append(round(destination_coordinate["lat"], 2))
            destination_longitude_list.append(round(destination_coordinate["lng"], 2))

            distance_list.append(distance)
            duration_list.append(duration)

        route_table_dict = {"origin": origin_list,
                            "origin_latitude": origin_latitude_list,
                            "origin_longitude": origin_longitude_list,
                            "destination": destination_list,
                            "destination_latitude": destination_latitude_list,
                            "destination_longitude": destination_longitude_list,
                            "distance[m]": distance_list,
                            "duration[s]": duration_list}

        route_table_df = pd.DataFrame(route_table_dict)
        if save_flag:
            route_table_df.to_csv("route.csv", index=None, encoding='utf_8_sig')
        return route_table_df


def calc_route(place_list):
    route = Route(place_list)
    df_route = route.get_route_table(save_flag=True)

    place = Place(place_list)
    df_place = place.get_place_table(save_flag=True)

    N = len(place_list)
    c = np.zeros((N, N))
    p = 0
    for i in range(N):
        for j in range(i, N):
            if i != j:
                c[i, j] = df_route['duration[s]'][p]
                c[j, i] = df_route['duration[s]'][p]
                p += 1

    # 最適化モデルの定義
    mip_model = pp.LpProblem("tsp_mip", pp.LpMinimize)

    pd.plotting.register_matplotlib_converters()
    # 変数の定義
    x = pp.LpVariable.dicts('x', ((i, j) for i in range(N) for j in range(N)), lowBound=0, upBound=1, cat='Binary')
    # we need to keep track of the order in the tour to eliminate the possibility of subtours
    u = pp.LpVariable.dicts('u', (i for i in range(N)), lowBound=1, upBound=N, cat='Integer')

    # 評価指標（式（１））の定義＆登録
    objective = pp.lpSum(c[i, j] * x[i, j] for i in range(N) for j in range(N) if i != j)
    mip_model += objective

    # 　条件式(2)の登録
    for i in range(N):
        mip_model += pp.lpSum(x[i, j] for j in range(N) if i != j) == 1

    # 条件式(3)の登録
    for i in range(N):
        mip_model += pp.lpSum(x[j, i] for j in range(N) if i != j) == 1

    # 条件式(4) (MTZ制約)
    for i in range(N):
        for j in range(N):
            if i != j and (i != 0 and j != 0):
                mip_model += u[i] - u[j] <= N * (1 - x[i, j]) - 1

    # 最適化の実行
    status = mip_model.solve()

    routes = [(i, j) for i in range(N) for j in range(N) if pp.value(x[i, j]) == 1]

    def get_places(routes):
        j = 0
        n = len(routes)
        places = [None] * n
        for i in range(n):
            places[i] = df_place.iloc[routes[j][0]]['place_name']
            j = routes[j][1]

        return places

    def get_times(routes):
        n = len(routes)
        times = [None] * n
        for i in range(n):
            df_time = df_route.loc[((df_route['origin'] == df_place.iloc[routes[i][0]]['place_name']) & (
                    df_route['destination'] == df_place.iloc[routes[i][1]]['place_name'])) |
                                   ((df_route['destination'] == df_place.iloc[routes[i][0]]['place_name']) & (
                                           df_route['origin'] == df_place.iloc[routes[i][1]]['place_name']))]
            times[i] = int(df_time.iloc[0]['duration[s]'] / 60)

        return times

    places = get_places(routes)
    times = get_times(routes)

    return places, times
