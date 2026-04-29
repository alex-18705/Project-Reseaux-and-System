/*
 * proxy_udp_real_ip.c — Proxy UDP P2P — Real IP / Internet
 *
 * Modes:
 *   Host  : proxy_udp_real_ip server   <py_port> <lan_port>
 *   Joiner: proxy_udp_real_ip <host_ip> <py_port> <lan_port> [<remote_port>]
 *
 * Fixes vs previous:
 *   - No HELLO ping-pong: we only reply ONCE to open NAT, never again.
 *   - Symmetric queue: LAN→Python packets are also buffered when Python
 *     has not yet registered (py_client_known==0).
 *   - Full diagnostic logging: every receive/forward is printed.
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
    #define THREAD_CREATE(fn,arg) \
        do{HANDLE _h=CreateThread(NULL,0,(fn),(arg),0,NULL);if(_h)CloseHandle(_h);}while(0)
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
    #define THREAD_CREATE(fn,arg) \
        do{pthread_t _t;pthread_create(&_t,NULL,(fn),(arg));pthread_detach(_t);}while(0)
    #define THREAD_RET void*
    #define THREAD_RETURN return NULL
    #define SLEEP_MS(ms) usleep((ms)*1000)
#endif

#define BUFFER_SIZE   65535
#define QUEUE_SIZE    64      /* packets buffered while waiting for peer/python */

/* ---- Globals ---- */
static sock_t lan_sock = SOCK_INVALID;
static sock_t py_sock  = SOCK_INVALID;

static struct sockaddr_in py_client_addr;
static volatile int py_client_known = 0;

static struct sockaddr_in remote_peer_addr;
static volatile int remote_peer_known = 0;

/* We only send ONE HELLO reply to avoid ping-pong floods */
static volatile int hello_reply_sent = 0;

/* Queue: LAN->Python when py_client not yet registered */
static char  q_lan[QUEUE_SIZE][BUFFER_SIZE];
static int   q_lan_len[QUEUE_SIZE];
static int   q_lan_head = 0, q_lan_count = 0;

/* Queue: Python->LAN when remote peer not yet known */
static char  q_py[QUEUE_SIZE][BUFFER_SIZE];
static int   q_py_len[QUEUE_SIZE];
static int   q_py_head = 0, q_py_count = 0;

static void init_wsa(void) {
#ifdef _WIN32
    WSADATA w; WSAStartup(MAKEWORD(2,2),&w);
#endif
}

static void print_local_ips(void) {
    char h[256];
    if (gethostname(h, sizeof(h)) != 0) return;
    printf("[INFO] Hostname : %s\n", h);
#ifdef _WIN32
    struct hostent *he = gethostbyname(h);
    if (he) {
        for (int i = 0; he->h_addr_list[i]; i++) {
            struct in_addr a;
            memcpy(&a, he->h_addr_list[i], sizeof(a));
            printf("[INFO] Local IP  : %s\n", inet_ntoa(a));
        }
    }
#endif
}

/* Flush LAN->Python queue after Python registers */
static void flush_lan_queue(void) {
    if (q_lan_count == 0) return;
    printf("[PY ] Flushing %d buffered LAN packet(s) to Python...\n", q_lan_count);
    fflush(stdout);
    for (int i = 0; i < q_lan_count; i++) {
        int idx = (q_lan_head + i) % QUEUE_SIZE;
        sendto(py_sock, q_lan[idx], q_lan_len[idx], 0,
               (struct sockaddr*)&py_client_addr, sizeof(py_client_addr));
    }
    q_lan_head = 0; q_lan_count = 0;
}

/* Flush Python->LAN queue after peer is discovered */
static void flush_py_queue(void) {
    if (q_py_count == 0) return;
    printf("[LAN] Flushing %d buffered Python packet(s) to peer...\n", q_py_count);
    fflush(stdout);
    for (int i = 0; i < q_py_count; i++) {
        int idx = (q_py_head + i) % QUEUE_SIZE;
        sendto(lan_sock, q_py[idx], q_py_len[idx], 0,
               (struct sockaddr*)&remote_peer_addr, sizeof(remote_peer_addr));
    }
    q_py_head = 0; q_py_count = 0;
}

/* ====================================================================
 * THREAD 1 : LAN -> Python
 * Receives packets from the remote peer; forwards to local Python.
 * ==================================================================== */
static THREAD_RET lan_to_py_thread(void *arg) {
    char buf[BUFFER_SIZE];
    struct sockaddr_in sender;
    socklen_t slen;
    static long pkt_count = 0;

    (void)arg;
    printf("[LAN] Network listener thread started.\n");
    fflush(stdout);

    while (1) {
        slen = sizeof(sender);
        int n = recvfrom(lan_sock, buf, BUFFER_SIZE, 0,
                         (struct sockaddr*)&sender, &slen);
        if (n <= 0) continue;

        /* ---- HELLO: NAT punch-through packet ---- */
        if (n == 5 && memcmp(buf, "HELLO", 5) == 0) {
            if (!remote_peer_known) {
                remote_peer_addr  = sender;
                remote_peer_known = 1;
                printf("-> [LAN] Peer discovered via HELLO: %s:%d\n",
                       inet_ntoa(sender.sin_addr), ntohs(sender.sin_port));
                fflush(stdout);
                flush_py_queue();
            }
            /* Reply ONCE so the other side learns our address too */
            if (!hello_reply_sent) {
                hello_reply_sent = 1;
                sendto(lan_sock, "HELLO", 5, 0,
                       (struct sockaddr*)&sender, sizeof(sender));
                printf("[LAN] Sent HELLO reply to %s:%d\n",
                       inet_ntoa(sender.sin_addr), ntohs(sender.sin_port));
                fflush(stdout);
            }
            continue;
        }

        /* ---- Real data packet ---- */
        if (!remote_peer_known) {
            remote_peer_addr  = sender;
            remote_peer_known = 1;
            printf("-> [LAN] Peer discovered via data: %s:%d\n",
                   inet_ntoa(sender.sin_addr), ntohs(sender.sin_port));
            fflush(stdout);
            flush_py_queue();
        }

        pkt_count++;
        if (pkt_count <= 5 || pkt_count % 50 == 0) {
            printf("[LAN] Pkt #%ld from %s:%d (%d bytes) -> Python? %s\n",
                   pkt_count,
                   inet_ntoa(sender.sin_addr), ntohs(sender.sin_port), n,
                   py_client_known ? "YES" : "QUEUED");
            fflush(stdout);
        }

        if (py_client_known) {
            sendto(py_sock, buf, n, 0,
                   (struct sockaddr*)&py_client_addr, sizeof(py_client_addr));
        } else {
            /* Buffer it; flush when Python registers */
            if (q_lan_count < QUEUE_SIZE) {
                int slot = (q_lan_head + q_lan_count) % QUEUE_SIZE;
                memcpy(q_lan[slot], buf, n);
                q_lan_len[slot] = n;
                q_lan_count++;
            }
        }
    }
    THREAD_RETURN;
}

/* ====================================================================
 * THREAD 2 : Python -> LAN
 * Receives packets from local Python; forwards to remote peer.
 * ==================================================================== */
static THREAD_RET py_to_lan_thread(void *arg) {
    char buf[BUFFER_SIZE];
    struct sockaddr_in sender;
    socklen_t slen;
    static long pkt_count = 0;

    (void)arg;
    printf("[IPC] Python listener thread started.\n");
    fflush(stdout);

    while (1) {
        slen = sizeof(sender);
        int n = recvfrom(py_sock, buf, BUFFER_SIZE, 0,
                         (struct sockaddr*)&sender, &slen);
        if (n <= 0) continue;

        if (!py_client_known) {
            py_client_addr  = sender;
            py_client_known = 1;
            printf("-> [IPC] Python registered on port %d\n",
                   ntohs(sender.sin_port));
            fflush(stdout);
            flush_lan_queue();
        }

        /* Ignore the bare newline registration packet */
        if (n == 1 && buf[0] == '\n') continue;

        pkt_count++;
        if (pkt_count <= 5 || pkt_count % 50 == 0) {
            printf("[IPC] Pkt #%ld from Python (%d bytes) -> Peer? %s\n",
                   pkt_count, n,
                   remote_peer_known ? "YES" : "QUEUED");
            fflush(stdout);
        }

        if (remote_peer_known) {
            sendto(lan_sock, buf, n, 0,
                   (struct sockaddr*)&remote_peer_addr, sizeof(remote_peer_addr));
        } else {
            if (q_py_count < QUEUE_SIZE) {
                int slot = (q_py_head + q_py_count) % QUEUE_SIZE;
                memcpy(q_py[slot], buf, n);
                q_py_len[slot] = n;
                q_py_count++;
            }
        }
    }
    THREAD_RETURN;
}

/* ====================================================================
 * THREAD 3 : HELLO keepalive (Joiner only)
 * Sends 10 HELLO punches 2 s apart to open the NAT hole.
 * ==================================================================== */
static THREAD_RET hello_keepalive_thread(void *arg) {
    (void)arg;
    printf("[LAN] Starting HELLO punch-through...\n");
    fflush(stdout);
    for (int i = 0; i < 10; i++) {
        sendto(lan_sock, "HELLO", 5, 0,
               (struct sockaddr*)&remote_peer_addr, sizeof(remote_peer_addr));
        printf("[LAN] HELLO #%d sent to %s:%d\n",
               i+1, inet_ntoa(remote_peer_addr.sin_addr),
               ntohs(remote_peer_addr.sin_port));
        fflush(stdout);
        SLEEP_MS(2000);
        if (remote_peer_known && hello_reply_sent) break;
    }
    printf("[LAN] HELLO punch-through done.\n");
    fflush(stdout);
    THREAD_RETURN;
}

/* ==================================================================== */
int main(int argc, char *argv[]) {
    char *remote_ip       = NULL;
    int   py_port         = 5000;
    int   lan_port        = 6000;
    int   remote_port     = 6000;

    printf("========== PROXY C REAL IP TEST ==========\n\n");
    print_local_ips();
    printf("\n");

    if (argc >= 2 && strcmp(argv[1],"server") != 0 && strcmp(argv[1],"peer") != 0)
        remote_ip = argv[1];
    if (argc >= 3) py_port     = atoi(argv[2]);
    if (argc >= 4) lan_port    = atoi(argv[3]);
    if (argc >= 5) remote_port = atoi(argv[4]);
    else           remote_port = lan_port;

    init_wsa();

    lan_sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    py_sock  = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (lan_sock == SOCK_INVALID || py_sock == SOCK_INVALID) {
        printf("[!] Socket creation failed.\n"); return 1;
    }

    int opt = 1;
    setsockopt(lan_sock, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));
    setsockopt(py_sock,  SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt));

    /* LAN socket — listen on all interfaces */
    struct sockaddr_in lb; memset(&lb,0,sizeof(lb));
    lb.sin_family = AF_INET; lb.sin_port = htons(lan_port);
    lb.sin_addr.s_addr = INADDR_ANY;
    if (bind(lan_sock,(struct sockaddr*)&lb,sizeof(lb))<0) {
        printf("[!] Cannot bind LAN socket port %d.\n", lan_port); return 1;
    }

    /* Python socket — loopback only */
    struct sockaddr_in pb; memset(&pb,0,sizeof(pb));
    pb.sin_family = AF_INET; pb.sin_port = htons(py_port);
    pb.sin_addr.s_addr = inet_addr("127.0.0.1");
    if (bind(py_sock,(struct sockaddr*)&pb,sizeof(pb))<0) {
        printf("[!] Cannot bind Python socket port %d.\n", py_port); return 1;
    }

    if (remote_ip) {
        memset(&remote_peer_addr,0,sizeof(remote_peer_addr));
        remote_peer_addr.sin_family = AF_INET;
        remote_peer_addr.sin_port   = htons(remote_port);
        inet_pton(AF_INET, remote_ip, &remote_peer_addr.sin_addr);
        remote_peer_known = 1;
        printf("[LAN] Mode: Joiner -> Host %s:%d (listen on :%d)\n",
               remote_ip, remote_port, lan_port);
    } else {
        printf("[LAN] Mode: Host -> Waiting for discovery on port %d\n", lan_port);
    }
    printf("[IPC] Waiting for Python on 127.0.0.1:%d\n", py_port);
    fflush(stdout);

    THREAD_CREATE(lan_to_py_thread, NULL);
    THREAD_CREATE(py_to_lan_thread, NULL);
    if (remote_ip)
        THREAD_CREATE(hello_keepalive_thread, NULL);

    while (1) { SLEEP_MS(1000); }
    return 0;
}
