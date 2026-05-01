# CHECK_V1_V2.md — Distributed AI Battle Game Network Audit

## Project Architecture

```text
Python AI/Game
    ↕ TCP localhost (IPC)
C Proxy
    ↕ UDP LAN
Other C Proxies / Peers
```

The project is a peer-to-peer distributed AI battle game.

Each peer runs:

- one Python process for AI and game logic
- one C process for IPC and network routing
- TCP localhost between Python and C
- UDP between C proxies
- JSON messages
- no central server

---

# Version 1 — Core Networking Checklist

Version 1 validates the minimum distributed networking layer.

Expected goal:

```text
Python local ↔ C proxy local ↔ UDP ↔ C proxy remote ↔ Python remote
```

For multi-peer testing:

```text
peer_1 ↔ peer_2 ↔ peer_3
```

---

## 1. IPC Layer: Python ↔ C Proxy

### Requirements

- [ ] Python connects to C proxy through TCP localhost.
- [ ] C proxy listens on a TCP localhost port.
- [ ] Python can send JSON messages to C.
- [ ] C can send JSON messages back to Python.
- [ ] Messages use newline framing: `\n`.
- [ ] Python receive loop runs in a separate thread.
- [ ] C event loop can detect Python messages.
- [ ] Disconnect is handled cleanly.

### Test

```text
1. Start C proxy.
2. Start Python NetworkBridge.
3. Send JOIN from Python.
4. Verify C proxy receives and parses JOIN.
5. Send a test message from C to Python.
6. Verify Python receives it in get_updates().
```

### Potential Bugs

- [ ] Python uses TCP but C expects UDP.
- [ ] Python sends newline-delimited JSON but C does not parse by line.
- [ ] C sends raw JSON without `\n`, causing Python recv buffer to wait.
- [ ] `recv()` blocks forever.
- [ ] socket closes without graceful cleanup.
- [ ] multiple Python clients accidentally connect to same proxy port.

---

## 2. UDP Layer: C Proxy ↔ C Proxy

### Requirements

- [ ] C proxy opens a UDP socket.
- [ ] C proxy binds to a LAN port.
- [ ] C proxy can send UDP packets to another proxy.
- [ ] C proxy can receive UDP packets from another proxy.
- [ ] UDP receive loop is non-blocking or integrated into event loop.
- [ ] UDP address and port are stored correctly.

### Test

```text
peer_1 sends UDP packet to peer_2
peer_2 receives it
peer_2 sends response
peer_1 receives response
```

### Potential Bugs

- [ ] wrong IP address used.
- [ ] wrong UDP port used.
- [ ] firewall blocks UDP.
- [ ] two proxies bind the same port on the same machine.
- [ ] UDP socket receives packets but handler is never called.
- [ ] `sendto()` return value is not checked.

---

## 3. Message Protocol V1

### Required Message Types

For Version 1, recommended minimal types:

```c
JOIN
STATE_UPDATE
PING
PONG
SHUTDOWN
```

### Required JSON Format

```json
{
  "type": "STATE_UPDATE",
  "sender_id": "peer_1",
  "target_peer_id": "",
  "payload": {
    "seq": 42,
    "state": {}
  }
}
```

### Requirements

- [ ] every message has `type`.
- [ ] every message has `sender_id`.
- [ ] every message has `target_peer_id`.
- [ ] broadcast uses `target_peer_id == ""`.
- [ ] `STATE_UPDATE` includes `payload.seq`.
- [ ] `STATE_UPDATE` includes `payload.state`.

### Potential Bugs

- [ ] Python and C use different field names.
- [ ] sequence number is sometimes inside payload and sometimes outside.
- [ ] C parser assumes fixed JSON order.
- [ ] malformed JSON crashes proxy.
- [ ] missing `sender_id` prevents per-peer filtering.

---

## 4. Peer Manager V1

### Requirements

- [ ] peer table supports at least 3 peers.
- [ ] each peer has a unique `peer_id`.
- [ ] each peer stores UDP IP and port.
- [ ] peer can be added on JOIN.
- [ ] peer can be found by `peer_id`.
- [ ] inactive peers can be removed or ignored.
- [ ] duplicate JOIN does not create duplicate peer entries.

### Example Peer Table

```text
peer_id    ip              udp_port    active
peer_1     192.168.1.10    6000        yes
peer_2     192.168.1.11    6000        yes
peer_3     192.168.1.12    6000        yes
```

### Potential Bugs

- [ ] only one `remote_peer_addr` is stored.
- [ ] new peer overwrites old peer.
- [ ] peer_id is not linked to UDP address.
- [ ] disconnected peers remain forever.
- [ ] broadcast sends to inactive peers.

---

## 5. Routing Logic V1

### Expected Logic

```text
if target_peer_id == "":
    broadcast to all peers except sender
else:
    send only to target_peer_id
```

### Requirements

- [ ] broadcast supported.
- [ ] direct send supported.
- [ ] sender does not receive its own broadcast.
- [ ] unknown target is handled safely.
- [ ] invalid message is dropped safely.

### Test: 3 Peers

```text
peer_1 sends STATE_UPDATE with target_peer_id=""
Expected:
- peer_2 receives it
- peer_3 receives it
- peer_1 does not apply its own update again
```

### Potential Bugs

- [ ] broadcast only reaches one peer.
- [ ] peer receives its own update and duplicates state.
- [ ] broadcast loop happens between proxies.
- [ ] target_peer_id is ignored.
- [ ] unknown peer causes crash.

---

## 6. STATE_UPDATE Synchronization V1

### Requirements

- [ ] Python AI/game periodically generates state.
- [ ] Python sends `STATE_UPDATE`.
- [ ] C proxy forwards `STATE_UPDATE`.
- [ ] remote Python receives `STATE_UPDATE`.
- [ ] remote game applies remote state.
- [ ] outdated packets are discarded.
- [ ] sequence filtering is per sender.

### Correct Sequence Key

```text
(sender_id, message_type)
```

### Test

```text
peer_1 sends seq=1
peer_1 sends seq=2
peer_1 sends delayed seq=1 again

Expected:
seq=1 accepted first time
seq=2 accepted
delayed seq=1 ignored
```

### Potential Bugs

- [ ] global sequence number rejects valid updates from other peers.
- [ ] old state overwrites new state.
- [ ] missing seq makes filtering impossible.
- [ ] peer reconnects and seq resets, causing updates to be ignored.

---

## 7. Python NetworkBridge V1

### Requirements

- [ ] `connect()` implemented.
- [ ] `send_message()` implemented.
- [ ] `send_state_update()` implemented.
- [ ] `get_updates()` implemented.
- [ ] `disconnect()` implemented.
- [ ] receive thread implemented.
- [ ] incoming queue implemented.
- [ ] sequence filtering implemented.

### Recommended Minimal API

```python
bridge = NetworkBridge(peer_id="peer_1")
bridge.connect()
bridge.join()
bridge.send_state_update(state)
updates = bridge.get_updates()
bridge.disconnect()
```

### Potential Bugs

- [ ] bridge expects TCP but proxy uses UDP.
- [ ] bridge does not start proxy or proxy is not already running.
- [ ] recv buffer splits JSON message.
- [ ] send_message does not append newline.
- [ ] disconnect closes socket while thread is reading.

---

## 8. C Proxy V1

### Requirements

- [ ] initializes context.
- [ ] initializes IPC TCP socket.
- [ ] initializes UDP socket.
- [ ] runs event loop.
- [ ] parses Python messages.
- [ ] parses UDP peer messages.
- [ ] forwards Python → UDP.
- [ ] forwards UDP → Python.
- [ ] uses peer_manager.
- [ ] handles invalid input safely.

### Potential Bugs

- [ ] event loop watches wrong file descriptors.
- [ ] Python fd not registered.
- [ ] UDP fd not registered.
- [ ] C parser fails on compact JSON.
- [ ] buffer is not null-terminated before parsing.
- [ ] `send()` or `sendto()` partial/error not handled.

---

# Version 1 Final Validation

Mark complete only if all are true:

- [ ] Python ↔ C IPC works.
- [ ] C ↔ C UDP works.
- [ ] JSON protocol is consistent.
- [ ] at least 3 peers can be stored.
- [ ] broadcast works.
- [ ] direct routing works.
- [ ] STATE_UPDATE sync works.
- [ ] out-of-order STATE_UPDATE is ignored.
- [ ] invalid JSON does not crash proxy.
- [ ] clean shutdown works.

Result:

```text
[ ] Version 1 complete
[ ] Version 1 incomplete
```

---

# Version 2 — Ownership and Distributed Authority Checklist

Version 2 validates distributed ownership of game entities.

Version 1 synchronizes state.

Version 2 decides which peer has authority over which entity.

Example:

```text
peer_1 owns army_1
peer_2 owns army_2
peer_3 observes both
```

A peer should not freely modify an entity it does not own unless ownership is transferred.

---

## 9. Ownership Model V2

### Required Message Types

```c
OWNERSHIP_REQUEST
OWNERSHIP_TRANSFER
OWNERSHIP_DENIED
OWNERSHIP_RETURN
STATE_UPDATE
```

### Recommended Ownership Fields

```json
{
  "type": "OWNERSHIP_REQUEST",
  "sender_id": "peer_2",
  "target_peer_id": "peer_1",
  "payload": {
    "entity_id": "army_1",
    "reason": "combat_interaction"
  }
}
```

### Requirements

- [ ] each entity has an owner.
- [ ] owner is identified by `owner_peer_id`.
- [ ] only owner can authoritatively update an entity.
- [ ] non-owner must request ownership before modifying entity.
- [ ] ownership state is stored locally.
- [ ] ownership changes are propagated to peers.

### Potential Bugs

- [ ] two peers believe they own the same entity.
- [ ] entity has no owner.
- [ ] ownership transfer is accepted without validation.
- [ ] old ownership state overwrites new ownership state.
- [ ] peer modifies remote-owned entity directly.

---

## 10. OWNERSHIP_REQUEST V2

### Expected Behavior

```text
peer_2 wants to control entity owned by peer_1
peer_2 sends OWNERSHIP_REQUEST to peer_1
```

### Requirements

- [ ] request includes `entity_id`.
- [ ] request includes sender.
- [ ] request targets current owner.
- [ ] owner checks whether transfer is allowed.
- [ ] duplicate requests are handled safely.

### Test

```text
peer_2 requests ownership of army_1 from peer_1
peer_1 receives request
peer_1 decides transfer or deny
```

### Potential Bugs

- [ ] request sent to wrong peer.
- [ ] request accepted by non-owner.
- [ ] repeated requests flood the network.
- [ ] missing entity_id crashes handler.

---

## 11. OWNERSHIP_TRANSFER V2

### Expected Behavior

```text
current owner transfers entity to requester
```

### Example

```json
{
  "type": "OWNERSHIP_TRANSFER",
  "sender_id": "peer_1",
  "target_peer_id": "peer_2",
  "payload": {
    "entity_id": "army_1",
    "new_owner_id": "peer_2",
    "state": {}
  }
}
```

### Requirements

- [ ] transfer includes `entity_id`.
- [ ] transfer includes `new_owner_id`.
- [ ] transfer includes latest entity state.
- [ ] receiver updates local ownership table.
- [ ] previous owner stops updating entity.
- [ ] other peers are informed if required.

### Potential Bugs

- [ ] two peers update same entity after transfer.
- [ ] transfer does not include latest state.
- [ ] receiver accepts transfer for wrong entity.
- [ ] transfer is not broadcast to observers.
- [ ] stale transfer overrides newer ownership.

---

## 12. OWNERSHIP_DENIED V2

### Expected Behavior

```text
owner refuses ownership transfer
```

### Requirements

- [ ] denial includes `entity_id`.
- [ ] denial includes reason.
- [ ] requester keeps entity as remote-controlled.
- [ ] requester does not modify denied entity.

### Potential Bugs

- [ ] requester ignores denial.
- [ ] requester already modified entity before denial.
- [ ] denial has no entity_id.
- [ ] denial arrives after a transfer and incorrectly cancels it.

---

## 13. OWNERSHIP_RETURN V2

### Expected Behavior

```text
temporary owner returns entity to original owner or neutral owner
```

### Requirements

- [ ] return includes `entity_id`.
- [ ] return includes latest entity state.
- [ ] original owner accepts ownership back.
- [ ] ownership table is updated.
- [ ] other peers are informed if needed.

### Potential Bugs

- [ ] entity returns with stale state.
- [ ] original owner not found.
- [ ] both temporary and original owner keep updating entity.
- [ ] ownership return not propagated.

---

## 14. Ownership State Table V2

### Required Local Table

```text
entity_id    owner_peer_id    version    last_seq
army_1       peer_1           3          120
army_2       peer_2           1          55
```

### Requirements

- [ ] each entity has owner.
- [ ] ownership has version or timestamp.
- [ ] stale ownership messages are ignored.
- [ ] transfer increments ownership version.
- [ ] state update checks owner before applying.

### Potential Bugs

- [ ] no versioning.
- [ ] stale ownership transfer accepted.
- [ ] entity owner differs across peers.
- [ ] ownership state not included in sync.

---

## 15. Authority Check V2

### Rule

```text
A peer may send authoritative STATE_UPDATE only for entities it owns.
```

### Requirements

- [ ] outgoing state only contains owned entities or marks authority clearly.
- [ ] incoming state is checked against known owner.
- [ ] invalid state update from non-owner is ignored or treated as non-authoritative.
- [ ] conflict is logged.

### Test

```text
peer_2 sends STATE_UPDATE for army_1 owned by peer_1
Expected:
peer_3 rejects or ignores that part of the state
```

### Potential Bugs

- [ ] all peers overwrite all entities.
- [ ] non-owner update accepted.
- [ ] no distinction between authoritative and observed state.
- [ ] state_update bypasses ownership logic.

---

## 16. Conflict Handling V2

### Conflict Cases

- two ownership transfers for same entity
- delayed STATE_UPDATE from old owner
- requester modifies before ownership granted
- peer disconnects while owning entity
- simultaneous requests for same entity

### Requirements

- [ ] conflicts are detected.
- [ ] deterministic resolution exists.
- [ ] stale messages are ignored using version/seq.
- [ ] disconnect ownership policy exists.

### Recommended Simple Policy

```text
1. Owner with highest ownership_version wins.
2. For same version, highest seq wins.
3. If owner disconnects, entity becomes neutral or reassigned.
```

### Potential Bugs

- [ ] split-brain ownership.
- [ ] old owner continues sending updates.
- [ ] peer crash leaves entity permanently locked.
- [ ] simultaneous transfer creates inconsistent state.

---

## 17. Version 2 Tests

### Test A — Ownership Request Accepted

```text
peer_1 owns army_1
peer_2 requests army_1
peer_1 sends OWNERSHIP_TRANSFER
peer_2 becomes owner
peer_1 stops updating army_1
```

Expected:

- [ ] peer_2 owner table says `army_1 -> peer_2`.
- [ ] peer_1 owner table says `army_1 -> peer_2`.
- [ ] peer_3 also learns new owner if broadcast is implemented.

---

### Test B — Ownership Request Denied

```text
peer_2 requests army_1
peer_1 denies
peer_2 does not update army_1
```

Expected:

- [ ] ownership unchanged.
- [ ] requester logs denial.
- [ ] no unauthorized STATE_UPDATE is applied.

---

### Test C — Delayed Old Owner Update

```text
peer_1 owns army_1
peer_1 transfers army_1 to peer_2
delayed STATE_UPDATE from peer_1 arrives after transfer
```

Expected:

- [ ] delayed update is ignored.
- [ ] peer_2 remains owner.
- [ ] entity state is not overwritten.

---

### Test D — Three-Peer Ownership Consistency

```text
peer_1 owns army_1
peer_2 owns army_2
peer_3 observes

peer_2 requests army_1
peer_1 transfers army_1 to peer_2
peer_3 receives ownership update
```

Expected:

- [ ] all peers agree on owner of army_1.
- [ ] only peer_2 sends authoritative updates for army_1.
- [ ] no duplicate owner exists.

---

# Version 2 Final Validation

Mark complete only if all are true:

- [ ] ownership request implemented.
- [ ] ownership transfer implemented.
- [ ] ownership denied implemented.
- [ ] ownership return implemented, if required.
- [ ] each entity has owner.
- [ ] stale ownership messages ignored.
- [ ] non-owner state updates rejected or ignored.
- [ ] ownership table consistent across 3 peers.
- [ ] disconnect ownership policy documented.
- [ ] conflict handling policy documented.

Result:

```text
[ ] Version 2 complete
[ ] Version 2 incomplete
```

---

# Global Known Limitations

These limitations are acceptable if documented:

- UDP can lose packets.
- UDP can reorder packets.
- UDP can duplicate packets.
- UDP packets above MTU may fragment.
- no NAT traversal.
- no encryption.
- no authentication.
- no Byzantine fault tolerance.
- no guaranteed global consistency.

---

# Final Project Audit Summary

## Version 1

```text
[ ] Complete
[ ] Incomplete
```

Main missing points:

```text
-
-
-
```

Main bugs found:

```text
-
-
-
```

---

## Version 2

```text
[ ] Complete
[ ] Incomplete
```

Main missing points:

```text
-
-
-
```

Main bugs found:

```text
-
-
-
```

---

# Recommended Final Decision

Use this section before submission:

```text
Version 1 is considered complete if:
- Python ↔ C IPC works
- C ↔ C UDP works
- multi-peer routing works
- STATE_UPDATE synchronization works
- sequence filtering works

Version 2 is considered complete if:
- ownership exists
- authority is enforced
- stale ownership/state messages are ignored
- 3 peers remain consistent after transfer
```
