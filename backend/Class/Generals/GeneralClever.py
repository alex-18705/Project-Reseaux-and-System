from backend.Class.Generals.General import General
from backend.Class.Units.Monk import Monk

class GeneralClever(General):
    def __init__(self):
        super().__init__()
        # Petite base de données perso pour connaître les PV max des unités et calculer mes ratios
        self._max_hp_cache = {"Knight": 100, "Pikeman": 55, "Crossbowman": 35}
        # Un booléen pour savoir si je lance l'attaque générale ou si je reste prudente
        self._is_deployed = False
        # Ma distance de sécurité : si l'ennemi approche à moins de 7 cases, on engage !
        self._deployment_threshold = 49 

    def getTargets(self, map, otherArmy):
        try:
            # Je récupère les troupes encore en vie des deux côtés
            enemies = otherArmy.living_units()
            my_units = self.army.living_units()
        except:
            # Sécurité au cas où le code de mes camarades ferait des siennes
            return []

        if not enemies or not my_units:
            return []

        # TACTIQUE : Si l'ennemi n'a presque plus personne, je passe en mode "assaut total" pour finir la partie
        if len(enemies) <= 2:
            self._is_deployed = True

        # Je surveille la distance entre les deux armées
        min_dist = self._min_distance(my_units, enemies)
        if not self._is_deployed and min_dist <= self._deployment_threshold:
            self._is_deployed = True

        targets = []
        for unit in my_units:
            if not hasattr(unit, 'position') or unit.position is None:
                continue

            # --- MA LOGIQUE POUR LE MOINE ---
            if isinstance(unit, Monk):
                # Le moine check d'abord s'il y a des copains blessés à soigner
                allies = [a for a in self.army.living_units() if a.hp < getattr(a, 'max_hp', 100)]
                if allies:
                    # Il choisit le blessé le plus proche pour être efficace
                    target = min(allies, key=lambda a: self.__distance_sq(unit, a))
                    targets.append((unit, target))
                    continue # S'il soigne, il ne fait rien d'autre ce tour-ci
                
                # Si personne n'a besoin de soin, le moine avance quand même avec l'armée pour ne pas rester seul
                if not self._is_deployed: continue

            # --- MA FORMATION DE GUERRE ---
            # Mes archers restent sagement derrière ma mêlée tant que le combat n'est pas serré
            is_ranged = getattr(unit, 'range', 1) > 1
            if not self._is_deployed and is_ranged:
                # Sauf si un ennemi me colle déjà (moins de 4 cases), là je me défends !
                if min_dist > 16: 
                    continue

            # --- MON ALGORITHME DE SCORING ---
            # Je demande à mon cerveau tactique de choisir la meilleure cible possible
            target = self._choose_best_target(unit, enemies)
            if target:
                targets.append((unit, target))

        return targets

    def _choose_best_target(self, unit, enemies):
        best_enemy = None
        max_score = -float("inf")

        for enemy in enemies:
            if not hasattr(enemy, 'position') or enemy.position is None:
                continue
            
            # Je calcule mes dégâts réels en comptant mes bonus et son armure
            bonus = 0
            try:
                bonus = unit.compute_bonus(enemy)
            except:
                pass
            
            dmg = max(1, (getattr(unit, 'attack', 1) + bonus) - getattr(enemy, 'armor', 0))
            dist_sq = self.__distance_sq(unit, enemy)
            
            # MA STRATÉGIE "FOCUS FIRE" : On achève les unités mourantes !
            u_type = enemy.__class__.__name__
            m_hp = self._max_hp_cache.get(u_type, 100)
            hp_ratio = enemy.hp / m_hp if m_hp > 0 else 1
            
            # Si l'ennemi est à moins de 30% de vie, je multiplie sa priorité par 3 pour le sortir du jeu
            focus = 3.0 if hp_ratio < 0.3 else 1.5 if hp_ratio < 0.6 else 1.0
            
            # Mon score magique : les gros dégâts sur les cibles proches et blessées sont prioritaires
            score = (dmg * focus) / (dist_sq + 0.5)

            if score > max_score:
                max_score = score
                best_enemy = enemy
        
        return best_enemy

    def _min_distance(self, units, enemies):
        """Petite fonction pour trouver l'ennemi le plus proche de mon bloc d'armée."""
        best = float("inf")
        for u in units:
            if not hasattr(u, 'position') or u.position is None: continue
            for e in enemies:
                if not hasattr(e, 'position') or e.position is None: continue
                d = self.__distance_sq(u, e)
                if d < best: best = d
        return best

    @staticmethod
    def __distance_sq(u1, u2):
        """Calcul de distance rapide sans racine carrée pour ne pas faire ramer mon PC."""
        p1, p2 = getattr(u1, 'position', None), getattr(u2, 'position', None)
        if p1 is None or p2 is None: return float("inf")
        return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2