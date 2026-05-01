/*
 * proxy_udp.c — Proxy UDP P2P (version multi-threads)
 *
 * Architecture 100% UDP, sans connexion (connectionless).
 * - 1 socket UDP local (port Python)
 * - 1 socket UDP LAN (port réseau)
 * - Thread 1 : Lit le réseau LAN -> Transfère au port Python éphémère
 * - Thread 2 : Lit Python -> Transfère au réseau LAN distant
 *
 * Compilation : gcc -o proxy_udp proxy_udp.c -lws2_32
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #include <windows.h>
    typedef SOCKET sock_t;
    #define SOCK_INVALID INVALID_SOCKET
    #define THREAD_CREATE(fn, arg) \
        do { HANDLE _h = CreateThread(NULL, 0, (fn), (arg), 0, NULL); if (_h) CloseHandle(_h); } while(0)
    #define THREAD_RET DWORD WINAPI
    #define THREAD_RETURN return 0
#else
    #include <sys/socket.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <pthread.h>
    typedef int sock_t;
    #define SOCK_INVALID (-1)
    #define THREAD_CREATE(fn, arg) \
        do { pthread_t _t; pthread_create(&_t, NULL, (fn), (arg)); pthread_detach(_t); } while(0)
    #define THREAD_RET void*
    #define THREAD_RETURN return NULL
#endif

#define BUFFER_SIZE 65535

/* Variables globales pour les sockets UDP */
static sock_t lan_sock = SOCK_INVALID;
static sock_t py_sock = SOCK_INVALID;

/* Adresses dynamiques découvertes lors de la réception */
static struct sockaddr_in py_client_addr;
static int py_client_known = 0;

static struct sockaddr_in remote_peer_addr;
static int remote_peer_known = 0;

static void init_sockets(void) {
#ifdef _WIN32
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
#endif
}

/* ------------------------------------------------------------------------
 * THREAD 1 : Écoute le LAN (port distant) et forward à Python
 * ------------------------------------------------------------------------ */
static THREAD_RET lan_to_py_thread(void *arg) {
    char buffer[BUFFER_SIZE];
    struct sockaddr_in sender_addr;
    socklen_t sender_len = sizeof(sender_addr);

    printf("[LAN] Thread d'écoute réseau lancé.\n");

    while (1) {
        int n = recvfrom(lan_sock, buffer, BUFFER_SIZE, 0, (struct sockaddr*)&sender_addr, &sender_len);
        if (n > 0) {
            /* Enregistre la source si c'est la première fois ou maj (serveur qui découvre le client) */
            if (!remote_peer_known) {
                remote_peer_addr = sender_addr;
                remote_peer_known = 1;
                printf("-> [LAN] IP distante découverte : %s:%d\n", inet_ntoa(sender_addr.sin_addr), ntohs(sender_addr.sin_port));
            }
            
            /* Forward au client Python (s'il s'est déjà manifesté) */
            if (py_client_known) {
                sendto(py_sock, buffer, n, 0, (struct sockaddr*)&py_client_addr, sizeof(py_client_addr));
            }
        }
    }
    THREAD_RETURN;
}

/* ------------------------------------------------------------------------
 * THREAD 2 : Écoute Python (localhost) et forward au LAN
 * ------------------------------------------------------------------------ */
static THREAD_RET py_to_lan_thread(void *arg) {
    char buffer[BUFFER_SIZE];
    struct sockaddr_in sender_addr;
    socklen_t sender_len = sizeof(sender_addr);

    printf("[IPC] Thread d'écoute Python lancé.\n");

    while (1) {
        int n = recvfrom(py_sock, buffer, BUFFER_SIZE, 0, (struct sockaddr*)&sender_addr, &sender_len);
        if (n > 0) {
            /* Enregistre le port éphémère de l'application Python locale */
            if (!py_client_known) {
                py_client_addr = sender_addr;
                py_client_known = 1;
                printf("-> [IPC] Client Python attaché sur le port %d\n", ntohs(sender_addr.sin_port));
            }
            
            /* Forward vers le réseau LAN (s'il est connu) */
            if (remote_peer_known) {
                sendto(lan_sock, buffer, n, 0, (struct sockaddr*)&remote_peer_addr, sizeof(remote_peer_addr));
            }
        }
    }
    THREAD_RETURN;
}


int main(int argc, char *argv[]) {
    printf("========== PROXY C (MODE UDP PUR + THREADS) ==========\n\n");

    char *remote_ip = NULL;
    int py_port = 5000;
    int lan_listen_port = 6000;
    int remote_dest_port = 6000;

    if (argc >= 2 && strcmp(argv[1], "server") != 0) {
        remote_ip = argv[1];
    }
    if (argc >= 3) py_port = atoi(argv[2]);
    if (argc >= 4) lan_listen_port = atoi(argv[3]);
    if (argc >= 5) remote_dest_port = atoi(argv[4]);
    else remote_dest_port = lan_listen_port;

    init_sockets();

    /* Création des deux sockets UDP */
    lan_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    py_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);

    if (lan_sock == SOCK_INVALID || py_sock == SOCK_INVALID) {
        printf("[!] Erreur de création des sockets UDP.\n");
        return 1;
    }

    /* Permettre la réutilisation rapide */
    int opt = 1;
    setsockopt(lan_sock, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));
    setsockopt(py_sock, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));

    /* Bind sur le port LAN pour recevoir du réseau */
    struct sockaddr_in lan_bind;
    lan_bind.sin_family = AF_INET;
    lan_bind.sin_port = htons(lan_listen_port);
    lan_bind.sin_addr.s_addr = INADDR_ANY;
    if (bind(lan_sock, (struct sockaddr*)&lan_bind, sizeof(lan_bind)) < 0) {
        printf("[!] Erreur: Impossible de lier le socket LAN (port %d).\n", lan_listen_port);
        return 1;
    }

    /* Bind sur le port local pour recevoir de Python */
    struct sockaddr_in py_bind;
    py_bind.sin_family = AF_INET;
    py_bind.sin_port = htons(py_port);
    py_bind.sin_addr.s_addr = inet_addr("127.0.0.1");
    if (bind(py_sock, (struct sockaddr*)&py_bind, sizeof(py_bind)) < 0) {
        printf("[!] Erreur: Impossible de lier le socket Python (port %d).\n", py_port);
        return 1;
    }

    /* Si on connaît l'IP distante (mode client), on l'enregistre de suite */
    if (remote_ip != NULL) {
        remote_peer_addr.sin_family = AF_INET;
        remote_peer_addr.sin_port = htons(remote_dest_port);
        inet_pton(AF_INET, remote_ip, &remote_peer_addr.sin_addr);
        remote_peer_known = 1;
        printf("[LAN] Client UDP : Envoi initial ciblé vers %s:%d (Écoute réponses sur %d)\n", remote_ip, remote_dest_port, lan_listen_port);
    } else {
        printf("[LAN] Serveur UDP : En attente d'un pair sur le port %d...\n", lan_listen_port);
    }

    printf("[IPC] En attente des paquets UDP de Python sur 127.0.0.1:%d...\n", py_port);

    /* Démarrage des threads */
    THREAD_CREATE(lan_to_py_thread, NULL);
    THREAD_CREATE(py_to_lan_thread, NULL);

    /* Le thread principal fait une boucle infinie pour maintenir le programme en vie */
    while (1) {
        #ifdef _WIN32
            Sleep(1000);
        #else
            sleep(1);
        #endif
    }

    return 0;
}
