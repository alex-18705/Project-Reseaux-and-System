import uuid


class Obstacle :

    def __init__(self, position : tuple[float],size : float):
        self._size = size
        self._position = position
        self.id = str(uuid.uuid4())

        self.map = None

    #this is used to get the size of the obstacle
    @property
    def size(self):
        return self._size

    #this is used to get the position of the obstacle
    @property
    def position(self):
        return self._position
