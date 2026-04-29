# Project Security Documentation

This document summarizes the security enhancements implemented to protect network communications within the project.

## 1. Implemented Features

### Identity Authentication via SSL/Asymmetric Keys
- Each client generates an **RSA-2048** key pair upon initialization.
- **Handshake Protocol**: Clients exchange public keys using `SECURE_HELLO` messages.
- **Identity Verification**: All subsequent game messages must be signed by the private key corresponding to the registered public key for that peer ID.

### Digital Signatures
- **Algorithm**: RSA-PSS (Probabilistic Signature Scheme) with SHA-256.
- **Purpose**: Ensures **authenticity** (the message comes from the claimed sender) and **integrity** (the message was not modified in transit).
- Every network payload is signed before encryption.

### Asymmetric Encryption
- **Algorithm**: RSA-OAEP with SHA-256.
- **Usage**: Used during the handshake to securely exchange a **Symmetric Session Key** (AES-256). This fulfills the requirement for asymmetric encryption while maintaining performance for game data.

### Symmetric Encryption (Payload Security)
- **Algorithm**: AES-256-GCM (Galois/Counter Mode).
- **Usage**: Encrypts the actual game payloads. GCM provides "Authenticated Encryption," ensuring both confidentiality and additional integrity checks.

### Replay Attack Prevention (TTL & Timestamps)
- **TTL (Time-To-Live)**: Each message includes a floating-point timestamp. Receivers reject any message older than a configurable limit (default: 5.0 seconds).
- **Strict Ordering**: The receiver tracks the `last_timestamp` for each peer. Any message with a timestamp less than or equal to the last seen is rejected as a replay attempt.

---

## 2. Vulnerability Analysis & Proofs of Concept (PoC)

Despite these enhancements, some vulnerabilities remain inherent to the decentralized/UDP nature of the project.

### V1: Man-in-the-Middle (MitM) during Handshake
- **Description**: Since there is no Central Authority (CA) or pre-shared certificate, the system uses **TOFU (Trust On First Use)**. An attacker sitting between two players could intercept the first `SECURE_HELLO` and swap the public keys for their own.
- **PoC**: An attacker script listening on the UDP port could intercept `SECURE_HELLO`, drop it, and send a fake one with its own public key.
- **Mitigation**: Implement a web-based PKI or pre-shared master keys.

### V2: Resource Exhaustion (DDoS via Handshake)
- **Description**: RSA decryption and signature verification are CPU-intensive operations. An attacker can flood a client with fake `SECURE_HELLO` or invalid signed messages to saturate their CPU.
- **PoC**: Use a script to send thousands of randomized JSON messages to the UDP port.
- **Mitigation**: Implement rate limiting and IP-based blacklisting.

### V3: UDP Fragmentation (MTU Limits)
- **Description**: Adding encryption, signatures, and metadata increases message size. If a message exceeds ~1400 bytes, it may be fragmented by the network. UDP does not guarantee reassembly of fragments, leading to packet loss.
- **PoC**: Creating an army with hundreds of units will result in a `SYNC_UPDATE` payload that, when encrypted and signed, exceeds 1500 bytes.
- **Mitigation**: Implement a custom fragmentation/reassembly layer or use delta-compression for game state.

### V4: Local Process Tampering
- **Description**: The private keys are stored in memory within the Python process. An attacker with local access to the machine can read the process memory to extract the private keys.
- **PoC**: Use a tool like `Cheat Engine` or a Python debugger to inspect the `SecurityManager` instance.
- **Mitigation**: Use hardware security modules (HSM) or OS-level key storage (Windows Credential Manager / macOS Keychain).

---

## 3. Verification
Run `python test_security_poc.py` to verify the effectiveness of the implemented protections against replay attacks and tampering.
