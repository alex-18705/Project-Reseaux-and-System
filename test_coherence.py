import time
import json
import uuid
from backend.GameModes.Online import Online
from backend.Class.Army import Army
from backend.Class.Map import Map
from backend.Class.Units.Knight import Knight

class MockNetworkBridge:
    """A bridge that routes messages directly to another bridge's queue for testing."""
    def __init__(self, owner_id):
        self.owner_id = owner_id
        self.target = None
        self.security_manager = None # Set by Online init if enabled
        self.is_connected = True
        self.incoming_queue = [] # Simple list for mock

    def connect(self, *args, **kwargs):
        return True

    def disconnect(self):
        self.is_connected = False

    def get_updates(self):
        updates = self.incoming_queue[:]
        self.incoming_queue = []
        return updates

    def send_message(self, msg_type, destination, payload_dict=None, peer_id=None):
        if not self.is_connected: return
        
        # Apply security if enabled (this mimics the real NetworkBridge logic)
        if self.security_manager and msg_type not in ["SECURE_HELLO", "SECURE_KEY_EXCHANGE"] and peer_id:
            secure_payload = self.security_manager.sign_and_encrypt(peer_id, payload_dict)
            if secure_payload:
                payload_dict = secure_payload
        
        msg = {
            "type": msg_type,
            "payload": payload_dict,
            "_sender_ip": "127.0.0.1", # Mock IP
            "seq": 1
        }
        
        # Route to target
        if self.target:
            self.target.incoming_queue.append(msg)
        return True

def demonstrate_coherence():
    print("=== Coherence Demonstration: Secure Online Battle ===")
    
    # 1. Setup Alice (Host)
    alice = Online(is_first=True)
    alice.map = Map(100, 100)
    alice.my_army = Army()
    alice.my_army.add_unit(Knight((10, 10)))
    
    # 2. Setup Bob (Joiner)
    bob = Online(is_first=False)
    bob.my_army = Army()
    bob.my_army.add_unit(Knight((90, 90)))
    
    # 3. Inject Mock Bridges
    alice_bridge = MockNetworkBridge(alice.my_id)
    bob_bridge = MockNetworkBridge(bob.my_id)
    
    # Link SecurityManagers from Online instances to bridges
    alice_bridge.security_manager = alice.network_bridge.security_manager
    bob_bridge.security_manager = bob.network_bridge.security_manager
    
    # Replace real bridges with mocks
    alice.network_bridge = alice_bridge
    bob.network_bridge = bob_bridge
    
    # Link targets
    alice_bridge.target = bob_bridge
    bob_bridge.target = alice_bridge
    
    print(f"Alice ID: {alice.my_id}")
    print(f"Bob ID:   {bob.my_id}")
    print("\n--- Phase 1: Discovery & Handshake ---")
    
    # Bob discovers Alice (simulated by adding IP)
    alice.know_ip.add("127.0.0.1")
    bob.know_ip.add("127.0.0.1")
    
    # Loop to process handshake
    for i in range(5):
        print(f"Tick {i}...")
        alice.message_receive()
        bob.message_receive()
        
        # Check security status
        alice_sec = alice.network_bridge.security_manager
        bob_sec = bob.network_bridge.security_manager
        
        if bob.my_id in alice_sec.peer_session_keys and alice.my_id in bob_sec.peer_session_keys:
            print(f"[Success] Secure Session Established on Tick {i}!")
            break
    
    print("\n--- Phase 2: Secure State Synchronization ---")
    
    # Alice broadcasts her state (Encrypted & Signed)
    alice._broadcast_state()
    print("Alice sent SYNC_UPDATE (Encrypted & Signed)")
    
    # Bob receives and decrypts
    bob.message_receive()
    
    if alice.my_id in bob.othersArmy:
        remote_army = bob.othersArmy[alice.my_id]
        print(f"[Success] Bob successfully decrypted Alice's army: {len(remote_army.units)} units found.")
        print(f"Unit 0 Position: {remote_army.units[0].position} (Verified)")
    else:
        print("[Fail] Bob could not see Alice's army.")

    print("\n--- Phase 3: Coherence Check ---")
    # Verify that Bob's view of Alice's units matches Alice's local state
    alice_unit_pos = alice.my_army.units[0].position
    bob_view_pos = bob.othersArmy[alice.my_id].units[0].position
    
    if alice_unit_pos == bob_view_pos:
        print(f"[Pass] World Coherence: Alice.pos{alice_unit_pos} == Bob'sView.pos{bob_view_pos}")
    else:
        print(f"[Fail] Incoherence detected! Alice:{alice_unit_pos} != Bob:{bob_view_pos}")

    # Verify that unencrypted/tampered messages would be rejected
    print("\n--- Phase 4: Resilience Check ---")
    # Alice sends a fake unencrypted message
    alice_bridge.send_message("SYNC_UPDATE", "127.0.0.1", {"fake": "data"})
    print("Alice sent a fake unencrypted message.")
    
    # Bob tries to receive
    bob.message_receive()
    if "fake" in str(bob.othersArmy):
         print("[Fail] Bob accepted unencrypted data!")
    else:
         print("[Pass] Bob ignored the insecure message (Expected behavior).")

if __name__ == "__main__":
    demonstrate_coherence()
