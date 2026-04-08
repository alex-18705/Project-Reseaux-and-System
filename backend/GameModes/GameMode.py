from abc import ABC, abstractmethod

from backend.Class.Army import Army
from backend.Class.Map import Map
from frontend.Affichage import Affichage


class GameMode(ABC) :
    def __init__(self):
        self.__army1 = None
        self.__army2 = None
        self.__affichage = None
        self.__map = None
        self.isSave = False

    @abstractmethod
    def launch(self):
        pass

    @abstractmethod
    def gameLoop(self):
        pass

    @abstractmethod
    def save(self):
        pass

    @abstractmethod
    def end(self):
        pass

    @property
    def army1(self):
        pass

    @army1.setter
    def army1(self, value: Army):
        pass

    @property
    def army2(self):
        pass

    @army2.setter
    def army2(self, value: Army):
        pass

    @property
    def map(self):
        return self.__map

    @map.setter
    def map(self, value: Map):
        value.gameMode = self
        self.__map = value

    @property
    def affichage(self):
        return self.__affichage

    @affichage.setter
    def affichage(self, value: Affichage):
        value.gameMode = self
        self.__affichage = value
