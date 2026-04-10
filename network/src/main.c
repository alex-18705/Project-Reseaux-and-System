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

#define PEER_PORT   6000
#define PYTHON_PORT 5000
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
        ctx->has_peer_addr = 0;
        ctx->peer_addr_len = 0;
        memset(&ctx->peer_addr, 0, sizeof(ctx->peer_addr));
    }
}

int main(void) {
    AppContext ctx;
    init_app_context(&ctx);

    if (init_socket_system() != 0) {
        return EXIT_FAILURE;
    }

    /*
     * 1. Create server socket for peers
     *    Other machines/peers will connect here
     */
    ctx.peer_fd = create_server_socket(NULL, PEER_PORT);
    if (ctx.peer_fd == INVALID_FD) {
        cleanup_socket_system();
        return EXIT_FAILURE;
    }

    printf("[MAIN] Peer server listening on 0.0.0.0:%d\n", PEER_PORT);

    /*
     * 2. Create local server socket for Python
     *    Python process connects to localhost:5000
     */
    socket_t python_fd = create_server_socket(PYTHON_HOST, PYTHON_PORT);
    if (python_fd == INVALID_FD) {
        cleanup_context(&ctx);
        cleanup_socket_system();
        return EXIT_FAILURE;
    }

    printf("[MAIN] Python local server listening on %s:%d\n", PYTHON_HOST, PYTHON_PORT);

    /*
     * 3. Start main event loop
     */
    ctx.running = 1;
    printf("[MAIN] Starting event loop...\n");
    run_event_loop(&ctx);

    /*
     * 5. Cleanup
     */
    if (ctx.peer_fd != INVALID_FD) {
        CLOSESOCKET(ctx.peer_fd);
    }
    if (ctx.python_fd != INVALID_FD) {
        CLOSESOCKET(ctx.python_fd);
    }

    cleanup_context(&ctx);
    cleanup_socket_system();
    return EXIT_SUCCESS;
}