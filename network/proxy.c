#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #include <process.h>
    #pragma comment(lib, "ws2_32.lib")
#else
    #include <sys/socket.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <pthread.h>
    #include <netinet/tcp.h>
#endif

#define BUFFER_SIZE 4096
#define REMOTE_PORT 6000   // Port pour communiquer avec l'autre PC (LAN)
#define LOCAL_PORT 5000    // Port pour communiquer avec Python (Localhost)

// Structure pour passer les deux sockets aux threads
typedef struct {
    int lan_sock;
    int local_sock;
} sockets_t;

void init_sockets() {
#ifdef _WIN32
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        printf("Échec de l'initialisation de Winsock.\n");
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

// ====================================================================
// THREAD 1 : Écoute Python (Local) et transfère vers le réseau (LAN)
// ====================================================================
#ifdef _WIN32
void python_to_lan_thread(void* arg) {
#else
void* python_to_lan_thread(void* arg) {
#endif
    sockets_t* socks = (sockets_t*)arg;
    char buffer[BUFFER_SIZE];

    while (1) {
        int len = recv(socks->local_sock, buffer, BUFFER_SIZE - 1, 0);
        if (len > 0) {
            buffer[len] = '\0';
            // Afficher dans la console du proxy pour débugger
            printf("[PYTHON -> LAN] : %s\n", buffer);
            
            // Envoyer la donnée au PC distant
            send(socks->lan_sock, buffer, len, 0);
        } else if (len == 0) {
            printf("\n[!] Le script Python s'est déconnecté.\n");
            break;
        } else {
            printf("\n[!] Erreur de lecture depuis Python.\n");
            break;
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
    sockets_t all_sockets;


    // ÉTAPE 1 : Connexion au PC distant (Réseau LAN - Port 6000)


    struct sockaddr_in peer_addr;
    peer_addr.sin_family = AF_INET;
    peer_addr.sin_port = htons(REMOTE_PORT);
    inet_pton(AF_INET, remote_ip, &peer_addr.sin_addr);

    printf("Tentative de connexion au réseau LAN (%s:%d)...\n", remote_ip, REMOTE_PORT);
    int temp_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    
    if (connect(temp_sock, (struct sockaddr*)&peer_addr, sizeof(peer_addr)) == 0) {
        printf("-> [LAN] Connecté en tant que CLIENT.\n");
        all_sockets.lan_sock = temp_sock;
    } else {
        cleanup_socket(temp_sock);
        printf("-> [LAN] Le pair n'est pas prêt. Passage en mode SERVEUR...\n");

        int listen_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        int opt = 1;
        setsockopt(listen_sock, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));

        struct sockaddr_in my_addr;
        my_addr.sin_family = AF_INET;
        my_addr.sin_port = htons(REMOTE_PORT);
        my_addr.sin_addr.s_addr = INADDR_ANY;

        bind(listen_sock, (struct sockaddr*)&my_addr, sizeof(my_addr));
        listen(listen_sock, 1);

        struct sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);
        all_sockets.lan_sock = accept(listen_sock, (struct sockaddr*)&client_addr, &client_len);
        
        printf("-> [LAN] Un pair s'est connecté ! SERVEUR prêt.\n");
        cleanup_socket(listen_sock); 
    }

    // Optimisation Nagle pour le LAN
    int flag = 1;
    setsockopt(all_sockets.lan_sock, IPPROTO_TCP, TCP_NODELAY, (char*)&flag, sizeof(int));


    // ÉTAPE 2 : Création du serveur local pour Python (Port 5000)


    printf("\nEn attente de la connexion de Python sur le port %d (Localhost)...\n", LOCAL_PORT);
    int local_server_sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    int opt_local = 1;
    setsockopt(local_server_sock, SOL_SOCKET, SO_REUSEADDR, (char*)&opt_local, sizeof(opt_local));

    struct sockaddr_in local_addr;
    local_addr.sin_family = AF_INET;
    local_addr.sin_port = htons(LOCAL_PORT);
    local_addr.sin_addr.s_addr = inet_addr("127.0.0.1"); // N'accepte que les connexions de ce PC

    bind(local_server_sock, (struct sockaddr*)&local_addr, sizeof(local_addr));
    listen(local_server_sock, 1); // N'accepte qu'un seul processus Python

    struct sockaddr_in python_addr;
    socklen_t python_len = sizeof(python_addr);
    all_sockets.local_sock = accept(local_server_sock, (struct sockaddr*)&python_addr, &python_len);
    
    printf("-> [IPC] Python est connecté avec succès au C Proxy !\n\n");
    printf("========== LE PONT C-PYTHON EST OPÉRATIONNEL ==========\n\n");
    cleanup_socket(local_server_sock); // Plus besoin d'écouter d'autres processus Python

  
    // ÉTAPE 3 : Démarrage du thread de transfert (Python -> LAN)


#ifdef _WIN32
    _beginthread(python_to_lan_thread, 0, &all_sockets);
#else
    pthread_t thread_id;
    pthread_create(&thread_id, NULL, python_to_lan_thread, &all_sockets);
#endif

    // ÉTAPE 4 : Boucle principale (LAN -> Python)


    char recv_buffer[BUFFER_SIZE];

    while (1) {
        int len = recv(all_sockets.lan_sock, recv_buffer, BUFFER_SIZE - 1, 0);
        
        if (len > 0) {
            recv_buffer[len] = '\0';
            printf("[LAN -> PYTHON] : %s\n", recv_buffer);
            
            // Transférer la donnée reçue du réseau directement au script Python
            send(all_sockets.local_sock, recv_buffer, len, 0);
        } else {
            printf("\n[!] La connexion réseau (LAN) a été perdue.\n");
            break;
        }
    }

    // Nettoyage
    cleanup_socket(all_sockets.lan_sock);
    cleanup_socket(all_sockets.local_sock);
#ifdef _WIN32
    WSACleanup();
#endif
    return 0;
}