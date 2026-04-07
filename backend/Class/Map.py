from backend.Class.Obstacles.Obstacle import Obstacle


class Map:
    def __init__(self, width=100, height=100):
        self.width = width
        self.height = height
        self.obstacles = set()
        self.gameMode=None

    def add_obstacle(self, obstacle : Obstacle):
        self.map = self
        self.obstacles.add(obstacle)