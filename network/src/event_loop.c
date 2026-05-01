#include <stdio.h>
#include <string.h>
#ifdef _WIN32
    #include <winsock2.h>
    #include <windows.h>
#else
    #include <unistd.h>
    #include <sys/socket.h>
#endif
#include "handlers.h"
#include "peer_manage.h"
#include "protocol.h"
#include "app_context.h"

void run_event_loop(AppContext *ctx) {
    if (!ctx) {
        return;
    }
    if (ctx->peer_fd == INVALID_FD || ctx->python_fd == INVALID_FD) {
        fprintf(stderr, "[event_loop] invalid file descriptor\n");
        return;
    }
    while (ctx->running) {
        fd_set readfds;
        struct timeval timeout;
        FD_ZERO(&readfds);
        FD_SET(ctx->peer_fd, &readfds);
        FD_SET(ctx->python_fd, &readfds);

        socket_t max_fd = (ctx->peer_fd > ctx->python_fd) ? ctx->peer_fd : ctx->python_fd;
        timeout.tv_sec = 1;
        timeout.tv_usec = 0;

        int activity = select( (int)(max_fd + 1), &readfds, NULL, NULL, &timeout);
        if (activity < 0) {
            perror("select");
            ctx->running = 0;
            break;
        }
        if (activity == 0) {
            continue;
        }
        if (FD_ISSET(ctx->peer_fd, &readfds)) {
            handle_peer_data(ctx);
        }
        if (FD_ISSET(ctx->python_fd, &readfds)) {
            handle_python_data(ctx);
        }
    }
}