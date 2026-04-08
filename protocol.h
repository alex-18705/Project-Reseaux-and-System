#ifndef PROTOCOL_H
#define PROTOCOL_H

/* Structure du paquet de jeu commune à C et Python */
typedef struct {
    int player_id;
    int entity_id;
    int type;    // 1: MOVE, 2: ATTACK, 3: SPAWN
    float x;
    float y;
    int hp;
} GamePacket;

/* Chemins des tubes nommés (FIFOs) dans le système Unix */
#define PIPE_PY_TO_C "/tmp/py_to_c"
#define PIPE_C_TO_PY "/tmp/c_to_py"

#endif