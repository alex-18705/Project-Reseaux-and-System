from backend.Class.Obstacles.Obstacle import Obstacle


class Rocher(Obstacle) :

    def __init__(self, positition : tuple[float],size : float):
        super().__init__(positition,size)

