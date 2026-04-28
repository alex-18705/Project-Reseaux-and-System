/*
 * proxy_udp_real_ip.c — Proxy UDP P2P for Real IP testing
 *
 * This version is optimized for testing between two different machines.
 * It prints local IP addresses to help the user and provides more verbose logging.
 *
 * Compilation: gcc -o proxy_udp_real_ip proxy_udp_real_ip.c -lws2_32
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
    #include <netdb.h>
    typedef int sock_t;
    #define SOCK_INVALID (-1)
    #define THREAD_CREATE(fn, arg) \
        do { pthread_t _t; pthread_create(&_t, NULL, (fn), (arg)); pthread_detach(_t); } while(0)
    #define THREAD_RET void*
    #define THREAD_RETURN return NULL
#endif

#define BUFFER_SIZE 65535

/* Global sockets */
static sock_t lan_sock = SOCK_INVALID;
static sock_t py_sock = SOCK_INVALID;

/* Dynamic addresses */
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

/* Helper to print local IPs */
void print_local_ips() {
    char hostname[256];
    if (gethostname(hostname, sizeof(hostname)) == 0) {
        struct hostent *host_entry;
        host_entry = gethostbyname(hostname);
        if (host_entry != NULL) {
            printf("[INFO] Local Hostname: %s\n", hostname);
            for (int i = 0; host_entry->h_addr_list[i] != NULL; i++) {
                struct in_addr addr;
                memcpy(&addr, host_entry->h_addr_list[i], sizeof(struct in_addr));
                printf("[INFO] Local IP %d: %s\n", i + 1, inet_ntoa(addr));
            }
        }
    }
}

/* ------------------------------------------------------------------------
 * THREAD 1: LAN -> Python
 * ------------------------------------------------------------------------ */
static THREAD_RET lan_to_py_thread(void *arg) {
    char buffer[BUFFER_SIZE];
    struct sockaddr_in sender_addr;
    socklen_t sender_len = sizeof(sender_addr);

    printf("[LAN] Network listener thread started.\n");

    while (1) {
        int n = recvfrom(lan_sock, buffer, BUFFER_SIZE, 0, (struct sockaddr*)&sender_addr, &sender_len);
        if (n > 0) {
            /* Discover or update remote peer */
            if (!remote_peer_known) {
                remote_peer_addr = sender_addr;
                remote_peer_known = 1;
                printf("-> [LAN] Peer discovered: %s:%d\n", inet_ntoa(sender_addr.sin_addr), ntohs(sender_addr.sin_port));
            } else if (sender_addr.sin_addr.s_addr != remote_peer_addr.sin_addr.s_addr || sender_addr.sin_port != remote_peer_addr.sin_port) {
                /* Optional: log if we receive from a different IP than expected */
                // printf("-> [LAN] Received from unexpected source: %s:%d\n", inet_ntoa(sender_addr.sin_addr), ntohs(sender_addr.sin_port));
            }
            
            /* Forward to Python client if attached */
            if (py_client_known) {
                sendto(py_sock, buffer, n, 0, (struct sockaddr*)&py_client_addr, sizeof(py_client_addr));
            }
        }
    }
    THREAD_RETURN;
}

/* ------------------------------------------------------------------------
 * THREAD 2: Python -> LAN
 * ------------------------------------------------------------------------ */
static THREAD_RET py_to_lan_thread(void *arg) {
    char buffer[BUFFER_SIZE];
    struct sockaddr_in sender_addr;
    socklen_t sender_len = sizeof(sender_addr);

    printf("[IPC] Python listener thread started.\n");

    while (1) {
        int n = recvfrom(py_sock, buffer, BUFFER_SIZE, 0, (struct sockaddr*)&sender_addr, &sender_len);
        if (n > 0) {
            /* Attach local Python app */
            if (!py_client_known) {
                py_client_addr = sender_addr;
                py_client_known = 1;
                printf("-> [IPC] Python app attached on port %d\n", ntohs(sender_addr.sin_port));
            }
            
            /* Forward to LAN peer */
            if (remote_peer_known) {
                sendto(lan_sock, buffer, n, 0, (struct sockaddr*)&remote_peer_addr, sizeof(remote_peer_addr));
            } else {
                // printf("-> [IPC] Warning: No remote peer known yet, dropping packet.\n");
            }
        }
    }
    THREAD_RETURN;
}

int main(int argc, char *argv[]) {
    printf("========== PROXY C REAL IP TEST ==========\n\n");

    print_local_ips();
    printf("\n");

    char *remote_ip = NULL;
    int py_port = 5000;
    int lan_listen_port = 6000;
    int remote_dest_port = 6000;

    if (argc >= 2 && strcmp(argv[1], "peer") != 0) {
        remote_ip = argv[1];
    }
    if (argc >= 3) py_port = atoi(argv[2]);
    if (argc >= 4) lan_listen_port = atoi(argv[3]);
    if (argc >= 5) remote_dest_port = atoi(argv[4]);
    else remote_dest_port = lan_listen_port;

    init_sockets();

    lan_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    py_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);

    if (lan_sock == SOCK_INVALID || py_sock == SOCK_INVALID) {
        printf("[!] Error creating sockets.\n");
        return 1;
    }

    int opt = 1;
    setsockopt(lan_sock, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));
    setsockopt(py_sock, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));

    /* LAN bind: INADDR_ANY to listen on all interfaces (including the one from ipconfig) */
    struct sockaddr_in lan_bind;
    lan_bind.sin_family = AF_INET;
    lan_bind.sin_port = htons(lan_listen_port);
    lan_bind.sin_addr.s_addr = INADDR_ANY; 
    if (bind(lan_sock, (struct sockaddr*)&lan_bind, sizeof(lan_bind)) < 0) {
        printf("[!] Error: Could not bind LAN socket to port %d.\n", lan_listen_port);
        return 1;
    }

    /* Python bind: 127.0.0.1 for local IPC */
    struct sockaddr_in py_bind;
    py_bind.sin_family = AF_INET;
    py_bind.sin_port = htons(py_port);
    py_bind.sin_addr.s_addr = inet_addr("127.0.0.1");
    if (bind(py_sock, (struct sockaddr*)&py_bind, sizeof(py_bind)) < 0) {
        printf("[!] Error: Could not bind Python socket to port %d.\n", py_port);
        return 1;
    }

    if (remote_ip != NULL) {
        remote_peer_addr.sin_family = AF_INET;
        remote_peer_addr.sin_port = htons(remote_dest_port);
        inet_pton(AF_INET, remote_ip, &remote_peer_addr.sin_addr);
        remote_peer_known = 1;
        printf("[LAN] P2P Mode: Initiator\n");
        printf("[LAN] Target Peer: %s:%d\n", remote_ip, remote_dest_port);
        printf("[LAN] Listening on all interfaces, port %d\n", lan_listen_port);
    } else {
        printf("[LAN] P2P Mode: Waiting for discovery\n");
        printf("[LAN] Listening on port %d... Waiting for peer to send first packet.\n", lan_listen_port);
    }

    printf("[IPC] Waiting for Python packets on 127.0.0.1:%d...\n", py_port);

    THREAD_CREATE(lan_to_py_thread, NULL);
    THREAD_CREATE(py_to_lan_thread, NULL);

    while (1) {
        #ifdef _WIN32
            Sleep(1000);
        #else
            sleep(1);
        #endif
    }

    return 0;
}
