from enum import IntEnum
from typing import Dict, Optional

class OwnershipStatus(IntEnum):
    """Status codes for network ownership verification."""
    AUTHORIZED = 0
    DENIED_NOT_OWNER = 1
    DENIED_INVALID_UNIT = 2
    DENIED_MALFORMED_ACTION = 3
    DENIED_UNREGISTERED_PEER = 4

class OwnershipManager:
    """
    Manages and verifies network ownership of game units.
    Ensures that only the peer owning a unit can issue commands (actions) for it.
    """
    def __init__(self, local_peer_id: str):
        self.local_peer_id = local_peer_id
        self._unit_to_peer: Dict[str, str] = {}  # Map: unit_id -> peer_id
        self._registered_peers = {local_peer_id}

    def register_peer(self, peer_id: str):
        """Registers a new network peer."""
        self._registered_peers.add(peer_id)

    def assign_ownership(self, unit_id: str, peer_id: str):
        """Assigns a unit to a specific peer."""
        if peer_id not in self._registered_peers:
            self.register_peer(peer_id)
        self._unit_to_peer[unit_id] = peer_id

    def get_owner(self, unit_id: str) -> Optional[str]:
        """Returns the peer_id owning the given unit_id."""
        return self._unit_to_peer.get(unit_id)

    def is_local_owner(self, unit_id: str) -> bool:
        """Checks if the local peer owns the unit."""
        return self.get_owner(unit_id) == self.local_peer_id

    def validate_action(self, action_data: dict, executor_peer_id: str) -> OwnershipStatus:
        """
        Validates if an action is authorized based on network ownership.
        Expected action_data format: {"unit_id": str, "kind": str, ...}
        """
        if not isinstance(action_data, dict) or "unit_id" not in action_data:
            return OwnershipStatus.DENIED_MALFORMED_ACTION

        unit_id = action_data["unit_id"]
        
        if executor_peer_id not in self._registered_peers:
            return OwnershipStatus.DENIED_UNREGISTERED_PEER

        owner_id = self.get_owner(unit_id)
        if owner_id is None:
            return OwnershipStatus.DENIED_INVALID_UNIT

        if owner_id == executor_peer_id:
            return OwnershipStatus.AUTHORIZED
        
        return OwnershipStatus.DENIED_NOT_OWNER

# Singleton-like access for the current game session
_instance: Optional[OwnershipManager] = None

def initialize_ownership(local_id: str):
    global _instance
    _instance = OwnershipManager(local_id)

def get_ownership_manager() -> OwnershipManager:
    if _instance is None:
        raise RuntimeError("OwnershipManager has not been initialized. Call initialize_ownership first.")
    return _instance
