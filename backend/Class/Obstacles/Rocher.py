from backend.Class.Obstacles.Obstacle import Obstacle


class Rocher(Obstacle) :

    def __init__(self, position : tuple[float],size : float):
        super().__init__(position,size)

