#include <stdio.h>
#include "ipc.c"

int main() {
    GamePacket pkt;
    
    init_ipc();
    
    //Python -> C
    printf("[C] En attente de Python sur %s...\n", PIPE_PY_TO_C);
    
    // Le programme va s'arrêter ici tant que Python n'envoie rien
    if (read_from_python(&pkt) > 0) {
        printf("\n--- Paquet reçu de Python ---\n");
        printf("ID Joueur : %d | Pos : (%.2f, %.2f) | HP : %d\n", 
                pkt.player_id, pkt.x, pkt.y, pkt.hp);
    }

    //C -> Python
    pkt.player_id = 99; // Changeons l'ID pour différencier la réponse
    pkt.hp = 50;
    printf("[C] Envoi d'une réponse à Python...\n");
    write_to_python(&pkt);


    return 0;
}