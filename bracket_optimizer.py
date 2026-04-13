from collections import defaultdict

import gurobipy as gp
from geopy.distance import geodesic as GD

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
pass

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

# x_a_k == 1 means site k has exactly 1 a-pod
x = dict()
for a in range(len(pods)):
    for k in range(len(locations)):
        x[a, k] = model.addVar(vtype=gp.GRB.BINARY, name=f'x_{a}_{k}')

# y_a_k == 1 means site k has exactly 2 a-pods
y = dict()
for a in range(len(pods)):
    for k in range(len(locations)):
        y[a, k] = model.addVar(vtype=gp.GRB.BINARY, name=f'y_{a}_{k}')

# z_i_k == 1 means team i plays at site k
z = dict()
for i in range(len(schools)):
    for k in range(len(locations)):
        z[i, k] = model.addVar(vtype=gp.GRB.BINARY, name=f'z_{i}_{k}')

# add constraints

# each school plays at exactly 1 site
for i in range(len(schools)):
    model.addConstr(gp.quicksum([z[i, k] for k in range(len(locations))]) == 1)

# each site has exactly 2 pods
for k in range(len(locations)):
    model.addConstr(gp.quicksum([x[a, k] for a in range(len(pods))]) + 2*gp.quicksum([y[a, k] for a in range(len(pods))]) == 2)

# each site/seed combo has the correct number of teams
for k in range(len(locations)):
    for a in range(len(pods)):
        for seed in pods[a]:
            model.addConstr(gp.quicksum([z[i, k] for i, school in enumerate(schools) if school[1] == seed]) - x[a, k] - 2*y[a, k] == 0)

model.setObjective(gp.quicksum([GD((school[2], school[3]), (location[1], location[2])).miles*z[i, k] for i, school in enumerate(schools) for k, location in enumerate(locations)]))

model.optimize()

best_objective = model.ObjVal
variables = [v for v in model.getVars() if v.X==1]
assignments = []
for v in variables:
    if v.VarName.startswith('z_'):
        _, i, k = v.VarName.split('_')
        i, k = int(i), int(k)
        assignments.append([schools[i][0], locations[k][0]])
new_site_map = defaultdict(set)
for school, location in assignments:
    new_site_map[location].add(school)

ratio = best_objective / original_value
pass

