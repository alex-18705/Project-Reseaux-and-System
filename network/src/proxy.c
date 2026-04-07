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
    #include <netinet/tcp.h> // Nécessaire pour TCP_NODELAY sous Linux
#endif

#define BUFFER_SIZE 1024
#define REMOTE_PORT 6000 

void init_sockets() {
#ifdef _WIN32
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        printf("Échec de l'initialisation de Winsock. Code erreur : %d\n", WSAGetLastError());
        exit(EXIT_FAILURE);
    }
#endif
}

void cleanup_socket(int sock) {
#ifdef _WIN32
    closesocket(sock);
#else
    close(sock);
#endif
}

// Fonction de gestion de l'envoi des messages (exécutée dans un thread séparé)
#ifdef _WIN32
void send_thread(void* arg) {
#else
void* send_thread(void* arg) {
#endif
    int comm_sock = *(int*)arg; // Le socket connecté
    char buffer[BUFFER_SIZE];

    while (1) {
        if (fgets(buffer, BUFFER_SIZE, stdin)) {
            // Supprimer le caractère de nouvelle ligne
            buffer[strcspn(buffer, "\r\n")] = 0;
            
            if (strlen(buffer) > 0) {
                // Avec TCP, on utilise send() au lieu de sendto()
                int sent = send(comm_sock, buffer, (int)strlen(buffer), 0);
                if (sent < 0) {
                    printf("\nErreur lors de l'envoi du message ! La connexion est peut-être coupée.\n");
                    break; // Sortir si la connexion est perdue
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

    int comm_sock = -1; // Le socket qui sera utilisé pour communiquer
    
    // 1. Préparation de l'adresse du pair distant
    struct sockaddr_in peer_addr;
    peer_addr.sin_family = AF_INET;
    peer_addr.sin_port = htons(REMOTE_PORT);
    if (inet_pton(AF_INET, remote_ip, &peer_addr.sin_addr) <= 0) {
        printf("Adresse IP invalide !\n");
        return 1;
    }

    // 2. Tenter de se connecter en tant que Client
    printf("Tentative de connexion à %s:%d...\n", remote_ip, REMOTE_PORT);
    int temp_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    
    if (connect(temp_sock, (struct sockaddr*)&peer_addr, sizeof(peer_addr)) == 0) {
        printf("Connecté avec succès en tant que CLIENT.\n");
        comm_sock = temp_sock;
    } else {
        // La connexion a échoué (le pair n'est pas encore en ligne)
        cleanup_socket(temp_sock);
        printf("Le pair n'est pas prêt. Basculement en mode SERVEUR (en attente de connexion)...\n");

        int listen_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        
        // Autoriser la réutilisation de l'adresse (SO_REUSEADDR)
        int opt = 1;
        setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));

        struct sockaddr_in my_addr;
        my_addr.sin_family = AF_INET;
        my_addr.sin_port = htons(REMOTE_PORT);
        my_addr.sin_addr.s_addr = INADDR_ANY;

        if (bind(listen_sock, (struct sockaddr*)&my_addr, sizeof(my_addr)) < 0) {
            perror("Échec du bind");
            return 1;
        }

        if (listen(listen_sock, 1) < 0) {
            perror("Échec de l'écoute (listen)");
            return 1;
        }

        struct sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);
        comm_sock = accept(listen_sock, (struct sockaddr*)&client_addr, &client_len);
        
        if (comm_sock < 0) {
            perror("Échec de l'acceptation (accept)");
            return 1;
        }
        
        printf("Un pair s'est connecté ! Connecté avec succès en tant que SERVEUR.\n");
        cleanup_socket(listen_sock); // Plus besoin d'écouter d'autres connexions
    }

    // 3. OPTIMISATION : Désactiver l'algorithme de Nagle pour une latence minimale (Important pour le jeu)
    int flag = 1;
    if (setsockopt(comm_sock, IPPROTO_TCP, TCP_NODELAY, (char*)&flag, sizeof(int)) < 0) {
        printf("Avertissement : Impossible de définir TCP_NODELAY.\n");
    }

    printf("--- Cœur réseau TCP démarré ---\n");
    printf("Tapez un message puis appuyez sur Entrée pour envoyer :\n> ");
    fflush(stdout);

    // 4. Création d'un thread pour l'envoi des données
#ifdef _WIN32
    _beginthread(send_thread, 0, &comm_sock);
#else
    pthread_t thread_id;
    pthread_create(&thread_id, NULL, send_thread, &comm_sock);
#endif

    // 5. Boucle principale : réception des données TCP
    char recv_buffer[BUFFER_SIZE];

    while (1) {
        // Avec TCP, on utilise recv() au lieu de recvfrom()
        int len = recv(comm_sock, recv_buffer, BUFFER_SIZE - 1, 0);
        
        if (len > 0) {
            recv_buffer[len] = '\0';
            printf("\n[REÇU du pair] : %s\n> ", recv_buffer);
            fflush(stdout);
        } else if (len == 0) {
            // Un retour de 0 signifie que le pair a fermé la connexion de manière propre
            printf("\nLa connexion a été fermée par le pair distant.\n");
            break;
        } else {
            // Erreur de connexion (ex: coupure brutale)
            printf("\nErreur de réception. Connexion perdue.\n");
            break;
        }
    }

    // 6. Nettoyage final
    cleanup_socket(comm_sock);
#ifdef _WIN32
    WSACleanup();
#endif
    return 0;
}
//  gcc proxy.c -o proxy.exe -lws2_32 (win)  gcc proxy.c -o proxy -lpthread(linux) ./proxy ip1 ou ip2