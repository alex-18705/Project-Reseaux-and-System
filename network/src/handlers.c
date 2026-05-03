#include <stdio.h>
#include <string.h>

#include "handlers.h"
#include "ipc.h"
#include "network.h"
#include "peer_manage.h"
#include "protocol.h"

#ifdef _WIN32
#include <winsock2.h>
#else
#include <arpa/inet.h>
#endif

static void remember_peer_from_message(AppContext *ctx, const Message *msg, const struct sockaddr_in *addr, socklen_t addr_len) {
    if (!ctx || !msg || !addr) {
        return;
    }
    if (msg->sender_peer_id[0] != '\0') {
        if (add_or_update_peer(ctx, msg->sender_peer_id, addr, addr_len) < 0) {
            fprintf(stderr, "[handlers] unable to register peer '%s'\n", msg->sender_peer_id);
        }
    } else if (!is_known_peer(ctx, addr, addr_len)) {
        if (add_peer(ctx, addr, addr_len) < 0) {
            fprintf(stderr, "[handlers] unable to register peer by address\n");
        }
    }
}

static int route_to_peer_or_broadcast(AppContext *ctx, const Message *msg, const char *buffer, size_t len){
    if (msg->target_peer_id[0] == '\0') {
        return broadcast_to_peers(ctx, buffer, len);
    }
    return send_to_peer_id(ctx, msg->target_peer_id, buffer, len);
}
static int forward_to_python(AppContext *ctx, const char *buffer, size_t len) {
    int sent;
    if (!ctx || !buffer || len == 0) {
        return -1;
    }
    sent = ipc_send_to_python(ctx, buffer, len);
    if (sent < 0) {
        perror("ipc_send_to_python");
        return -1;
    }
    return sent;
}

static int payload_has_key(const Message *msg, const char *key) {
    char pattern[64];
    if (!msg || !key) {
        return 0;
    }
    snprintf(pattern, sizeof(pattern), "\"%s\"", key);
    return strstr(msg->payload, pattern) != NULL;
}

static int validate_message_payload(const Message *msg) {
    if (!msg) {
        return 0;
    }

    switch (msg->kind) {
        case MSG_STATE_UPDATE:
            return payload_has_key(msg, "seq") && payload_has_key(msg, "state");
        case MSG_OWNERSHIP_REQUEST:
        case MSG_OWNERSHIP_TRANSFER:
        case MSG_OWNERSHIP_DENIED:
        case MSG_OWNERSHIP_RETURN:
            return payload_has_key(msg, "entity_id");
        default:
            return 1;
    }
}

static int forward_to_peers(AppContext *ctx, const Message *msg, const char *buffer, size_t len) {
    if (!ctx || !msg || !buffer || len == 0) {
        return -1;
    }
    if (!validate_message_payload(msg)) {
        fprintf(stderr, "[handlers] invalid payload for message type '%s'\n", msg->type);
        return -1;
    }

    switch (msg->kind) {
        case MSG_JOIN:
            if (msg->sender_peer_id[0] != '\0') {
                strncpy(ctx->local_peer_id, msg->sender_peer_id, sizeof(ctx->local_peer_id) - 1);
                ctx->local_peer_id[sizeof(ctx->local_peer_id) - 1] = '\0';
            }
            return broadcast_to_peers(ctx, buffer, len);

        case MSG_SEND_TO:
        case MSG_OWNERSHIP_REQUEST:
        case MSG_OWNERSHIP_DENIED:
            if (msg->target_peer_id[0] == '\0') {
                fprintf(stderr, "[handlers] message '%s' has no target_peer_id\n", msg->type);
                return -1;
            }
            return send_to_peer_id(ctx, msg->target_peer_id, buffer, len);

        case MSG_OWNERSHIP_TRANSFER:
        case MSG_OWNERSHIP_RETURN:
            return route_to_peer_or_broadcast(ctx, msg, buffer, len);

        case MSG_SHUTDOWN:
            ctx->running = 0;
            return 0;
        
        case MSG_REMOTE_EVENT:
            fprintf(stderr, "[handlers] REMOTE_EVENT should not be sent from Python to peers\n");
            return -1;
        
        case MSG_BROADCAST:
        case MSG_STATE_UPDATE:
        case MSG_PING:
        case MSG_PONG:
            return route_to_peer_or_broadcast(ctx, msg, buffer, len);

            // return broadcast_to_peers(ctx, buffer, len);

        case MSG_UNKNOWN:
        default:
            fprintf(stderr, "[handlers] unknown message type '%s'\n", msg->type);
            return -1;
    }
}

static int is_message_for_local_python(AppContext *ctx, const Message *msg) {
    if (!ctx || !msg) {
        return 0;
    }
    if (msg->target_peer_id[0] == '\0') {
        return 1;
    }
    return ctx->local_peer_id[0] != '\0' && strcmp(msg->target_peer_id, ctx->local_peer_id) == 0;
}

static void relay_peer_message(AppContext *ctx, const Message *msg, const char *buffer, size_t len, const struct sockaddr_in *src_addr) {
    int relayed = 0;
    if (!ctx || !msg || !buffer || len == 0 || !src_addr) {
        return;
    }
    if (msg->sender_peer_id[0] != '\0' && strcmp(msg->sender_peer_id, ctx->local_peer_id) == 0) {
        return;
    }

    if (msg->target_peer_id[0] == '\0') {
        relayed = broadcast_to_peers_except_addr(ctx, buffer, len, src_addr);
    } else if (!is_message_for_local_python(ctx, msg)) {
        relayed = send_to_peer_id_except_addr(ctx, msg->target_peer_id, buffer, len, src_addr);
    }

    if (relayed < 0) {
        fprintf(stderr, "[handlers] unable to relay message type '%s'\n", msg->type);
    }
}

void handle_peer_data(AppContext *ctx) {
    char buffer[BUF_SIZE + 1];
    struct sockaddr_in src_addr;
    socklen_t src_addr_len = sizeof(src_addr);
    Message msg;
    int received;

    if (!ctx) {
        return;
    }

    received = udp_recv_from_addr(ctx->peer_fd, buffer, sizeof(buffer), &src_addr, &src_addr_len);
    if (received < 0) {
         perror("recvfrom peer");
        return;
    }
    if (received == 0) {
        return;
    }

    buffer[received] = '\0';

    if (parse_message(buffer, &msg) != 0) {
        fprintf(stderr, "[handlers] dropping invalid packet from unknown peer %s:%u\n", inet_ntoa(src_addr.sin_addr), (unsigned)ntohs(src_addr.sin_port));
        return;
    }
    if (!validate_message_payload(&msg)) {
        fprintf(stderr, "[handlers] dropping packet with invalid payload for '%s'\n", msg.type);
        return;
    }

    remember_peer_from_message(ctx, &msg, &src_addr, src_addr_len);
    relay_peer_message(ctx, &msg, buffer, (size_t)received, &src_addr);

    if (!is_message_for_local_python(ctx, &msg)) {
        return;
    }

    if (ctx->python_fd == INVALID_FD){
        fprintf(stderr, "[handlers] Python IPC socket is not connected\n");
        return;
    }

    if (forward_to_python(ctx, buffer, (size_t)received) < 0) {
        stop("send to python");
    }
}

void handle_python_data(AppContext *ctx) {
    char buffer[BUF_SIZE + 1];
    Message msg;
    int received;

    if (!ctx) {
        return;
    }

    received = ipc_recv_from_python(ctx, buffer, sizeof(buffer));
    if (received < 0) {
        fprintf(stderr, "[handlers] Python IPC receive error, stopping proxy\n");
        ctx->running = 0;
        return;
    }
    if (received == 0) {
        printf("[handlers] Python disconnected\n");
        ctx->running = 0;
        return;
    }

    if (parse_message(buffer, &msg) != 0) {
        fprintf(stderr, "[handlers] invalid message from Python: %s\n", buffer);
        return;
    }

    if (forward_to_peers(ctx, &msg, buffer, (size_t)received) < 0) {
        fprintf(stderr, "[handlers] unable to forward message type '%s'\n", msg.type);
    }
}
