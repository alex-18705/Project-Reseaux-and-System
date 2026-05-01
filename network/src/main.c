/*
Build on Linux:
    gcc -Wall main.c app_context.c network.c ipc.c peer_manage.c handlers.c event_loop.c protocol.c -I../includes -o proxy

Build on Windows (MinGW/MSYS2):
    gcc -Wall main.c app_context.c network.c ipc.c peer_manage.c handlers.c event_loop.c protocol.c -I../includes -o proxy.exe -lws2_32

Run example:
    ./proxy player_A 5000 9000 player_B 127.0.0.1 9001
    ./proxy player_B 5001 9001 player_A 127.0.0.1 9000

Arguments:
    <local_peer_id> <python_ipc_port> <udp_peer_port> [<peer_id> <peer_ip> <peer_udp_port> ...]

Example:
    ./proxy player_A 5000 9000 player_B 127.0.0.1 9001
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
#else
    #include <unistd.h>
    #include <arpa/inet.h>
    #include <sys/socket.h>
    #include <netinet/in.h>
#endif

#include "app_context.h"
#include "event_loop.h"
#include "ipc.h"
#include "network.h"
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

static int parse_port(const char *value, const char *name) {
    char *endptr = NULL;
    long port;

    if (!value || value[0] == '\0') {
        fprintf(stderr, "Invalid %s: empty value\n", name);
        return -1;
    }

    port = strtol(value, &endptr, 10);

    if ((endptr && *endptr != '\0') || port < 1 || port > 65535) {
        fprintf(stderr, "Invalid %s: %s\n", name, value);
        return -1;
    }

    return (int)port;
}

static int register_remote_peer(
    AppContext *ctx,
    const char *peer_id,
    const char *remote_ip,
    int remote_peer_port
) {
    struct sockaddr_in peer_addr;

    if (!ctx || !peer_id || !remote_ip) {
        return -1;
    }

    memset(&peer_addr, 0, sizeof(peer_addr));
    peer_addr.sin_family = AF_INET;
    peer_addr.sin_port = htons((unsigned short)remote_peer_port);

    if (inet_pton(AF_INET, remote_ip, &peer_addr.sin_addr) <= 0) {
        fprintf(stderr, "Invalid remote peer IP: %s\n", remote_ip);
        return -1;
    }

    if (add_or_update_peer(ctx, peer_id, &peer_addr, sizeof(peer_addr)) < 0) {
        fprintf(
            stderr,
            "Unable to register remote peer %s at %s:%d\n",
            peer_id,
            remote_ip,
            remote_peer_port
        );
        return -1;
    }

    return 0;
}

static void cleanup_context(AppContext *ctx) {
    if (!ctx) {
        return;
    }

    if (ctx->python_fd != INVALID_FD) {
        ipc_close_socket(ctx->python_fd);
        ctx->python_fd = INVALID_FD;
    }

    if (ctx->peer_fd != INVALID_FD) {
        udp_close_socket(ctx->peer_fd);
        ctx->peer_fd = INVALID_FD;
    }

    ctx->peer_count = 0;
    memset(ctx->peers, 0, sizeof(ctx->peers));
}

static void print_usage(const char *program) {
    fprintf(
        stderr,
        "Usage:\n"
        "  %s <local_peer_id> <python_ipc_port> <udp_peer_port> "
        "[<peer_id> <peer_ip> <peer_udp_port> ...]\n\n"
        "Examples:\n"
        "  %s player_A 5000 9000 player_B 127.0.0.1 9001\n"
        "  %s player_B 5001 9001 player_A 127.0.0.1 9000\n",
        program,
        program,
        program
    );
}

int main(int argc, char **argv) {
    AppContext ctx;
    socket_t ipc_listen_fd = INVALID_FD;

    const char *local_peer_id;
    int python_port;
    int peer_port;

    /*
     * Required:
     *   argv[1] = local_peer_id
     *   argv[2] = python_ipc_port
     *   argv[3] = udp_peer_port
     *
     * Optional peers in groups of 3:
     *   peer_id peer_ip peer_udp_port
     */
    if (argc < 4 || ((argc - 4) % 3 != 0)) {
        print_usage(argv[0]);
        return EXIT_FAILURE;
    }

    local_peer_id = argv[1];

    python_port = parse_port(argv[2], "python_ipc_port");
    peer_port = parse_port(argv[3], "udp_peer_port");

    if (python_port < 0 || peer_port < 0) {
        return EXIT_FAILURE;
    }

    if (init_socket_system() != 0) {
        return EXIT_FAILURE;
    }

    init_app_context(&ctx);
    strncpy(ctx.local_peer_id, local_peer_id, PEER_ID_SIZE - 1);
    ctx.local_peer_id[PEER_ID_SIZE - 1] = '\0';

    /*
     * 1. Create UDP socket for inter-proxy peer network.
     */
    ctx.peer_fd = udp_create_socket(NULL, peer_port);
    if (ctx.peer_fd == INVALID_FD) {
        cleanup_context(&ctx);
        cleanup_socket_system();
        return EXIT_FAILURE;
    }

    printf(
        "[MAIN] Local peer_id=%s\n",
        ctx.local_peer_id
    );

    printf(
        "[MAIN] UDP peer socket listening on 0.0.0.0:%d\n",
        peer_port
    );

    /*
     * 2. Register initial remote peers from CLI.
     */
    for (int i = 4; i < argc; i += 3) {
        const char *peer_id = argv[i];
        const char *peer_ip = argv[i + 1];
        int remote_peer_port = parse_port(argv[i + 2], "remote_peer_port");

        if (
            remote_peer_port < 0 ||
            register_remote_peer(&ctx, peer_id, peer_ip, remote_peer_port) != 0
        ) {
            cleanup_context(&ctx);
            cleanup_socket_system();
            return EXIT_FAILURE;
        }

        printf(
            "[MAIN] Remote peer configured: %s -> %s:%d\n",
            peer_id,
            peer_ip,
            remote_peer_port
        );
    }

    /*
     * 3. Create TCP localhost IPC server for Python process.
     */
    ipc_listen_fd = ipc_create_server(PYTHON_HOST, python_port);
    if (ipc_listen_fd == INVALID_FD) {
        cleanup_context(&ctx);
        cleanup_socket_system();
        return EXIT_FAILURE;
    }

    printf(
        "[MAIN] Python TCP IPC listening on %s:%d\n",
        PYTHON_HOST,
        python_port
    );

    /*
     * 4. Wait for Python process connection.
     */
    printf("[MAIN] Waiting for Python IPC connection...\n");

    ctx.python_fd = ipc_accept_python(ipc_listen_fd);

    ipc_close_socket(ipc_listen_fd);
    ipc_listen_fd = INVALID_FD;

    if (ctx.python_fd == INVALID_FD) {
        cleanup_context(&ctx);
        cleanup_socket_system();
        return EXIT_FAILURE;
    }

    printf("[MAIN] Python IPC connected\n");

    /*
     * 5. Start event loop.
     */
    ctx.running = 1;
    printf("[MAIN] Starting event loop...\n");

    run_event_loop(&ctx);

    /*
     * 6. Cleanup.
     */
    printf("[MAIN] Stopping proxy...\n");

    cleanup_context(&ctx);

    if (ipc_listen_fd != INVALID_FD) {
        ipc_close_socket(ipc_listen_fd);
    }

    cleanup_socket_system();

    return EXIT_SUCCESS;
}
