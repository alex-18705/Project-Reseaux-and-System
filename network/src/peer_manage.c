#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include "app_context.h"
#include "peer_manage.h"
#include "network.h"

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>
#endif


static int same_peer_addr(const struct sockaddr_in *lhs, const struct sockaddr_in *rhs) {
    if (!lhs || !rhs) {
        return 0;
    }
    return lhs->sin_family == rhs->sin_family && lhs->sin_port == rhs->sin_port && lhs->sin_addr.s_addr == rhs->sin_addr.s_addr;
}

static void copy_peer_id(char *dst, size_t dst_size, const char *peer_id) {
    if (!dst || dst_size == 0) {
        return;
    }
    if (!peer_id) {
        dst[0] = '\0';
        return;
    }
    strncpy(dst, peer_id, dst_size - 1);
    dst[dst_size - 1] = '\0';
}

static void make_addr_peer_id(char *dst, size_t dst_size, const struct sockaddr_in *addr) {
    const char *ip;
    uint16_t port;
    if (!dst || dst_size == 0) {
        return;
    }
    dst[0] = '\0';
    if (!addr) {
        return;
    }
    ip = inet_ntoa(addr->sin_addr);
    port = ntohs(addr->sin_port);
    snprintf(dst, dst_size, "%s:%u", ip ? ip : "0.0.0.0", (unsigned)port);
}

static int find_peer_by_addr(const AppContext *ctx, const struct sockaddr_in *addr) {
    int i;
    if (!ctx || !addr) {
        return -1;
    }
    for (i = 0; i < ctx->peer_count; ++i) {
        if (ctx->peers[i].active && same_peer_addr(&ctx->peers[i].addr, addr)) {
            return i;
        }
    }
    return -1;
}

static int first_free_peer_slot(AppContext *ctx) {
    int i;
    if (!ctx) {
        return -1;
    }
    for (i = 0; i < ctx->peer_count; ++i) {
        if (!ctx->peers[i].active) {
            return i;
        }
    }
    if (ctx->peer_count >= MAX_PEERS) {
        return -1;
    }
    return ctx->peer_count++;
}

int find_peer_by_id(const AppContext *ctx, const char *peer_id) {
    int i;
    if (!ctx || !peer_id || peer_id[0] == '\0') {
        return -1;
    }
    for (i = 0; i < ctx->peer_count; ++i) {
        if (ctx->peers[i].active && strcmp(ctx->peers[i].peer_id, peer_id) == 0) {
            return i;
        }
    }
    return -1;
}

int add_or_update_peer(AppContext *ctx, const char *peer_id, const struct sockaddr_in *addr, socklen_t addr_len) {
    int index;
    if (!ctx || !peer_id || peer_id[0] == '\0' || !addr) {
        return -1;
    }
    index = find_peer_by_id(ctx, peer_id);
    if (index < 0) {
        index = find_peer_by_addr(ctx, addr);
    }
    if (index < 0) {
        index = first_free_peer_slot(ctx);
    }
    if (index < 0) {
        return -1;
    }
    copy_peer_id(ctx->peers[index].peer_id, sizeof(ctx->peers[index].peer_id), peer_id);
    ctx->peers[index].addr = *addr;
    ctx->peers[index].addr_len = addr_len;
    ctx->peers[index].active = 1;
    return index;
}

int add_peer(AppContext *ctx, const struct sockaddr_in *addr, socklen_t addr_len) {
    char peer_id[sizeof(ctx->peers[0].peer_id)];
    if (!ctx || !addr) {
        return -1;
    }
    make_addr_peer_id(peer_id, sizeof(peer_id), addr);
    return add_or_update_peer(ctx, peer_id, addr, addr_len) < 0 ? -1 : 0;
}

int is_known_peer(const AppContext *ctx, const struct sockaddr_in *addr, socklen_t addr_len) {
    (void)addr_len;
    if (find_peer_by_addr(ctx, addr) >=0){
        return 1;
    }
    return 0;
}

static int send_to_peer_index(AppContext *ctx, int peer_index, const char *msg, size_t len) {
    if (!ctx || !msg || len == 0 || peer_index < 0 || peer_index >= ctx->peer_count) {
        return -1;
    }
    if (!ctx->peers[peer_index].active) {
        return -1;
    }
    return udp_send_to_addr(ctx->peer_fd, msg, len, &ctx->peers[peer_index].addr, ctx->peers[peer_index].addr_len);
}

int send_to_peer_id(AppContext *ctx, const char *peer_id, const char *msg, size_t len) {
    int index = find_peer_by_id(ctx, peer_id);
    if (index < 0) {
        return -1;
    }
    return send_to_peer_index(ctx, index, msg, len);
}

int send_to_peer_id_except_addr(
    AppContext *ctx,
    const char *peer_id,
    const char *msg,
    size_t len,
    const struct sockaddr_in *excluded_addr
) {
    int index = find_peer_by_id(ctx, peer_id);
    if (index < 0) {
        return -1;
    }
    if (excluded_addr && same_peer_addr(&ctx->peers[index].addr, excluded_addr)) {
        return 0;
    }
    return send_to_peer_index(ctx, index, msg, len);
}

int broadcast_to_peers(AppContext *ctx, const char *msg, size_t len) {
    int i;
    int sent_count = 0;
    if (!ctx || !msg || len == 0) {
        return -1;
    }
    for (i = 0; i < ctx->peer_count; ++i) {
        if (!ctx->peers[i].active) {
            continue;
        }
        if (ctx->local_peer_id[0] != '\0' && strcmp(ctx->peers[i].peer_id, ctx->local_peer_id) == 0) {
            continue;
        }
        if (send_to_peer_index(ctx, i, msg, len) >= 0) {
            sent_count++;
        }
    }
    return sent_count;
}

int broadcast_to_peers_except_addr(
    AppContext *ctx,
    const char *msg,
    size_t len,
    const struct sockaddr_in *excluded_addr
) {
    int i;
    int sent_count = 0;
    if (!ctx || !msg || len == 0) {
        return -1;
    }
    for (i = 0; i < ctx->peer_count; ++i) {
        if (!ctx->peers[i].active) {
            continue;
        }
        if (ctx->local_peer_id[0] != '\0' && strcmp(ctx->peers[i].peer_id, ctx->local_peer_id) == 0) {
            continue;
        }
        if (excluded_addr && same_peer_addr(&ctx->peers[i].addr, excluded_addr)) {
            continue;
        }
        if (send_to_peer_index(ctx, i, msg, len) >= 0) {
            sent_count++;
        }
    }
    return sent_count;
}
