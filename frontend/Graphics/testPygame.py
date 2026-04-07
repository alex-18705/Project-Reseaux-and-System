
import pygame
import sys

from frontend.Graphics.PyScreen import PyScreen

if __name__ == '__main__':
    affichage = PyScreen("pygame_assets/")
    affichage.initialiser()
    # Boucle principale
    while True:
        affichage.afficher(None,None,None)




