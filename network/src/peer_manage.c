#include <string.h>

#include "app_context.h"
#include "peer_manage.h"

#ifdef _WIN32
#include <winsock2.h>
#else
#include <sys/socket.h>
#endif


void init_app_context(AppContext *ctx) {
    if (!ctx) {
        return;
    }

    memset(ctx, 0, sizeof(*ctx));
    ctx->peer_fd = INVALID_FD;
    ctx->python_fd = INVALID_FD;
    ctx->peer_addr_len = sizeof(ctx->peer_addr);
    ctx->python_addr_len = sizeof(ctx->python_addr);
    ctx->running = 1;
}


void stop(const char *msg) {
    perror(msg);
    exit(1);
}


void set_peer_addr(AppContext *ctx, const struct sockaddr_in *addr, socklen_t addr_len) {
    if (!ctx || !addr) {
        return;
    }

    ctx->peer_addr = *addr;
    ctx->peer_addr_len = addr_len;
    ctx->has_peer_addr = 1;
}


void set_python_addr(AppContext *ctx, const struct sockaddr_in *addr, socklen_t addr_len) {
    if (!ctx || !addr) {
        return;
    }

    ctx->python_addr = *addr;
    ctx->python_addr_len = addr_len;
    ctx->has_python_addr = 1;
}


int send_to_peer(AppContext *ctx, const char *msg, size_t len) {
    if (!ctx || !msg || !ctx->has_peer_addr) {
        return -1;
    }

    return sendto(
        ctx->peer_fd,
        msg,
        (int)len,
        0,
        (const struct sockaddr *)&ctx->peer_addr,
        ctx->peer_addr_len
    );
}


int send_to_python(AppContext *ctx, const char *msg, size_t len) {
    if (!ctx || !msg || !ctx->has_python_addr) {
        return -1;
    }

    return sendto(
        ctx->python_fd,
        msg,
        (int)len,
        0,
        (const struct sockaddr *)&ctx->python_addr,
        ctx->python_addr_len
    );
}
