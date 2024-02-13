import logging
from typing import Callable, Iterable, Optional, Any, Union, Tuple, Dict, List
import math
import numpy as np

from pyglet.math import Vec2
import pymunk
import arcade
from arcade import PymunkPhysicsObject, Sprite


LOG = logging.getLogger(__name__)


class PhysicsEngine(arcade.PymunkPhysicsEngine):
    """
    GGJ2024 Physics Engine: extension of arcade.PymunkPhysicsEngine with some extra features and optimizations.

    :param gravity: The direction where gravity is pointing
    :param damping: The amount of speed which is kept to the next tick. a value of 1.0 means no speed loss,
                    while 0.9 has 10% loss of speed etc.
    :param maximum_incline_on_ground: The maximum incline the ground can have, before is_on_ground() becomes False
        default = 0.708 or a little bit over 45° angle
    """

    # pymunk is built upon Chipmunk which only supports upto 32 collision categories
    MAX_COLLISION_CATEGORY = 1 << 32

    def __init__(self, gravity=(0, 0), damping: float = 1.0, maximum_incline_on_ground: float = 0.708):
        super().__init__(gravity, damping, maximum_incline_on_ground)
        self.collision_types: dict[str, int] = {}
        self.next_collision_category: int = 1
    

    def add_sprite(self,
                   sprite: Sprite,
                   mass: float = 1,
                   friction: float = 0.2,
                   elasticity: Optional[float] = None,
                   moment_of_inertia: Optional[float] = None,  # correct spelling
                   body_type: int = arcade.PymunkPhysicsEngine.DYNAMIC,
                   damping: Optional[float] = None,
                   gravity: Union[pymunk.Vec2d, Tuple[float, float], Vec2] = None,
                   max_velocity: int = None,
                   max_horizontal_velocity: int = None,
                   max_vertical_velocity: int = None,
                   radius: float = 0,
                   collision_type: Optional[str] = "default",
                   disable_collisions_for: Optional[list[str] | str] = None,
                   # the next two arguments are for backwards compatibility with prior versions
                   moment_of_intertia: Optional[float] = None,  # typo keyword, used by 2.6.2 and 2.6.3
                   moment: Optional[float] = None,  # used prior to 2.6.2
                   ):
        """ Add a sprite to the physics engine.
            Rewritten to use dicts instead of lists for collision type management

            :param sprite: The sprite to add
            :param mass: The mass of the object. Defaults to 1
            :param friction: The friction the object has. Defaults to 0.2
            :param elasticity: How bouncy this object is. 0 is no bounce. Values of 1.0 and higher may behave badly.
            :param moment_of_inertia: The moment of inertia, or force needed to change angular momentum. \
            Providing infinite makes this object stuck in its rotation.
            :param body_type: The type of the body. Defaults to Dynamic, meaning, the body can move, rotate etc. \
            Providing STATIC makes it fixed to the world.
            :param damping: See class docs
            :param gravity: See class docs
            :param max_velocity: The maximum velocity of the object.
            :param max_horizontal_velocity: maximum velocity on the x axis
            :param max_vertical_velocity: maximum velocity on the y axis
            :param radius:
            :param collision_type: name of the collision category to use for this object
            :param disabler_collisions_for: diable collisions with objects of the given category / categories
            :param moment_of_intertia: Deprecated alias of moment_of_inertia compatible with a typo introduced in 2.6.2
            :param moment: Deprecated alias of moment_of_inertia compatible with versions <= 2.6.1
        """

        if damping is not None:
            sprite.pymunk.damping = damping

        if gravity is not None:
            sprite.pymunk.gravity = gravity

        if max_velocity is not None:
            sprite.pymunk.max_velocity = max_velocity

        if max_vertical_velocity is not None:
            sprite.pymunk.max_vertical_velocity = max_vertical_velocity

        if max_horizontal_velocity is not None:
            sprite.pymunk.max_horizontal_velocity = max_horizontal_velocity

        # See if the sprite already has been added
        if sprite in self.sprites:
            LOG.warning("Attempt to add a Sprite that has already been added. Ignoring.")
            return

        # Get a number associated with the string of collision_type
        collision_category = self.get_collision_category(collision_type)

        # Backwards compatibility for a typo introduced in 2.6.2 and for versions under 2.6.1
        # The current version is checked first, then the most common older form, then the typo
        moment_of_inertia = moment_of_inertia or moment or moment_of_intertia

        # Default to a box moment_of_inertia
        if moment_of_inertia is None:
            moment_of_inertia = pymunk.moment_for_box(mass, (sprite.width, sprite.height))

        # Create the physics body
        body = pymunk.Body(mass, moment_of_inertia, body_type=body_type)

        # Set the body's position
        body.position = pymunk.Vec2d(sprite.center_x, sprite.center_y)
        body.angle = math.radians(sprite.angle)

        # Callback used if we need custom gravity, damping, velocity, etc.
        def velocity_callback(my_body, my_gravity, my_damping, dt):
            """ Used for custom damping, gravity, and max_velocity. """

            # Custom damping
            if sprite.pymunk.damping is not None:
                adj_damping = ((sprite.pymunk.damping * 100.0) / 100.0) ** dt
                # print(f"Custom damping {sprite.pymunk.damping} {my_damping} default to {adj_damping}")
                my_damping = adj_damping

            # Custom gravity
            if sprite.pymunk.gravity is not None:
                my_gravity = sprite.pymunk.gravity

            # Go ahead and update velocity
            pymunk.Body.update_velocity(my_body, my_gravity, my_damping, dt)

            # Now see if we are going too fast...

            # Support max velocity
            if sprite.pymunk.max_velocity:
                velocity = my_body.velocity.length
                if velocity > sprite.pymunk.max_velocity:
                    scale = sprite.pymunk.max_velocity / velocity
                    my_body.velocity = my_body.velocity * scale

            # Support max horizontal velocity
            if sprite.pymunk.max_horizontal_velocity:
                velocity = my_body.velocity.x
                if abs(velocity) > sprite.pymunk.max_horizontal_velocity:
                    velocity = sprite.pymunk.max_horizontal_velocity * math.copysign(1, velocity)
                    my_body.velocity = pymunk.Vec2d(velocity, my_body.velocity.y)

            # Support max vertical velocity
            if max_vertical_velocity:
                velocity = my_body.velocity[1]
                if abs(velocity) > max_vertical_velocity:
                    velocity = max_horizontal_velocity * math.copysign(1, velocity)
                    my_body.velocity = pymunk.Vec2d(my_body.velocity.x, velocity)

        # Add callback if we need to do anything custom on this body
        # if damping or gravity or max_velocity or max_horizontal_velocity or max_vertical_velocity:
        if body_type == self.DYNAMIC:
            body.velocity_func = velocity_callback

        # Set the physics shape to the sprite's hitbox
        poly = sprite.get_hit_box()
        scaled_poly = [[x * sprite.scale for x in z] for z in poly]
        shape = pymunk.Poly(body, scaled_poly, radius=radius)  # type: ignore

        # Set collision type, used in collision callbacks
        if collision_type:
            shape.collision_type = collision_category
        

        # How bouncy is the shape?
        if elasticity is not None:
            shape.elasticity = elasticity

        # Set shapes friction
        shape.friction = friction

        # Create physics object and add to list
        physics_object = PymunkPhysicsObject(body, shape)
        self.sprites[sprite] = physics_object
        if body_type != self.STATIC:
            self.non_static_sprite_list.append(sprite)

        # Set collision category
        old_filter: pymunk.ShapeFilter = physics_object.shape.filter or pymunk.ShapeFilter()
        physics_object.shape.filter = pymunk.ShapeFilter(old_filter.group,
                                                         collision_category,
                                                         old_filter.mask)
        
        # Disable given collisions
        if disable_collisions_for:
            self.disable_collisions(physics_object, disable_collisions_for)

        # Add body and shape to pymunk engine
        self.space.add(body, shape)
        # Register physics engine with sprite, so we can remove from physics engine
        # if we tell the sprite to go away.
        sprite.register_physics_engine(self)


    def add_sprite_list(self,
                        sprite_list,
                        mass: float = 1,
                        friction: float = 0.2,
                        elasticity: Optional[float] = None,
                        moment_of_intertia: Optional[float] = None,
                        body_type: int = arcade.PymunkPhysicsEngine.DYNAMIC,
                        damping: Optional[float] = None,
                        collision_type: Optional[str] = None,
                        disable_collisions_for: Optional[list[str] | str] = None
                        ):
        """ Add all sprites in a sprite list to the physics engine. """

        for sprite in sprite_list:
            self.add_sprite(sprite=sprite,
                            mass=mass,
                            friction=friction,
                            elasticity=elasticity,
                            moment_of_inertia=moment_of_intertia,
                            body_type=body_type,
                            damping=damping,
                            collision_type=collision_type,
                            disable_collisions_for=disable_collisions_for
                            )


    def get_collision_category(self, collision_type: str) -> int:
        category = self.collision_types.get(collision_type)
        if category is None:
            category = self.next_collision_category
            LOG.debug(f"Adding new collision type of {collision_type} with category 0x{category:08X}")
            if category > PhysicsEngine.MAX_COLLISION_CATEGORY:
                raise ValueError("Maximum number of collision categories has been reached")
            self.next_collision_category <<= 1
            self.collision_types[collision_type] = category
        return category
    
    
    def get_collision_category_names(self, category: int) -> list[str]:
        return [name for name, i in self.collision_types.items() if i & category]
    

    def enable_collisions(self, object: arcade.PymunkPhysicsObject | arcade.Sprite, collision_types: str | Iterable[str]):
        """Enable or disable collisions for `object` and other objects"""
        if isinstance(object, arcade.Sprite):
            object = self.get_physics_object(object)
        if isinstance(collision_types, str):
            collision_types = [collision_types]
        old_filter = pymunk.ShapeFilter() if object.shape.filter is None else object.shape.filter
        mask: int = old_filter.mask
        for collision_type in collision_types:
            category = self.get_collision_category(collision_type)
            # category = 1 << category
            mask |= category
        object.shape.filter = pymunk.ShapeFilter(old_filter.group,
                                                 old_filter.categories,
                                                 mask)


    def disable_collisions(self, object: arcade.PymunkPhysicsObject | arcade.Sprite, collision_types: str | Iterable[str]):
        """Disable or disable collisions for `object` and other objects"""
        if isinstance(object, arcade.Sprite):
            object = self.get_physics_object(object)
        if isinstance(collision_types, str):
            collision_types = [collision_types]
        old_filter = pymunk.ShapeFilter() if object.shape.filter is None else object.shape.filter
        mask: int = old_filter.mask
        for collision_type in collision_types:
            category = self.get_collision_category(collision_type)
            # category = 1 << category
            mask &= ~category
        object.shape.filter = pymunk.ShapeFilter(old_filter.group,
                                                 old_filter.categories,
                                                 mask)
    
    def add_collision_handler(self,
                              first_type: str,
                              second_type: str,
                              begin_handler: Callable = None,
                              pre_handler: Callable = None,
                              post_handler: Callable = None,
                              separate_handler: Callable = None):
        """ Add code to handle collisions between objects. """
        first_type_id = self.get_collision_category(first_type)
        second_type_id = self.get_collision_category(second_type)

        def _f1(arbiter, space, data):
            sprite_a, sprite_b = self.get_sprites_from_arbiter(arbiter)
            should_process_collision = begin_handler(sprite_a, sprite_b, arbiter, space, data)
            return should_process_collision

        def _f2(arbiter, space, data):
            sprite_a, sprite_b = self.get_sprites_from_arbiter(arbiter)
            if sprite_a is not None and sprite_b is not None:
                post_handler(sprite_a, sprite_b, arbiter, space, data)

        def _f3(arbiter, space, data):
            sprite_a, sprite_b = self.get_sprites_from_arbiter(arbiter)
            return pre_handler(sprite_a, sprite_b, arbiter, space, data)

        def _f4(arbiter, space, data):
            sprite_a, sprite_b = self.get_sprites_from_arbiter(arbiter)
            separate_handler(sprite_a, sprite_b, arbiter, space, data)

        h = self.space.add_collision_handler(first_type_id, second_type_id)
        if begin_handler:
            h.begin = _f1
        if post_handler:
            h.post_solve = _f2
        if pre_handler:
            h.pre_solve = _f3
        if separate_handler:
            h.separate = _f4
    
    def make_shapefilter(self, collision_types: str | list[str], categories: Optional[list[str]|str] = None, group: int = 0, invert_mask: bool = False, inver_categories: bool = False):
        """Make a shape filter for collisions with the given type(s).
        :param collision_types: collision type(s) to include in filter
        :param categories: collision type(s) this filter should belong to (default: all)
        :param group: collision group (see pymunk's doc on ShapeFilters for details)
        :param invert_mask: invert filter (so that collisions happen with every collision type *excep* the given ones)
        """
        if categories is not None:
            if isinstance(categories, str):
                categories = self.get_collision_category(categories)
            else:
                categories = np.bitwise_or.reduce([self.get_collision_category(c) for c in categories])
        else:
            categories = pymunk.ShapeFilter.ALL_CATEGORIES()
        if isinstance(collision_types, str):
            mask = self.get_collision_category(collision_types)
        else:
            mask = np.bitwise_or.reduce([self.get_collision_category(t) for t in collision_types])
        
        if inver_categories:
            categories = ~categories
        if invert_mask:
            mask = ~mask
        
        return pymunk.ShapeFilter(group, categories, mask)
        