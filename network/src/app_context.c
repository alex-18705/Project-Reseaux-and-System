#include <string.h>

#include "app_context.h"

void init_app_context(AppContext *ctx) {
    if (!ctx) {
        return;
    }               
    memset(ctx, 0, sizeof(AppContext));
    ctx->peer_fd = INVALID_FD;
    ctx->python_fd = INVALID_FD;
    ctx->peer_count = 0;
    ctx->running = 1;
    strncpy(ctx->local_peer_id, "unknown_peer", PEER_ID_SIZE - 1);
    ctx->local_peer_id[PEER_ID_SIZE - 1] = '\0';
    for (int i = 0; i < MAX_PEERS; i++) {
        ctx->peers[i].peer_id[0] = '\0';
        ctx->peers[i].addr_len = sizeof(struct sockaddr_in);
        ctx->peers[i].active = 0;
    }
}

void stop(const char *msg) {
    perror(msg);
    exit(EXIT_FAILURE);
}
