import time
import json
import base64
from network.security_manager import SecurityManager

def test_security_flow():
    print("--- Testing Security Flow ---")
    alice = SecurityManager(ttl_limit=1.0)
    bob = SecurityManager(ttl_limit=1.0)
    
    # 1. Identity Authentication (Key Exchange)
    alice_pub_pem = alice.get_my_public_key_pem()
    bob_pub_pem = bob.get_my_public_key_pem()
    
    alice.register_peer("bob", bob_pub_pem)
    bob.register_peer("alice", alice_pub_pem)
    print("[Pass] Public Keys Exchanged")
    
    # 2. Session Key Exchange (Asymmetric Encryption)
    encrypted_session_key = alice.create_session_key("bob")
    bob.handle_session_key("alice", encrypted_session_key)
    print("[Pass] Session Key established via RSA OAEP")
    
    # 3. Valid Message (Signing & Encryption)
    payload = {"action": "move", "unit": 1, "pos": [10, 20]}
    secure_msg = alice.sign_and_encrypt("bob", payload)
    
    decrypted, error = bob.decrypt_and_verify("alice", secure_msg)
    if decrypted == payload:
        print("[Pass] Valid message decrypted and verified")
    else:
        print(f"[Fail] Valid message failed: {error}")

    # 4. Replay Attack Detection
    print("\n--- Testing Replay Attack Detection ---")
    decrypted, error = bob.decrypt_and_verify("alice", secure_msg)
    if error == "Replay attack detected (Timestamp older or equal to last seen)":
        print("[Pass] Replay attack detected (Duplicate timestamp)")
    else:
        print(f"[Fail] Replay attack NOT detected: {error}")

    # 5. TTL Expiry Detection
    print("\n--- Testing TTL Expiry ---")
    time.sleep(1.1)
    secure_msg_old = alice.sign_and_encrypt("bob", {"msg": "old"})
    time.sleep(1.1) # Wait for it to expire
    decrypted, error = bob.decrypt_and_verify("alice", secure_msg_old)
    if "expired" in str(error):
        print("[Pass] Expired message detected (TTL)")
    else:
        print(f"[Fail] Expired message NOT detected: {error}")

    # 6. Signature Tampering Detection
    print("\n--- Testing Signature Tampering ---")
    secure_msg_tampered = alice.sign_and_encrypt("bob", {"msg": "secret"})
    # Tamper with the ciphertext (just change one character)
    ciphertext_bytes = list(base64.b64decode(secure_msg_tampered["ciphertext"]))
    ciphertext_bytes[0] ^= 0xFF
    secure_msg_tampered["ciphertext"] = base64.b64encode(bytes(ciphertext_bytes)).decode('utf-8')
    
    decrypted, error = bob.decrypt_and_verify("alice", secure_msg_tampered)
    if "verification failed" in str(error) or "Tag does not match" in str(error):
        print("[Pass] Tampered message detected (Integrity/Signature failure)")
    else:
        print(f"[Fail] Tampered message NOT detected: {error}")

if __name__ == "__main__":
    test_security_flow()
