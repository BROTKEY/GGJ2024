import arcade
import pymunk

import numpy as np

from typing import Optional

from ggj2024.HandReceiver import HandReceiver
from ggj2024.config import *
from ggj2024.utils import normalize_vector, rotate90_cw, rotate90_ccw
from ggj2024.sprites import PlayerSprite, PhysicsSprite, ControllablePlatformSprite


class GameWindow(arcade.Window):
    """ Main Window """

    def __init__(self, width, height, title):
        """ Create the variables """

        # Init the parent class
        super().__init__(width, height, title)

        # Physics engine
        self.physics_engine: Optional[arcade.PymunkPhysicsEngine] = None

        # Player sprite
        self.player_sprite: Optional[PlayerSprite] = None

        # Sprite lists we need
        self.player_list: Optional[arcade.SpriteList] = None
        self.wall_list: Optional[arcade.SpriteList] = None
        self.item_list: Optional[arcade.SpriteList] = None
        self.moving_sprites_list: Optional[arcade.SpriteList] = None
        self.platform_list: Optional[arcade.SpriteList] = None

        # Track the current state of what key is pressed
        self.a_pressed: bool = False
        self.d_pressed: bool = False
        self.w_pressed: bool = False
        self.s_pressed: bool = False

        self.space_pressed: bool = False
        self.enter_pressed: bool = False

        self.left_pressed: bool = False
        self.right_pressed: bool = False
        self.up_pressed: bool = False
        self.down_pressed: bool = False

        self.main_gravity = np.array([0, -GRAVITY], dtype='float')
        self.hands = HandReceiver()

        # Set background color
        arcade.set_background_color(arcade.color.AMAZON)


    @property
    def main_gravity(self):
        return self._main_gravity

    @main_gravity.setter
    def main_gravity(self, grav):
        if isinstance(grav, np.ndarray):
            self._main_gravity = grav
        else:
            self._main_gravity = np.array(grav, dtype='float')
        # Don't try to get the length of a zero vector
        if np.any(self._main_gravity):
            self._main_gravity_direction = normalize_vector(self._main_gravity)
        else:
            # Don't allow zero gravity. Set it to what it was before instead, just very small
            print('DEBUG: It was attempted to set gravity to 0, setting it to a very low value instead')
            self._main_gravity = self._main_gravity_direction * 1e-9
            # No need to set direction vector as it didn't change
            # self._main_gravity_direction = np.zeros((2, ))
        if self.physics_engine:
            self.physics_engine.space.gravity = tuple(self._main_gravity)

    @property
    def main_gravity_dir(self):
        """The direction (= normalized vector) of the main gravity"""
        return self._main_gravity_direction

    def setup(self):
        """ Set up everything with the game """

        # Create the sprite lists
        self.player_list = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList()
        self.platform_list = arcade.SpriteList()

        # Map name
        map_name = "resources/tiled_maps/gravity_test.json"
        # map_name = "resources/tiled_maps/test_map_1.json"

        # Load in TileMap
        tile_map = arcade.load_tilemap(map_name, SPRITE_SCALING_TILES)

        # Pull the sprite layers out of the tile map
        self.wall_list = tile_map.sprite_lists["Platforms"]
        self.item_list = tile_map.sprite_lists["Dynamic Items"]

        # player-controlled platforms
        size = 64
        mass = 1.0
        for i in range(2):
            x = 10 + size * i
            y = 10
            moment = pymunk.moment_for_box(mass, (size, 2*size))
            body = pymunk.Body(mass, moment)
            body.position = pymunk.Vec2d(x, y)
            shape = pymunk.Poly.create_box(body, (size, 2*size))
            shape.elasticity = 0.2
            shape.friction = 0.9
            sprite = ControllablePlatformSprite(shape, ":resources:images/tiles/boxCrate_double.png", width=2*size, height=size)
            self.platform_list.append(sprite)

        # Create player sprite
        self.player_sprite = PlayerSprite(hit_box_algorithm="Detailed")

        # Set player location

        grid_x = 1
        grid_y = 1
        # self.player_sprite.center_x = SPRITE_SIZE * grid_x + SPRITE_SIZE / 2
        # self.player_sprite.center_y = SPRITE_SIZE * grid_y + SPRITE_SIZE / 2
        # Start at center of map
        self.player_sprite.center_x = (tile_map.width * SPRITE_SIZE) / 2
        self.player_sprite.center_y = (tile_map.height * SPRITE_SIZE) / 2
        # Add to player sprite list
        self.player_list.append(self.player_sprite)

        # Used for dragging shapes around with the mouse
        self.platform_left = self.platform_list[0]
        self.platform_right = self.platform_list[1]
        self.last_mouse_position_left = 0, 0
        self.last_mouse_position_right = 0, 0

        # --- Pymunk Physics Engine Setup ---

        # The default damping for every object controls the percent of velocity
        # the object will keep each second. A value of 1.0 is no speed loss,
        # 0.9 is 10% per second, 0.1 is 90% per second.
        # For top-down games, this is basically the friction for moving objects.
        # For platformers with gravity, this should probably be set to 1.0.
        # Default value is 1.0 if not specified.
        damping = DEFAULT_DAMPING

        # Set the gravity. (0, 0) is good for outer space and top-down.
        # gravity = (0, -GRAVITY)

        # Create the physics engine
        self.physics_engine = arcade.PymunkPhysicsEngine(damping=damping,
                                                         gravity=tuple(self.main_gravity))

        # Add the player.
        # For the player, we set the damping to a lower value, which increases
        # the damping rate. This prevents the character from traveling too far
        # after the player lets off the movement keys.
        # Setting the moment to PymunkPhysicsEngine.MOMENT_INF prevents it from
        # rotating.
        # Friction normally goes between 0 (no friction) and 1.0 (high friction)
        # Friction is between two objects in contact. It is important to remember
        # in top-down games that friction moving along the 'floor' is controlled
        # by damping.
        self.physics_engine.add_sprite(self.player_sprite,
                                       friction=PLAYER_FRICTION,
                                       mass=PLAYER_MASS,
                                       moment=arcade.PymunkPhysicsEngine.MOMENT_INF,
                                       collision_type="player",
                                       max_horizontal_velocity=PLAYER_MAX_HORIZONTAL_SPEED,
                                       max_vertical_velocity=PLAYER_MAX_VERTICAL_SPEED)

        # Create the walls.
        # By setting the body type to PymunkPhysicsEngine.STATIC the walls can't
        # move.
        # Movable objects that respond to forces are PymunkPhysicsEngine.DYNAMIC
        # PymunkPhysicsEngine.KINEMATIC objects will move, but are assumed to be
        # repositioned by code and don't respond to physics forces.
        # Dynamic is default.
        self.physics_engine.add_sprite_list(self.wall_list,
                                            friction=WALL_FRICTION,
                                            collision_type="wall",
                                            body_type=arcade.PymunkPhysicsEngine.STATIC)

        # Create the items
        self.physics_engine.add_sprite_list(self.item_list,
                                            friction=DYNAMIC_ITEM_FRICTION,
                                            collision_type="item")

        # add platforms moved by second player
        self.physics_engine.add_sprite_list(
            self.platform_list,
            friction=DYNAMIC_ITEM_FRICTION,
            collision_type="item",
            body_type=arcade.PymunkPhysicsEngine.KINEMATIC
        )

        # Collisions
        def handle_player_wall_collision(player_sprite: PlayerSprite, wall_sprite: arcade.Sprite, arbiter: pymunk.Arbiter, space, data):
            surfvel: pymunk.Vec2d = arbiter.surface_velocity
            impulse: pymunk.Vec2d = arbiter.total_impulse
            if impulse.length > 500:
                print('wall collision, impulse =', impulse.length)
            if impulse.length > PLAYER_DEATH_IMPULSE:
                print(f'died from wall (impulse={impulse.length})')
        def handle_player_item_collision(player_sprite: PlayerSprite, item_sprite: arcade.Sprite, arbiter: pymunk.Arbiter, space, data):
            surfvel: pymunk.Vec2d = arbiter.surface_velocity
            impulse: pymunk.Vec2d = arbiter.total_impulse
            item_sprite.
            if impulse.length > 500:
                print('item collision, impulse =', impulse.length)
            if impulse.length > PLAYER_DEATH_IMPULSE:
                print(f'died from item (impulse={impulse.length})')

        self.physics_engine.add_collision_handler('player', 'wall', post_handler=handle_player_wall_collision)
        self.physics_engine.add_collision_handler('player', 'item', post_handler=handle_player_item_collision)
        # TODO: collision player-kinematics
        

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed. """
        match key:
            case arcade.key.A:
                self.a_pressed = True
            case arcade.key.D:
                self.d_pressed = True
            case arcade.key.W:
                self.w_pressed = True
            case arcade.key.S:
                self.s_pressed = True
            # Walking directions
            case arcade.key.A:
                self.a_pressed = True
            case arcade.key.D:
                self.d_pressed = True
            case arcade.key.W:
                self.w_pressed = True
            case arcade.key.S:
                self.s_pressed = True
            # Jump
            case arcade.key.SPACE:
                self.space_pressed = True
                # find out if player is standing on ground
                if self.physics_engine.is_on_ground(self.player_sprite):
                    if FORCES_RELATIVE_TO_PLAYER:
                        impulse = (0, PLAYER_JUMP_IMPULSE)
                    else:
                        # impulse = -self.main_gravity / np.linalg.norm(self.main_gravity)  * PLAYER_JUMP_IMPULSE
                        impulse = -self.main_gravity_dir * PLAYER_JUMP_IMPULSE
                        impulse = tuple(impulse)
                    self.physics_engine.apply_impulse(self.player_sprite, impulse)
            # Gravity modifier
            case arcade.key.ENTER:
                self.enter_pressed = True
                self.main_gravity = -self.main_gravity

        # TODO: combinations of direction buttons could be done better, this is just for testing
        def update_gravity():
            # This one will set gravity to 0 if two opposite keys are pressed, is this good...?
            new_grav = np.array([0, 0], dtype='float')
            if self.left_pressed and not self.right_pressed:
                new_grav[0] = -GRAVITY
            elif self.right_pressed and not self.left_pressed:
                new_grav[0] = GRAVITY
            if self.up_pressed and not self.down_pressed:
                new_grav[1] = GRAVITY
            elif self.down_pressed and not self.up_pressed:
                new_grav[1] = -GRAVITY
            self.main_gravity = new_grav

        if key == arcade.key.LEFT:
            self.left_pressed = True
            update_gravity()
            # self.main_gravity = np.array([GRAVITY, 0], dtype='float')
        elif key == arcade.key.RIGHT:
            self.right_pressed = True
            update_gravity()
            # self.main_gravity = np.array([-GRAVITY, 0], dtype='float')
        elif key == arcade.key.UP:
            self.up_pressed = True
            update_gravity()
            # self.main_gravity = np.array([0, -GRAVITY], dtype='float')
        elif key == arcade.key.DOWN:
            self.down_pressed = True
            update_gravity()
            # self.main_gravity = np.array([0, GRAVITY], dtype='float')

    def on_key_release(self, key, modifiers):
        """Called when the user releases a key. """
        match key:
            case arcade.key.A:
                self.a_pressed = False
            case arcade.key.D:
                self.d_pressed = False
            case arcade.key.W:
                self.w_pressed = False
            case arcade.key.S:
                self.s_pressed = False
            case arcade.key.SPACE:
                self.space_pressed = False
            case arcade.key.ENTER:
                self.enter_pressed = False
            case arcade.key.LEFT:
                self.left_pressed = False
            case arcade.key.RIGHT:
                self.right_pressed = False
            case arcade.key.UP:
                self.up_pressed = False
            case arcade.key.DOWN:
                self.down_pressed = False

    def on_mouse_press(self, x, y, button, modifiers):
        """ Called whenever the mouse button is clicked. """
        # match button:
        #     case arcade.MOUSE_BUTTON_LEFT:
        #         self.last_mouse_position_left = x, y
        #         self.platform_left = self.platform_list[0]
        #     case arcade.MOUSE_BUTTON_RIGHT:
        #         self.last_mouse_position_right = x, y
        #         self.platform_right = self.platform_list[1]
        pass

    def on_mouse_release(self, x, y, button, modifiers):
        # match button:
        #     case arcade.MOUSE_BUTTON_LEFT:
        #         self.platform_left = None
        #     case arcade.MOUSE_BUTTON_RIGHT:
        #         self.platform_right = None
        pass

    def on_mouse_motion(self, x, y, dx, dy):
        if self.platform_left is not None:
            self.last_mouse_position_left = (x, y)
        if self.platform_right is not None:
            self.last_mouse_position_right = (x, y)

    def on_update(self, delta_time):
        """ Movement and game logic """
        lx = self.hands.left_hand.x
        ly = self.hands.left_hand.y
        rx = self.hands.right_hand.x
        ry = self.hands.right_hand.y
        print(f"L = ({lx:.1f}, {ly:.1f}) R = ({rx:.1f}, {ry:.1f})")

        # Rotate player to gravity
        self.physics_engine.get_physics_object(self.player_sprite).shape.body.angle = np.pi - np.arctan2(*self.main_gravity_dir)

        is_on_ground = self.physics_engine.is_on_ground(self.player_sprite)
        # Update player forces based on keys pressed
        movement_force = PLAYER_MOVE_FORCE_ON_GROUND if is_on_ground else PLAYER_MOVE_FORCE_IN_AIR
        if self.a_pressed and not self.d_pressed:
            # Create a force to the left, perpendicular to the gravity.
            # Gravity pulls down so this actually needs to be the gravity rotated *clockwise*
            if FORCES_RELATIVE_TO_PLAYER:
                self.physics_engine.apply_force(self.player_sprite, (-movement_force, 0))
            else:
                force_dir = rotate90_cw(self.main_gravity_dir)
                self.apply_force_to_player(force_dir, PLAYER_MOVE_FORCE_ON_GROUND if is_on_ground else PLAYER_MOVE_FORCE_IN_AIR)
            # Set friction to zero for the player while moving
            # TODO: is this really a good idea?
            self.physics_engine.set_friction(self.player_sprite, 0)
        elif self.d_pressed and not self.a_pressed:
            # Create a force to the right, perpendicular to the gravity.
            # Gravity pulls down so this actually needs to be the gravity rotated *counterclockwise*
            if FORCES_RELATIVE_TO_PLAYER:
                self.physics_engine.apply_force(self.player_sprite, (movement_force, 0))
            else:
                force_dir = rotate90_ccw(self.main_gravity_dir)
                self.apply_force_to_player(force_dir, PLAYER_MOVE_FORCE_ON_GROUND if is_on_ground else PLAYER_MOVE_FORCE_IN_AIR)
            # Set friction to zero for the player while moving
            # TODO: is this really a good idea?
            self.physics_engine.set_friction(self.player_sprite, 0)
        elif self.w_pressed and not self.s_pressed:
            # Create a force to the top, in the opposite direction of the gravity.
            # force_dir = rotate90_ccw(self.main_gravity_dir)
            pass
        elif self.s_pressed and not self.w_pressed:
            pass

        else:
            # Player's feet are not moving. Therefore up the friction so we stop.
            self.physics_engine.set_friction(self.player_sprite, 1.0)

        # update platform positions based on player input
        if self.platform_left:
            pos = (500 + lx, ly)
            self.physics_engine.set_position(self.platform_left, pos)
            #self.physics_engine.set_position(self.platform_left, self.last_mouse_position_left)

        if self.platform_right:
            pos = (500 + rx, ry)
            self.physics_engine.set_position(self.platform_right, pos)
            #self.physics_engine.set_position(self.platform_right, self.last_mouse_position_right)

        # Move items in the physics engine
        self.physics_engine.step()

    def on_draw(self):
        """ Draw everything """
        self.clear()
        self.wall_list.draw()
        self.platform_list.draw()
        self.item_list.draw()
        self.player_list.draw()