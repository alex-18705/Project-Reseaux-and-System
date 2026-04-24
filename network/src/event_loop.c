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

void run_event_loop(AppContext *ctx) {
    fd_set readfds;
    while (ctx->running) {
        struct timeval timeout;
        int max_fd;
        FD_ZERO(&readfds);

        max_fd = 0;

        // follow listen_fd for peer connections and python_fd for Python messages
        FD_SET(ctx->peer_fd, &readfds);
        FD_SET(ctx->python_fd, &readfds);

        max_fd = (ctx->peer_fd > ctx->python_fd) ? ctx->peer_fd : ctx->python_fd;
        timeout.tv_sec = 1;
        timeout.tv_usec = 0;
        
        int activity = select (max_fd +1, &readfds, NULL, NULL, &timeout);
        if (activity<0){
            stop("select");
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
