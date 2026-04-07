#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #include <process.h> // Bibliothèque pour les threads sous Windows
    #pragma comment(lib, "ws2_32.lib")
#else
    #include <sys/socket.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <pthread.h> // Bibliothèque pour les threads sous Linux
#endif

#define BUFFER_SIZE 1024
#define REMOTE_PORT 6000 

// Structure pour transmettre les données au thread
typedef struct {
    int sock;
    struct sockaddr_in peer_addr;
} thread_data_t;

void init_sockets() {
#ifdef _WIN32
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        printf("Échec de l'initialisation de Winsock. Code erreur : %d\n", WSAGetLastError());
        exit(EXIT_FAILURE);
    }
#endif
}

// Fonction de gestion de l'envoi des messages (exécutée dans un thread séparé)
#ifdef _WIN32
void send_thread(void* arg) {
#else
void* send_thread(void* arg) {
#endif
    thread_data_t* data = (thread_data_t*)arg;
    char buffer[BUFFER_SIZE];

    while (1) {
        if (fgets(buffer, BUFFER_SIZE, stdin)) {
            // Supprimer le caractère de nouvelle ligne
            buffer[strcspn(buffer, "\r\n")] = 0;
            
            if (strlen(buffer) > 0) {
                int sent = sendto(data->sock, buffer, (int)strlen(buffer), 0, 
                                  (struct sockaddr*)&data->peer_addr, sizeof(data->peer_addr));
                if (sent < 0) {
                    printf("Erreur lors de l'envoi du message !\n");
                } else {
                    printf("> Message envoyé !\n> ");
                    fflush(stdout);
                }
            }
        }
    }
#ifndef _WIN32
    return NULL;
#endif
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage : %s <IP_distante>\n", argv[0]);
        return 1;
    }

    char *remote_ip = argv[1];
    init_sockets();

    // 1. Création du socket UDP
    int eth_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (eth_sock < 0) {
        perror("Échec de création du socket");
        return 1;
    }

    // 2. Configuration de l'adresse locale (bind)
    struct sockaddr_in my_addr;
    my_addr.sin_family = AF_INET;
    my_addr.sin_port = htons(REMOTE_PORT);
    my_addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(eth_sock, (struct sockaddr*)&my_addr, sizeof(my_addr)) < 0) {
#ifdef _WIN32
        printf("Échec du bind. Erreur : %d\n", WSAGetLastError());
#else
        perror("Échec du bind");
#endif
        return 1;
    }

    // 3. Configuration de l'adresse distante (pair)
    thread_data_t t_data;
    t_data.sock = eth_sock;
    t_data.peer_addr.sin_family = AF_INET;
    t_data.peer_addr.sin_port = htons(REMOTE_PORT);
    if (inet_pton(AF_INET, remote_ip, &t_data.peer_addr.sin_addr) <= 0) {
        printf("Adresse IP invalide !\n");
        return 1;
    }

    printf("--- Cœur réseau démarré ---\n");
    printf("Pair : %s:%d\n", remote_ip, REMOTE_PORT);
    printf("Tapez un message puis appuyez sur Entrée pour envoyer :\n> ");
    fflush(stdout);

    // 4. Création d'un thread pour l'envoi des données (entrée clavier)
#ifdef _WIN32
    _beginthread(send_thread, 0, &t_data);
#else
    pthread_t thread_id;
    pthread_create(&thread_id, NULL, send_thread, &t_data);
#endif

    // 5. Boucle principale : réception des données
    char recv_buffer[BUFFER_SIZE];
    struct sockaddr_in from_addr;
    int addr_len = sizeof(from_addr);

    while (1) {
        int len = recvfrom(eth_sock, recv_buffer, BUFFER_SIZE - 1, 0, 
                           (struct sockaddr*)&from_addr, &addr_len);
        if (len > 0) {
            recv_buffer[len] = '\0';
            printf("\n[REÇU de %s] : %s\n> ", inet_ntoa(from_addr.sin_addr), recv_buffer);
            fflush(stdout);
        } else if (len < 0) {
            // Éviter d'afficher des erreurs en boucle si le socket est non-bloquant
#ifdef _WIN32
            if (WSAGetLastError() != WSAEWOULDBLOCK) break;
#endif
        }
    }

#ifdef _WIN32
    closesocket(eth_sock);
    WSACleanup();
#else
    close(eth_sock);
#endif
    return 0;
}