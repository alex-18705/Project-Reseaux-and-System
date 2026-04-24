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
    ctx->python_addr_len = sizeof(ctx->python_addr);
    ctx->peer_count = 0;
    ctx->running = 1;
}


void stop(const char *msg) {
    perror(msg);
    exit(1);
}


static int same_peer(const struct sockaddr_in *lhs, const struct sockaddr_in *rhs) {
    return lhs->sin_family == rhs->sin_family
        && lhs->sin_port == rhs->sin_port
        && lhs->sin_addr.s_addr == rhs->sin_addr.s_addr;
}

int is_known_peer(const AppContext *ctx, const struct sockaddr_in *addr, socklen_t addr_len) {
    int i;

    if (!ctx || !addr) {
        return 0;
    }

    for (i = 0; i < ctx->peer_count; ++i) {
        if (!ctx->peers[i].active) {
            continue;
        }
        if (ctx->peers[i].addr_len == addr_len && same_peer(&ctx->peers[i].addr, addr)) {
            return 1;
        }
    }

    return 0;
}

int add_peer(AppContext *ctx, const struct sockaddr_in *addr, socklen_t addr_len) {
    if (!ctx || !addr) {
        return -1;
    }

    if (is_known_peer(ctx, addr, addr_len)) {
        return 0;
    }

    if (ctx->peer_count >= MAX_PEERS) {
        return -1;
    }

    ctx->peers[ctx->peer_count].addr = *addr;
    ctx->peers[ctx->peer_count].addr_len = addr_len;
    ctx->peers[ctx->peer_count].active = 1;
    ctx->peer_count++;
    return 0;
}


void set_python_addr(AppContext *ctx, const struct sockaddr_in *addr, socklen_t addr_len) {
    if (!ctx || !addr) {
        return;
    }

    ctx->python_addr = *addr;
    ctx->python_addr_len = addr_len;
    ctx->has_python_addr = 1;
}


int send_to_peer(AppContext *ctx, int peer_index, const char *msg, size_t len) {
    if (!ctx || !msg || peer_index < 0 || peer_index >= ctx->peer_count || !ctx->peers[peer_index].active) {
        return -1;
    }

    return sendto(
        ctx->peer_fd,
        msg,
        (int)len,
        0,
        (const struct sockaddr *)&ctx->peers[peer_index].addr,
        ctx->peers[peer_index].addr_len
    );
}

int broadcast_to_peers(AppContext *ctx, const char *msg, size_t len) {
    int i;
    int sent = 0;

    if (!ctx || !msg) {
        return -1;
    }

    for (i = 0; i < ctx->peer_count; ++i) {
        if (!ctx->peers[i].active) {
            continue;
        }
        if (send_to_peer(ctx, i, msg, len) < 0) {
            return -1;
        }
        sent++;
    }

    return sent;
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
