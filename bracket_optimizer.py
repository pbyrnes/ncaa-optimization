from collections import defaultdict

import gurobipy as gp
from geopy.distance import geodesic as GD
import plotly.graph_objs as go
import plotly.express as px

schools = []
with open('basketball_data/school_data.txt', 'r') as f:
    lines = f.readlines()
    for line in lines:
        school, seed, lat, long, location = line.split(',')
        schools.append((school, int(seed), float(lat), float(long), location.strip()))

locations = []
with open('basketball_data/location_data.txt', 'r') as f:
    lines = f.readlines()
    for line in lines:
        location, lat, long = line.split(',')
        locations.append((location, float(lat), float(long)))

location_map = {location: (lat, long) for location, lat, long in locations}
schools = [school + location_map[school[-1]] for school in schools]

original_value = sum(GD((school[2], school[3]), (school[-2], school[-1])).miles for school in schools)

model = gp.Model('ncaa_bracket_optimize')
pods = [
    [1, 16, 8, 9],
    [2, 15, 7, 10],
    [3, 14, 6, 11],
    [4, 13, 5, 12],
]

# x_a_k is the number of a-pod's assigned to site k
x = dict()
for a in range(1, len(pods)+1):
    for k in range(1, len(locations)+1):
        x[a, k] = model.addVar(vtype=gp.GRB.INTEGER, lb=0, ub=2, name=f'x_{a}_{k}')

# z_i_k == 1 means team i plays at site k
z = dict()
for i in range(1, len(schools)+1):
    for k in range(1, len(locations)+1):
        z[i, k] = model.addVar(vtype=gp.GRB.BINARY, name=f'z_{i}_{k}')


# add constraints

# each school plays at exactly 1 site
for i in range(1, len(schools)+1):
    model.addConstr(gp.quicksum([z[i, k] for k in range(1, len(locations)+1)]) == 1)

# each site has exactly 2 pods
for k in range(1, len(locations)+1):
    model.addConstr(gp.quicksum([x[a, k] for a in range(1, len(pods)+1)]) == 2)

# each site/seed combo has the correct number of teams
for k in range(1, len(locations)+1):
    for a in range(1, len(pods)+1):
        for seed in pods[a-1]:
            model.addConstr(gp.quicksum([z[i, k] for i, school in enumerate(schools, 1) if school[1] == seed]) - x[a, k] == 0)

model.setObjective(gp.quicksum([GD((school[2], school[3]), (location[1], location[2])).miles*z[i, k] for i, school in enumerate(schools, 1) for k, location in enumerate(locations, 1)]))

model.optimize()

best_objective = model.ObjVal
variables = [v for v in model.getVars() if v.X==1]
assignments = []
for v in variables:
    if v.VarName.startswith('z_'):
        _, i, k = v.VarName.split('_')
        i, k = int(i), int(k)
        assignments.append([schools[i-1][0], locations[k-1][0]])
new_site_map = defaultdict(set)
for school, location in assignments:
    new_site_map[location].add(school)

ratio = best_objective / original_value

for location, _, _ in locations:
    original_teams = sorted(school[0] for school in schools if school[4] == location)
    print(f'{location=}: \noriginal teams {original_teams}\noptimized teams {sorted(new_site_map[location])}')

for location, location_schools in new_site_map.items():
    location_school_tuples = [school for school in schools if school[0] in location_schools]
    lats = [t[2] for t in location_school_tuples]
    lons = [t[3] for t in location_school_tuples]
    texts = [t[0] for t in location_school_tuples]
    fig = go.Figure(data=go.Scattergeo(lon=lons, lat=lats, text=texts, mode='markers', marker_color='red'))
    fig.update_layout(geo_scope='usa')
    # fig.show()
    pass

original_school_distances = {school[0]: GD((school[2], school[3]), (school[-2], school[-1])).miles for school in schools}
new_school_distances = dict()
for location, location_schools in new_site_map.items():
    location_tuple = None
    for location_tuple in locations:
        if location_tuple[0] == location:
            break
    for school in location_schools:
        school_tuple = None
        for school_tuple in schools:
            if school_tuple[0] == school:
                break
        new_distance = GD((school_tuple[2], school_tuple[3]), (location_tuple[-2], location_tuple[-1])).miles
        new_school_distances[school] = new_distance
school_distance_changes = sorted([(school[0], original_school_distances[school[0]], new_school_distances[school[0]], new_school_distances[school[0]]-original_school_distances[school[0]]) for school in schools], key=lambda x: x[3])

fig = px.scatter(x=[s[1] for s in school_distance_changes], y=[s[2] for s in school_distance_changes])
fig.update_xaxes(title_text='Original Distance to Tournament location')
fig.update_yaxes(title_text='Optimized Distance to Tournament location')
max_dist = max(max(s[1], s[2]) for s in school_distance_changes)
fig.add_shape(type='line', line_color='red', line_width=2, x0=0, y0=0, x1=max_dist, y1=max_dist)
fig.write_image('school_distance_changes.png')
best_objective, original_value, ratio


location_colors = px.colors.qualitative.Dark2[:len(locations)]
location_colors = ['red', 'dodgerblue', 'lime', 'magenta', 'goldenrod', 'cyan', 'navy', 'olivedrab']
location_color_map = {location: color for (location, _, _), color in zip(locations, location_colors)}

lats, lons, marker_sizes, marker_colors, marker_symbols = [], [], [], [], []
for location, location_schools in new_site_map.items():
    location_school_tuples = [school for school in schools if school[0] in location_schools]
    location_tuple = None
    for location_tuple in locations:
        if location_tuple[0] == location:
            break
    lats += [t[2] for t in location_school_tuples]
    lats.append(location_tuple[1])
    lons += [t[3] for t in location_school_tuples]
    lons.append(location_tuple[2])
    marker_sizes += [7, ] * len(location_school_tuples) + [12, ]
    marker_colors += [location_color_map[location]] * (len(location_school_tuples) + 1)
    marker_symbols += ['circle', ] * len(location_school_tuples) + ['cross']

fig = go.Figure(data=go.Scattergeo(lon=lons, lat=lats, mode='markers', marker_symbol=marker_symbols, marker_color=marker_colors, marker_size=marker_sizes))
fig.update_layout(geo_scope='usa', width=1600, height=800)
fig.write_image('optimized_2026.png')

lats = [school[2] for school in schools] + [location[1] for location in locations]
lons = [school[3] for school in schools] + [location[2] for location in locations]
marker_sizes = [7, ] * len(schools) + [12, ] * len(locations)
marker_colors = [location_color_map[school[4]] for school in schools] + [location_color_map[location[0]] for location in locations]
marker_symbols = ['circle'] * len(schools) + ['cross'] * len(locations)
fig = go.Figure(data=go.Scattergeo(lon=lons, lat=lats, mode='markers', marker_symbol=marker_symbols, marker_color=marker_colors, marker_size=marker_sizes))
fig.update_layout(geo_scope='usa', width=1600, height=800)
# fig.show()
fig.write_image('original_2026.png')



pass