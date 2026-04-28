import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from backend.Class.Army import Army
from backend.Class.Units.Knight import Knight
from backend.Class.Action import Action
from backend.Utils.network_ownership import initialize_ownership, get_ownership_manager, OwnershipStatus

def test_ownership_enforcement():
    print("=== Testing Network Ownership Enforcement ===")
    
    local_id = "Peer_A"
    remote_id = "Peer_B"
    
    # 1. Initialize ownership
    initialize_ownership(local_id)
    manager = get_ownership_manager()
    manager.register_peer(remote_id)
    
    # 2. Setup Armies and Units
    army_a = Army()
    army_b = Army()
    
    # Mock a game mode to store the current sender
    class MockGameMode:
        def __init__(self):
            self.current_sender_id = None
            self.verbose = True
    
    mock_mode = MockGameMode()
    army_a.gameMode = mock_mode
    army_b.gameMode = mock_mode
    
    unit_b = Knight(position=(10, 10)) # Belongs to Peer B
    army_b.add_unit(unit_b)
    manager.assign_ownership(unit_b.id, remote_id)
    
    target = Knight(position=(11, 10)) # Target for testing attack
    army_a.add_unit(target)
    initial_hp = target.hp
    
    print(f"Unit B ID: {unit_b.id} (Owner: {remote_id})")
    print(f"Target HP: {initial_hp}")
    
    # 3. TEST: Unauthorized Action (Peer A tries to use Peer B's unit)
    print("\nAttempting unauthorized action (Peer A uses Unit B)...")
    mock_mode.current_sender_id = local_id
    
    # Peer A tries to make Unit B attack target
    action = Action(unit_b, "attack", target)
    army_b.execOrder([action], army_a)
    
    if target.hp == initial_hp:
        print("SUCCESS: Action was blocked by ownership manager.")
    else:
        print(f"FAILURE: Action was NOT blocked! Target HP: {target.hp}")
        return False

    # 4. TEST: Authorized Action (Peer B uses its own unit)
    print("\nAttempting authorized action (Peer B uses Unit B)...")
    mock_mode.current_sender_id = remote_id
    unit_b.cooldown = 0 # Ensure unit can attack
    
    army_b.execOrder([action], army_a)
    
    if target.hp < initial_hp:
        print(f"SUCCESS: Action was authorized. Target HP is now {target.hp}")
    else:
        print("FAILURE: Authorized action was blocked or failed!")
        return False
        
    print("\nOwnership test PASSED!")
    return True

if __name__ == "__main__":
    if test_ownership_enforcement():
        sys.exit(0)
    else:
        sys.exit(1)
