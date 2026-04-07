# backend/generals.py
from abc import ABC, abstractmethod
from typing import Optional, Tuple


class General(ABC):

    def __init__(self):
        self.army = None

    @abstractmethod
    def getTargets(self, map, otherArmy):
        # C'est ici le la stratégie du générale s'opère, cette fonction ne fait
        # qu'assigner une unité alliée à une unité ennemie selon des critères propres
        pass

