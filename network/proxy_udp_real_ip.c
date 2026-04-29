/*
 * proxy_udp_real_ip.c — Proxy UDP P2P for Real IP testing
 *
 * Supports two modes:
 *   Server (host)  : ./proxy_udp_real_ip            py_port lan_port
 *   Client (joiner): ./proxy_udp_real_ip <remote_ip> py_port lan_port [remote_port]
 *
 * Key fix vs previous version:
 *   - "Joiner" immediately sends a HELLO UDP punch-packet to the remote host
 *     so NAT on both sides is opened and the host can learn the joiner's public IP/port.
 *   - Python->LAN packets are QUEUED (not dropped) when remote peer is not yet known,
 *     and flushed once the peer is discovered.
 *   - Each forward is logged for easy debugging.
 *
 * Compilation Windows : gcc -o proxy_udp_real_ip proxy_udp_real_ip.c -lws2_32
 * Compilation Linux   : gcc -o proxy_udp_real_ip proxy_udp_real_ip.c -pthread
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
    #define SLEEP_MS(ms) Sleep(ms)
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
    #define SLEEP_MS(ms) usleep((ms)*1000)
#endif

#define BUFFER_SIZE   65535
/* Max pending Python packets to buffer while waiting for peer discovery */
#define PENDING_QUEUE 32

/* ---- Globals ---- */
static sock_t lan_sock = SOCK_INVALID;
static sock_t py_sock  = SOCK_INVALID;

/* Python client (local) */
static struct sockaddr_in py_client_addr;
static int py_client_known = 0;

/* Remote peer (internet) */
static struct sockaddr_in remote_peer_addr;
static int remote_peer_known = 0;

/* Pending queue: Python packets received before peer was known */
static char   pending_bufs[PENDING_QUEUE][BUFFER_SIZE];
static int    pending_lens[PENDING_QUEUE];
static int    pending_head = 0;
static int    pending_count = 0;

static void init_sockets(void) {
#ifdef _WIN32
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);
#endif
}

/* ---- Print local IPs ---- */
static void print_local_ips(void) {
    char hostname[256];
    if (gethostname(hostname, sizeof(hostname)) == 0) {
        printf("[INFO] Hostname : %s\n", hostname);
#ifdef _WIN32
        struct hostent *he = gethostbyname(hostname);
        if (he) {
            for (int i = 0; he->h_addr_list[i] != NULL; i++) {
                struct in_addr a;
                memcpy(&a, he->h_addr_list[i], sizeof(a));
                printf("[INFO] Local IP  : %s\n", inet_ntoa(a));
            }
        }
#else
        struct addrinfo hints, *res, *p;
        memset(&hints, 0, sizeof(hints));
        hints.ai_family = AF_INET;
        if (getaddrinfo(hostname, NULL, &hints, &res) == 0) {
            for (p = res; p != NULL; p = p->ai_next) {
                struct sockaddr_in *sin = (struct sockaddr_in *)p->ai_addr;
                printf("[INFO] Local IP  : %s\n", inet_ntoa(sin->sin_addr));
            }
            freeaddrinfo(res);
        }
#endif
    }
}

/* ---- Flush pending queue to the newly-discovered peer ---- */
static void flush_pending_to_peer(void) {
    if (pending_count == 0) return;
    printf("[LAN] Flushing %d buffered Python packet(s) to peer...\n", pending_count);
    for (int i = 0; i < pending_count; i++) {
        int idx = (pending_head + i) % PENDING_QUEUE;
        sendto(lan_sock, pending_bufs[idx], pending_lens[idx], 0,
               (struct sockaddr*)&remote_peer_addr, sizeof(remote_peer_addr));
    }
    pending_head  = 0;
    pending_count = 0;
}

/* ====================================================================
 * THREAD 1 : LAN -> Python
 * ==================================================================== */
static THREAD_RET lan_to_py_thread(void *arg) {
    char buffer[BUFFER_SIZE];
    struct sockaddr_in sender;
    socklen_t sender_len = sizeof(sender);

    printf("[LAN] Network listener thread started.\n");
    fflush(stdout);

    while (1) {
        int n = recvfrom(lan_sock, buffer, BUFFER_SIZE, 0,
                         (struct sockaddr*)&sender, &sender_len);
        if (n <= 0) continue;

        /* Skip HELLO punches (tiny marker) */
        if (n == 5 && memcmp(buffer, "HELLO", 5) == 0) {
            if (!remote_peer_known) {
                remote_peer_addr = sender;
                remote_peer_known = 1;
                printf("-> [LAN] Peer discovered via HELLO: %s:%d\n",
                       inet_ntoa(sender.sin_addr), ntohs(sender.sin_port));
                fflush(stdout);
                flush_pending_to_peer();
            }
            /* Send HELLO back so the other side also knows us */
            sendto(lan_sock, "HELLO", 5, 0,
                   (struct sockaddr*)&sender, sizeof(sender));
            continue;
        }

        /* Discover peer from first real data packet too */
        if (!remote_peer_known) {
            remote_peer_addr = sender;
            remote_peer_known = 1;
            printf("-> [LAN] Peer discovered: %s:%d\n",
                   inet_ntoa(sender.sin_addr), ntohs(sender.sin_port));
            fflush(stdout);
            flush_pending_to_peer();
        }

        /* Forward to Python */
        if (py_client_known) {
            sendto(py_sock, buffer, n, 0,
                   (struct sockaddr*)&py_client_addr, sizeof(py_client_addr));
        }
    }
    THREAD_RETURN;
}

/* ====================================================================
 * THREAD 2 : Python -> LAN
 * ==================================================================== */
static THREAD_RET py_to_lan_thread(void *arg) {
    char buffer[BUFFER_SIZE];
    struct sockaddr_in sender;
    socklen_t sender_len = sizeof(sender);

    printf("[IPC] Python listener thread started.\n");
    fflush(stdout);

    while (1) {
        int n = recvfrom(py_sock, buffer, BUFFER_SIZE, 0,
                         (struct sockaddr*)&sender, &sender_len);
        if (n <= 0) continue;

        /* Register Python client on first contact */
        if (!py_client_known) {
            py_client_addr  = sender;
            py_client_known = 1;
            printf("-> [IPC] Python app attached on port %d\n",
                   ntohs(sender.sin_port));
            fflush(stdout);
        }

        if (remote_peer_known) {
            sendto(lan_sock, buffer, n, 0,
                   (struct sockaddr*)&remote_peer_addr, sizeof(remote_peer_addr));
        } else {
            /* Queue the packet — will be flushed once the peer is discovered */
            if (pending_count < PENDING_QUEUE) {
                int slot = (pending_head + pending_count) % PENDING_QUEUE;
                if (n <= BUFFER_SIZE) {
                    memcpy(pending_bufs[slot], buffer, n);
                    pending_lens[slot] = n;
                    pending_count++;
                }
            }
            /* else: queue full, drop oldest (overwrite) */
        }
    }
    THREAD_RETURN;
}

/* ====================================================================
 * THREAD 3 : HELLO keepalive (joiner only)
 * Sends a HELLO punch packet every 2 seconds to keep the NAT hole open
 * and accelerate discovery.
 * ==================================================================== */
static THREAD_RET hello_keepalive_thread(void *arg) {
    (void)arg;
    int rounds = 0;
    printf("[LAN] Starting HELLO punch-through to remote peer...\n");
    fflush(stdout);
    while (!remote_peer_known || rounds < 5) {
        sendto(lan_sock, "HELLO", 5, 0,
               (struct sockaddr*)&remote_peer_addr, sizeof(remote_peer_addr));
        SLEEP_MS(2000);
        rounds++;
    }
    printf("[LAN] HELLO punch-through done.\n");
    fflush(stdout);
    THREAD_RETURN;
}

/* ==================================================================== */
int main(int argc, char *argv[]) {
    printf("========== PROXY C REAL IP TEST ==========\n\n");

    print_local_ips();
    printf("\n");

    char *remote_ip      = NULL;
    int   py_port        = 5000;
    int   lan_listen_port = 6000;
    int   remote_dest_port= 6000;

    /*
     * CLI:  proxy_udp_real_ip [remote_ip] [py_port] [lan_port] [remote_port]
     * "peer" keyword (legacy) means: wait for discovery (same as no remote_ip).
     */
    if (argc >= 2 && strcmp(argv[1], "peer") != 0 && strcmp(argv[1], "server") != 0) {
        remote_ip = argv[1];
    }
    if (argc >= 3) py_port          = atoi(argv[2]);
    if (argc >= 4) lan_listen_port  = atoi(argv[3]);
    if (argc >= 5) remote_dest_port = atoi(argv[4]);
    else           remote_dest_port = lan_listen_port;

    init_sockets();

    lan_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    py_sock  = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);

    if (lan_sock == SOCK_INVALID || py_sock == SOCK_INVALID) {
        printf("[!] Error creating sockets.\n");
        return 1;
    }

    int opt = 1;
    setsockopt(lan_sock, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));
    setsockopt(py_sock,  SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));

    /* LAN socket: bind on all interfaces so both LAN & internet packets arrive */
    struct sockaddr_in lan_bind;
    memset(&lan_bind, 0, sizeof(lan_bind));
    lan_bind.sin_family      = AF_INET;
    lan_bind.sin_port        = htons(lan_listen_port);
    lan_bind.sin_addr.s_addr = INADDR_ANY;
    if (bind(lan_sock, (struct sockaddr*)&lan_bind, sizeof(lan_bind)) < 0) {
        printf("[!] Error: Could not bind LAN socket to port %d.\n", lan_listen_port);
        return 1;
    }

    /* Python socket: bind on loopback only */
    struct sockaddr_in py_bind;
    memset(&py_bind, 0, sizeof(py_bind));
    py_bind.sin_family      = AF_INET;
    py_bind.sin_port        = htons(py_port);
    py_bind.sin_addr.s_addr = inet_addr("127.0.0.1");
    if (bind(py_sock, (struct sockaddr*)&py_bind, sizeof(py_bind)) < 0) {
        printf("[!] Error: Could not bind Python socket to port %d.\n", py_port);
        return 1;
    }

    if (remote_ip != NULL) {
        /* Joiner mode: we know the host IP ahead of time */
        memset(&remote_peer_addr, 0, sizeof(remote_peer_addr));
        remote_peer_addr.sin_family = AF_INET;
        remote_peer_addr.sin_port   = htons(remote_dest_port);
        inet_pton(AF_INET, remote_ip, &remote_peer_addr.sin_addr);
        remote_peer_known = 1;

        printf("[LAN] P2P Mode: Initiator (Joiner)\n");
        printf("[LAN] Target Peer: %s:%d\n", remote_ip, remote_dest_port);
        printf("[LAN] Listening on all interfaces, port %d\n", lan_listen_port);
    } else {
        /* Server/host mode: wait for joiner to punch through */
        printf("[LAN] P2P Mode: Waiting for discovery\n");
        printf("[LAN] Listening on port %d... Waiting for peer to send first packet.\n",
               lan_listen_port);
    }

    printf("[IPC] Waiting for Python packets on 127.0.0.1:%d...\n", py_port);
    fflush(stdout);

    THREAD_CREATE(lan_to_py_thread, NULL);
    THREAD_CREATE(py_to_lan_thread, NULL);

    /* If we are the joiner, start punch-through right away */
    if (remote_ip != NULL) {
        THREAD_CREATE(hello_keepalive_thread, NULL);
    }

    /* Main thread: just keep the process alive */
    while (1) {
        SLEEP_MS(1000);
    }

    return 0;
}
