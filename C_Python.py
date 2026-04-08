import struct
import os

# FORMAT : <iiiffi
# < : Little-endian (Standard pour x86/Linux)
# i : int (4 octets)
# f : float (4 octets)
# Structure: player_id, entity_id, type, x, y, hp

FORMAT = "<iiiffi"

def test_send_to_c():
    """
    Simule l'envoi d'un paquet de jeu vers le programme C.
    """
    pipe_path = "/tmp/py_to_c"

    # Vérification si le pipe existe (le programme C doit être lancé avant)
    if not os.path.exists(pipe_path):
        print(f"Erreur : Le tube {pipe_path} n'existe pas.")
        print("Avez-vous lancé le programme C (./test) ?")
        return

    # Données de test : Player 1, Entity 10, Action Move(1), X=15.5, Y=20.0, HP=100
    data = struct.pack(FORMAT, 1, 10, 1, 15.5, 20.0, 100)

    try:
        # Écriture dans le pipe en mode binaire
        with open(pipe_path, "wb") as f:
            f.write(data)
        print("Python : Paquet envoyé avec succès !")
    except Exception as e:
        print(f"Erreur lors de l'envoi : {e}")

if __name__ == "__main__":
    test_send_to_c()