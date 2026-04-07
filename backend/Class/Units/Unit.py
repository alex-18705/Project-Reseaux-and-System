import uuid
from abc import abstractmethod


class Unit():


    def __init__(self, max_hp: int, attack: int, armor: int,
                 speed: int, range_: int, reload_time: int, ligne_of_sight:int,position: tuple[float]= None, size :float=1, classes=None, bonuses=None):


        self.__id = str(uuid.uuid4())
        self.army = None

        # caractéristique
        self.max_hp = max_hp
        self.hp = max_hp
        self._attack = attack
        self.armor = armor
        self.speed = speed
        self.range = range_
        self.position = position  # (x, y) or None
        self.size = size
        self.classes = classes if classes else []
        self.bonuses = bonuses if bonuses else {}
        self.reload_time = reload_time #le temps qu'il faut entre 2 attaques
        self.cooldown = 0 #le temps necessaire qu'il reste à attendre pour la prochaine attaque
        self.line_of_sight = ligne_of_sight

        self.last_attacker = None
        self.last_attacked =None

    @property
    def attack(self):
        return self._attack


    @property #id est un argument privé cela permet de créer un getter
    def id(self) :
        return self.__id

    def is_alive(self) -> bool:
        return self.hp > 0


"""
    # Dans le init ---------------------------------------
        # per-unit "order" set by the general each tick:  usually a reference to an enemy unit
        self.current_target = None  # Optional[Unit]

        # Threat tracking:  remembers who attacked this unit and from where
        # Format: {"attacker_id": {"unit":  Unit, "last_known_pos": (x, y), "tick": int}}
        self.threat_memory: Dict[str, Dict[str, Any]] = {}
    # -------------------------------------------------------
    
    

    def register_threat(self, attacker: "Unit", attacker_pos: Tuple[int, int], tick: int):
        # Register an attacker as a threat.  Stores the attacker reference and their
        # position at the time of attack.  This allows units to track and pursue
        # enemies that attacked them from range.
        
        if attacker is None or attacker_pos is None:
            return
        self.threat_memory[attacker.id] = {
            "unit": attacker,
            "last_known_pos": tuple(attacker_pos),
            "tick": tick
        }
        logger.debug("%s registered threat from %s at %s (tick %d)",
                     self.unit_type(), attacker.unit_type(), attacker_pos, tick)

    def get_priority_threat(self) -> Optional["Unit"]:
        
        # Returns the most recent living attacker from threat memory.
        # Cleans up dead attackers from memory.

        # Clean up dead attackers
        dead_ids = [aid for aid, info in self.threat_memory.items()
                    if not info["unit"].is_alive()]
        for aid in dead_ids:
            del self.threat_memory[aid]

        if not self.threat_memory:
            return None

        # Return the most recently registered threat (highest tick)
        most_recent = max(self.threat_memory.values(), key=lambda x: x["tick"])
        return most_recent["unit"]

    def get_threat_last_known_pos(self, attacker_id: str) -> Optional[Tuple[int, int]]:
        # Get the last known position of a specific attacker.
        if attacker_id in self.threat_memory:
            return self.threat_memory[attacker_id]["last_known_pos"]
        return None

    def clear_threat(self, attacker_id: str):
        # Remove a specific attacker from threat memory (e.g., after killing them).
        if attacker_id in self.threat_memory:
            del self.threat_memory[attacker_id]

    def take_damage(self, dmg: int):
        # shared damage application (considers armor)
        applied = max(1, dmg - self.armor)
        self.hp -= applied
        if self.hp < 0:
            self.hp = 0
        logger.debug("%s took %d damage (after armor=%d) hp now=%d",
                     getattr(self, "unit_type", lambda: "unit")(), applied, self.armor, self.hp)
        return applied

    def can_attack(self) -> bool:
        return self.cooldown <= 0

    def reset_cooldown(self):
        self.cooldown = self.reload_time

    def compute_bonus(self, target) -> int:
        #Return the attack bonuses against the target based on its classes.
        total = 0
        for cls in target.classes:
            if cls in self.bonuses:
                total += self.bonuses[cls]
        return total

    @abstractmethod
    def attack_unit(self, target, game_map=None) -> Tuple[int, Optional[str]]:
        
        #Default attack - used by melee and by default for subclasses that don't override.
        #Accepts optional game_map so subclasses can inspect tile properties (elevation/buildings).
        #Returns (applied_damage, optional_message)
        
        if not target.is_alive():
            return 0, None
        # compute total damage including bonuses (do not mutate self.attack permanently)
        bonus = self.compute_bonus(target)
        raw = max(1, (self.attack + bonus) - target.armor)
        applied = target.take_damage(raw)
        self.cooldown = self.reload_time
        # no custom message by default
        return applied, None

    @abstractmethod
    def unit_type(self) -> str:
        pass

    def to_dict(self) -> Dict[str, Any]:
        # Serialize threat memory (only store IDs and positions, not unit references)
        threat_data = {}
        for aid, info in self.threat_memory.items():
            threat_data[aid] = {
                "attacker_id": aid,
                "last_known_pos": list(info["last_known_pos"]) if info["last_known_pos"] else None,
                "tick": info["tick"]
            }

        return {
            "id": self.id,
            "owner": self.owner,
            "hp": self.hp,
            "attack": self.attack,
            "armor": self.armor,
            "speed": self.speed,
            "range": self.range,
            "reload_time": self.reload_time,
            "position": list(self.position) if self.position is not None else None,
            "cooldown": self.cooldown,
            "classes": self.classes,
            "bonuses": self.bonuses,
            "unit_type": self.unit_type(),
            "threat_memory": threat_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Unit":
        unit_type = data.get("unit_type")
        owner = data["owner"]
        # instantiate right subclass
        if unit_type == "Knight":
            unit = Knight(owner, id=data.get("id"))
        elif unit_type == "Pikeman":
            unit = Pikeman(owner, id=data.get("id"))
        elif unit_type == "Crossbowman":
            unit = Crossbowman(owner, id=data.get("id"))
        else:
            # Fallback:  basic Unit-like object via generic subclass
            raise ValueError(f"Unknown unit_type: {unit_type}")

        # restore mutable state
        unit.hp = data.get("hp", unit.hp)
        unit.cooldown = data.get("cooldown", 0)
        pos = data.get("position")
        unit.position = tuple(pos) if pos is not None else None
        # Note: threat_memory restoration requires access to other units,
        # which is handled at a higher level (Battle.from_dict)
        return unit
"""
