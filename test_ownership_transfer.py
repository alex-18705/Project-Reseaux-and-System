import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from backend.Class.Army import Army
from backend.Class.Units.Knight import Knight
from backend.Class.Action import Action
from backend.Utils.network_ownership import initialize_ownership, get_ownership_manager, OwnershipStatus

def test_ownership_transfer():
    print("=== Testing Formal Ownership Transfer Protocol ===")
    
    local_id = "Peer_A"
    remote_id = "Peer_B"
    
    # 1. Initialize ownership
    initialize_ownership(local_id)
    manager = get_ownership_manager()
    manager.register_peer(remote_id)
    
    # 2. Setup Unit
    unit = Knight(position=(10, 10))
    manager.assign_ownership(unit.id, remote_id)
    
    print(f"Unit ID: {unit.id}")
    print(f"Initial Owner: {manager.get_owner(unit.id)}")
    
    # 3. Test: Local peer (Peer A) requests ownership
    print(f"\nPeer A ({local_id}) requests ownership of the unit...")
    manager.request_ownership(unit.id, local_id)
    
    pending = manager.get_pending_request(unit.id)
    if pending == local_id:
        print("SUCCESS: Request recorded as pending.")
    else:
        print("FAILURE: Request not recorded properly.")
        return False
        
    # 4. Test: Peer B (not local) attempts to grant but we simulate Peer B's perspective
    # Let's switch the perspective to test grant_ownership
    # Wait, `grant_ownership` only succeeds if the local peer owns it. 
    # To test, we need a unit owned by local peer.
    
    unit_local = Knight(position=(5, 5))
    manager.assign_ownership(unit_local.id, local_id)
    print(f"\nLocal Unit ID: {unit_local.id} (Owner: {manager.get_owner(unit_local.id)})")
    
    print(f"\nPeer B ({remote_id}) requests ownership of local unit...")
    manager.request_ownership(unit_local.id, remote_id)
    
    print("Peer A (local) grants ownership to Peer B...")
    granted = manager.grant_ownership(unit_local.id, remote_id)
    
    if granted and manager.get_owner(unit_local.id) == remote_id:
        print(f"SUCCESS: Ownership successfully transferred to {remote_id}.")
        if manager.get_pending_request(unit_local.id) is None:
            print("SUCCESS: Pending request cleared after grant.")
        else:
            print("FAILURE: Pending request not cleared.")
            return False
    else:
        print("FAILURE: Ownership grant failed or owner not updated.")
        return False
        
    # 5. Test: Local Peer A receives a GRANT message from Peer B for the first unit
    print(f"\nPeer A receives grant confirmation for Unit {unit.id} from Peer B...")
    manager.handle_grant(unit.id, local_id)
    
    if manager.get_owner(unit.id) == local_id:
        print(f"SUCCESS: Ownership of Unit {unit.id} updated to {local_id}.")
        if manager.get_pending_request(unit.id) is None:
            print("SUCCESS: Pending request cleared after handle_grant.")
        else:
            print("FAILURE: Pending request not cleared.")
            return False
    else:
        print("FAILURE: Ownership handle_grant failed.")
        return False
        
    print("\nOwnership Transfer Protocol test PASSED!")
    return True

if __name__ == "__main__":
    if test_ownership_transfer():
        sys.exit(0)
    else:
        sys.exit(1)
