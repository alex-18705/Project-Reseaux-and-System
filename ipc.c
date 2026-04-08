#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include "protocol.h"

/**
 * Initialise les FIFOs pour la communication inter-processus.
 * Création des fichiers spéciaux dans /tmp avec les droits rw-rw-rw-.
 */
void init_ipc() {
    // Suppression au cas où les pipes existent déjà pour éviter les erreurs
    unlink(PIPE_PY_TO_C);
    unlink(PIPE_C_TO_PY);

    if (mkfifo(PIPE_PY_TO_C, 0666) == -1 || mkfifo(PIPE_C_TO_PY, 0666) == -1) {
        perror("[IPC] Erreur lors de la création des FIFOs");
        exit(EXIT_FAILURE);
    }
    printf("[IPC] FIFOs créés avec succès dans /tmp\n");
}

/**
 * Lit un paquet envoyé par le script Python.
 * Cette fonction est BLOQUANTE jusqu'à ce que Python écrive.
 */
int read_from_python(GamePacket *packet) {
    int fd = open(PIPE_PY_TO_C, O_RDONLY);
    if (fd < 0) return -1;

    int bytes_read = read(fd, packet, sizeof(GamePacket));
    
    close(fd);
    return bytes_read;
}

/**
 * Envoie un paquet vers le script Python.
 */
int write_to_python(GamePacket *packet) {
    int fd = open(PIPE_C_TO_PY, O_WRONLY);
    if (fd < 0) return -1;

    int bytes_written = write(fd, packet, sizeof(GamePacket));
    
    close(fd);
    return bytes_written;
}