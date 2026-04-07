import heapq
import math



# Utils collision
def collide_circle(p1, r1, p2, r2):
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    return dx*dx + dy*dy <= (r1 + r2)**2


def cell_center(cell, cell_size):
    x, y = cell
    return (x * cell_size + cell_size / 2,
            y * cell_size + cell_size / 2)



# Grille virtuelle
def is_cell_blocked(cell, unit, map, army1, army2, cell_size):
    cx, cy = cell_center(cell, cell_size)

    # Obstacles
    for obs in map.obstacles:
        if collide_circle((cx, cy), unit.size, obs.position, obs.size):
            return True

    # Units (alliées + ennemies)
    for army in (army1, army2):
        for other in army.living_units():
            if other is unit:
                continue
            if collide_circle((cx, cy), unit.size, other.position, other.size):
                return True

    return False



# A* PATHFINDING
def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def neighbors(cell):
    x, y = cell
    return [
        (x+1, y), (x-1, y),
        (x, y+1), (x, y-1)
    ]


def find_path(map, start, goal, unit, army1, army2, cell_size=1.0, max_nodes=20000):
    """
    A* sur grille virtuelle construite depuis obstacles + unités.
    Retourne une liste de positions monde (float, float)
    """

    start_cell = (int(start[0] // cell_size), int(start[1] // cell_size))
    goal_cell  = (int(goal[0] // cell_size),  int(goal[1] // cell_size))

    open_set = []
    heapq.heappush(open_set, (0, start_cell))

    came_from = {}
    g_score = {start_cell: 0}

    explored = 0

    while open_set:
        explored += 1
        if explored > max_nodes:
            return None

        _, current = heapq.heappop(open_set)

        if current == goal_cell:
            # Reconstruction du chemin
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()

            # Convertir en positions monde
            return [cell_center(c, cell_size) for c in path]

        for n in neighbors(current):
            if is_cell_blocked(n, unit, map, army1, army2, cell_size):
                continue

            tentative = g_score[current] + 1

            if n not in g_score or tentative < g_score[n]:
                came_from[n] = current
                g_score[n] = tentative
                f = tentative + heuristic(n, goal_cell)
                heapq.heappush(open_set, (f, n))

    return None