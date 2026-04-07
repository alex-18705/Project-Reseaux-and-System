from random import randint
from backend.Class.Units.Unit import Unit


class Crossbowman(Unit):
    def __init__(self, position: tuple[float]):
        # longer range, slower reload, decent attack
        super().__init__(35, attack=6, armor=0,
                         speed=1, range_=5, reload_time=2, ligne_of_sight=7,position=position, classes=["Archer"], bonuses={"Spear": 3, "Building": 0},)

        self.army = None


    def unit_type(self) -> str:
        return "Crossbowman"

    @property
    def attack(self):
        #if randint(1, 100) >= 85: return 0
        return self._attack

"""
    def attack_unit(self, target, game_map=None) -> Tuple[int, Optional[str]]:
        
        # Ranged "shoot" attack with a small chance for the target to dodge.
        # If `game_map` is provided and the attacker stands on a hill (elevation > 0),
        # the shot deals additional damage (1 extra per elevation level). This function
        # returns (applied_damage, message) where message is a short human-readable string
        # that will be added to the battle's compact event log.
        
        if not target.is_alive():
            return 0, None

        # base dodge chance for ranged shots (tunable)
        base_miss = 0.10  # base 10% miss chance
        # scale with target speed, but keep within reasonable bounds
        speed_factor = 0.02 * max(0, (target.speed - 1))  # each extra speed adds 2% dodge
        dodge_chance = min(0.25, base_miss + speed_factor)  # clamp at 25%

        roll = random.random()
        if roll < dodge_chance:
            # Miss / dodge
            self.cooldown = self.reload_time
            msg = f"{self.owner}'s {self.unit_type()} fires at {target.owner}'s {target.unit_type()} but it dodges!"
            logger.debug("%s (roll=%.3f dodge=%.3f)", msg, roll, dodge_chance)
            return 0, msg

        # Hit: compute base damage
        bonus = self.compute_bonus(target)
        raw = max(1, (self.attack + bonus) - target.armor)

        # Hill amplification if game_map provided and attacker stands on an elevated tile
        hill_bonus = 0
        try:
            if game_map is not None and self.position is not None:
                ux, uy = self.position
                if 0 <= ux < game_map.width and 0 <= uy < game_map.height:
                    tile = game_map.grid[ux][uy]
                    if getattr(tile, "elevation", 0) and int(tile.elevation) > 0:
                        hill_bonus = int(tile.elevation)  # +1 damage per elevation level
        except Exception:
            hill_bonus = 0

        total_raw = raw + hill_bonus
        applied = target.take_damage(total_raw)
        self.cooldown = self.reload_time

        if hill_bonus > 0:
            msg = (f"{self.owner}'s {self.unit_type()} (on hill+{hill_bonus}) shoots "
                   f"{target.owner}'s {target.unit_type()} for {applied} dmg (HP={target.hp})")
        else:
            msg = f"{self.owner}'s {self.unit_type()} shoots {target.owner}'s {target.unit_type()} for {applied} dmg (HP={target.hp})"

        # logger. debug("%s", msg)
        return applied, msg
        
"""