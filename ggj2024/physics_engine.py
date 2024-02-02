import logging
from typing import Iterable

import pymunk
import arcade


LOG = logging.getLogger(__name__)


# TODO: use dict for collision_types instead of list. Requires rewrite of some base class functions.
class PhysicsEngine(arcade.PymunkPhysicsEngine):
    """
    GGJ2024 Physics Engine: extension of arcade.PymunkPhysicsEngine

    :param gravity: The direction where gravity is pointing
    :param damping: The amount of speed which is kept to the next tick. a value of 1.0 means no speed loss,
                    while 0.9 has 10% loss of speed etc.
    :param maximum_incline_on_ground: The maximum incline the ground can have, before is_on_ground() becomes False
        default = 0.708 or a little bit over 45° angle
    """

    def __init__(self, gravity=(0, 0), damping: float = 1.0, maximum_incline_on_ground: float = 0.708):
        super().__init__(gravity, damping, maximum_incline_on_ground)
    
    def _find_or_add_collision_type(self, collision_type: str) -> int:
        # Yes, try-except is actually the most efficient way to do this in python...
        try:
            return self.collision_types.index(collision_type)
        except ValueError:
            LOG.debug(f"Adding new collision type of {collision_type}.")
            id = len(self.collision_types)
            self.collision_types.append(collision_type)
            return id

    # def set_collisions(self, group1: str, group2: str, enable_collisions: bool):
    #     """Enable or disable collisions between two collision types"""
    #     # fuck this won't work as shapefilters are per-object. Will have to do it another way....
    #     id1 = self._find_or_add_collision_type(group1)
    #     id2 = self._find_or_add_collision_type(group2)
        
    
    def enable_collisions(self, object: arcade.PymunkPhysicsObject, collision_types: str | Iterable[str]):
        """Enable or disable collisions for `object` and other objects"""
        if isinstance(collision_types, str):
            collision_types = [collision_types]
        mask = object.shape.filter.mask
        for collision_type in collision_types:
            category = self._find_or_add_collision_type(collision_type)
            category = 1 << category
            mask |= category
        object.shape.filter.mask = mask

    def disable_collisions(self, object: arcade.PymunkPhysicsObject, collision_types: str | Iterable[str]):
        """Disable or disable collisions for `object` and other objects"""
        if isinstance(collision_types, str):
            collision_types = [collision_types]
        mask = object.shape.filter.mask
        for collision_type in collision_types:
            category = self._find_or_add_collision_type(collision_type)
            category = 1 << category
            mask &= ~category
        object.shape.filter.mask = mask
            