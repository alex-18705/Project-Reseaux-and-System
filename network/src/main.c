/*
Build on Windows (MinGW/MSYS2):
    gcc -Wall main.c peer_manage.c handlers.c event_loop.c protocol.c -I../includes -o proxy -lws2_32

Run two proxies on the same machine for local testing:
    ./proxy.exe 5001 9001 127.0.0.1 9000
    ./proxy.exe 5000 9000 127.0.0.1 9001

Run Python test apps in another two terminals:
    python -u ../test/test_app_remote.py 127.0.0.1 5001
    python -u ../test/test_app_local.py 127.0.0.1 5000

Program arguments:
    <python_port> <peer_port> <peer1_ip> <peer1_port> [<peer2_ip> <peer2_port> ...]

Example:
    ./proxy.exe 5000 9000 127.0.0.1 9001 127.0.0.1 9002
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #define CLOSESOCKET closesocket
    // #pragma comment(lib, "ws2_32.lib")
#else
    #include <unistd.h>
    #include <arpa/inet.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
    #define CLOSESOCKET close
#endif

#include "app_context.h"
#include "event_loop.h"
#include "peer_manage.h"

#define PYTHON_HOST "127.0.0.1"


static int init_socket_system(void) {
#ifdef _WIN32
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        fprintf(stderr, "WSAStartup failed\n");
        return -1;
    }
#endif
    return 0;
}

static void cleanup_socket_system(void) {
#ifdef _WIN32
    WSACleanup();
#endif
}

static socket_t create_server_socket(const char *bind_ip, int port) {
    socket_t server_fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (server_fd == INVALID_FD) {
        stop("socket");
    }

    int opt = 1;
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, (char*)&opt, sizeof(opt)) < 0) {
        perror("setsockopt");
        CLOSESOCKET(server_fd);
        return INVALID_FD;
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);

    if (bind_ip == NULL) {
        addr.sin_addr.s_addr = INADDR_ANY;
    } else {
        if (inet_pton(AF_INET, bind_ip, &addr.sin_addr) <= 0) {
            fprintf(stderr, "Invalid bind IP: %s\n", bind_ip);
            CLOSESOCKET(server_fd);
            return INVALID_FD;
        }
    }

    if (bind(server_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        perror("bind");
        CLOSESOCKET(server_fd);
        return INVALID_FD;
    }

    return server_fd;
}

static int parse_port(const char *value, const char *name) {
    char *endptr = NULL;
    long port = strtol(value, &endptr, 10);

    if (!value || *value == '\0' || (endptr && *endptr != '\0') || port < 1 || port > 65535) {
        fprintf(stderr, "Invalid %s: %s\n", name, value ? value : "(null)");
        return -1;
    }

    return (int)port;
}

static int register_remote_peer(AppContext *ctx, const char *remote_ip, int remote_peer_port) {
    struct sockaddr_in peer_addr;

    memset(&peer_addr, 0, sizeof(peer_addr));
    peer_addr.sin_family = AF_INET;
    peer_addr.sin_port = htons(remote_peer_port);

    if (inet_pton(AF_INET, remote_ip, &peer_addr.sin_addr) <= 0) {
        fprintf(stderr, "Invalid remote peer IP: %s\n", remote_ip);
        return -1;
    }

    if (add_peer(ctx, &peer_addr, sizeof(peer_addr)) != 0) {
        fprintf(stderr, "Unable to register remote peer %s:%d\n", remote_ip, remote_peer_port);
        return -1;
    }

    return 0;
}

static void cleanup_context(AppContext *ctx) {
    if (!ctx){
        return;
    }

    if (ctx->python_fd != INVALID_FD) {
        CLOSESOCKET(ctx->python_fd);
        ctx->python_fd = INVALID_FD;
        ctx->has_python_addr = 0;
        ctx->python_addr_len = 0;
        memset(&ctx->python_addr, 0, sizeof(ctx->python_addr));
    }

    if (ctx->peer_fd != INVALID_FD) {
        CLOSESOCKET(ctx->peer_fd);
        ctx->peer_fd = INVALID_FD;
        ctx->peer_count = 0;
        memset(&ctx->peers, 0, sizeof(ctx->peers));
    }
}

int main(int argc, char **argv) {
    AppContext ctx;
    int python_port;
    int peer_port;

    if (argc < 5 || ((argc -3) %2 !=0)) {
        fprintf(stderr,  "Usage: %s <python_port> <peer_port> <peer1_ip> <peer1_port> [<peer2_ip> <peer2_port> ...]\n", argv[0]);
        fprintf(stderr, "Example: %s 5000 9000 127.0.0.1 9001 127.0.0.1 9002\n", argv[0]);
        return EXIT_FAILURE;
    }

    init_app_context(&ctx);

    python_port = parse_port(argv[1], "python_port");
    peer_port = parse_port(argv[2], "peer_port");

    if (python_port < 0 || peer_port < 0) {
        return EXIT_FAILURE;
    }

    if (init_socket_system() != 0) {
        return EXIT_FAILURE;
    }

    /*
     * 1. Create server socket for peers
     *    Other machines/peers will connect here
     */
    ctx.peer_fd = create_server_socket(NULL, peer_port);
    if (ctx.peer_fd == INVALID_FD) {
        cleanup_socket_system();
        return EXIT_FAILURE;
    }

    printf("[MAIN] Peer UDP socket listening on 0.0.0.0:%d\n", peer_port);

    /*
     * 2. Create local server socket for Python
     *    Python process connects to localhost:5000
     */
    ctx.python_fd = create_server_socket(PYTHON_HOST, python_port);
    if (ctx.python_fd == INVALID_FD) {
        cleanup_context(&ctx);
        cleanup_socket_system();
        return EXIT_FAILURE;
    }

    printf("[MAIN] Python UDP socket listening on %s:%d\n", PYTHON_HOST, python_port);

    for (int i = 3; i < argc; i += 2) {
        const char *peer_ip = argv[i];
        int remote_peer_port = parse_port(argv[i + 1], "remote_peer_port");

        if (remote_peer_port < 0 || register_remote_peer(&ctx, peer_ip, remote_peer_port) != 0) {
            cleanup_context(&ctx);
            cleanup_socket_system();
            return EXIT_FAILURE;
        }

        printf("[MAIN] Remote peer configured as %s:%d\n", peer_ip, remote_peer_port);
    }

    /*
     * 3. Start main event loop
     */
    ctx.running = 1;
    printf("[MAIN] Starting event loop...\n");
    run_event_loop(&ctx);

    /*
     * 5. Cleanup
     */
    cleanup_context(&ctx);
    cleanup_socket_system();
    return EXIT_SUCCESS;
}
