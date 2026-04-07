from dataclasses import dataclass
from typing import Tuple, Union


class Action:

    def __init__(self, unit, kind, target):

        self.unit: object   =unit              # unité qui agit
        self.kind: str    =kind                # "attack" | "move"
        self.target: Union[object, Tuple[float, float]]= target

    def __repr__(self):
        return f"({self.unit},'{self.kind}',{self.target})"
