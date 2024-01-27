"""
Example of Pymunk Physics Engine Platformer
"""
import math
from typing import Optional
import arcade
import numpy as np


SCREEN_TITLE = "PyMunk Platformer"

# How big are our image tiles?
SPRITE_IMAGE_SIZE = 128

# Scale sprites up or down
SPRITE_SCALING_PLAYER = 0.5
SPRITE_SCALING_TILES = 0.5

# Scaled sprite size for tiles
SPRITE_SIZE = int(SPRITE_IMAGE_SIZE * SPRITE_SCALING_PLAYER)

# Size of grid to show on screen, in number of tiles
SCREEN_GRID_WIDTH = 25
SCREEN_GRID_HEIGHT = 15

# Size of screen to show, in pixels
SCREEN_WIDTH = SPRITE_SIZE * SCREEN_GRID_WIDTH
SCREEN_HEIGHT = SPRITE_SIZE * SCREEN_GRID_HEIGHT

# --- Physics forces. Higher number, faster accelerating.

# Gravity
GRAVITY = -2000

# Damping - Amount of speed lost per second
DEFAULT_DAMPING = 1.0
PLAYER_DAMPING = 0.4

# Friction between objects
PLAYER_FRICTION = 1.0
WALL_FRICTION = 0.7
DYNAMIC_ITEM_FRICTION = 0.6

# Mass (defaults to 1)
PLAYER_MASS = 2.0

# Keep player from going too fast
PLAYER_MAX_HORIZONTAL_SPEED = 1000
PLAYER_MAX_VERTICAL_SPEED = 1000

# Force applied while on the ground
PLAYER_MOVE_FORCE_ON_GROUND = 8000
# Force applied when moving left/right in the air
PLAYER_MOVE_FORCE_IN_AIR = 5000

# Strength of a jump
PLAYER_JUMP_IMPULSE = 1800

# Close enough to not-moving to have the animation go to idle.
DEAD_ZONE = 0.1

# Constants used to track if the player is facing left or right
RIGHT_FACING = 0
LEFT_FACING = 1

# How many pixels to move before we change the texture in the walking animation
DISTANCE_TO_CHANGE_TEXTURE = 20

# Defines whether forces on the player are considered to be in the Player's coordinate system
# This switch is basically here to keep some of the old code...
FORCES_RELATIVE_TO_PLAYER = True


def normalize_vector(vec: np.ndarray, inplace=False) -> np.ndarray:
    if inplace:
        vec /= np.linalg.norm(vec)
        return vec
    else:
        return vec / np.linalg.norm(vec)

def rotate90_cw(vec: np.ndarray, inplace=False) -> np.ndarray:
    if inplace:
        x = vec[0]
        vec[0] = vec[1]
        vec[1] = -x
        return vec
    else:
        return np.array([
            vec[1],
            -vec[0]
        ])
    
def rotate90_ccw(vec: np.ndarray, inplace=False) -> np.ndarray:
    if inplace:
        x = vec[0]
        vec[0] = -vec[1]
        vec[1] = x
        return vec
    else:
        return np.array([
            -vec[1],
            vec[0]
        ])


class PlayerSprite(arcade.Sprite):
    """ Player Sprite """
    def __init__(self,
                #  ladder_list: arcade.SpriteList,
                 hit_box_algorithm):
        """ Init """
        # Let parent initialize
        super().__init__()

        # Set our scale
        self.scale = SPRITE_SCALING_PLAYER

        # Images from Kenney.nl's Character pack
        # main_path = ":resources:images/animated_characters/female_adventurer/femaleAdventurer"
        main_path = ":resources:images/animated_characters/female_person/femalePerson"
        # main_path = ":resources:images/animated_characters/male_person/malePerson"
        # main_path = ":resources:images/animated_characters/male_adventurer/maleAdventurer"
        # main_path = ":resources:images/animated_characters/zombie/zombie"
        # main_path = ":resources:images/animated_characters/robot/robot"

        # Load textures for idle standing
        self.idle_texture_pair = arcade.load_texture_pair(f"{main_path}_idle.png",
                                                          hit_box_algorithm=hit_box_algorithm)
        self.jump_texture_pair = arcade.load_texture_pair(f"{main_path}_jump.png")
        self.fall_texture_pair = arcade.load_texture_pair(f"{main_path}_fall.png")

        # Load textures for walking
        self.walk_textures = []
        for i in range(8):
            texture = arcade.load_texture_pair(f"{main_path}_walk{i}.png")
            self.walk_textures.append(texture)

        # Set the initial texture
        self.texture = self.idle_texture_pair[0]

        # Hit box will be set based on the first image used.
        self.hit_box = self.texture.hit_box_points

        # Default to face-right
        self.character_face_direction = RIGHT_FACING

        # Index of our current texture
        self.cur_texture = 0

        # How far have we traveled horizontally since changing the texture
        self.x_odometer = 0
        self.y_odometer = 0


    def pymunk_moved(self, physics_engine, dx, dy, d_angle):
        """ Handle being moved by the pymunk engine """
        # Figure out if we need to face left or right
        if dx < -DEAD_ZONE and self.character_face_direction == RIGHT_FACING:
            self.character_face_direction = LEFT_FACING
        elif dx > DEAD_ZONE and self.character_face_direction == LEFT_FACING:
            self.character_face_direction = RIGHT_FACING

        # Are we on the ground?
        is_on_ground = physics_engine.is_on_ground(self)

        # Add to the odometer how far we've moved
        self.x_odometer += dx
        self.y_odometer += dy

        # Jumping animation
        if not is_on_ground:
            if dy > DEAD_ZONE:
                self.texture = self.jump_texture_pair[self.character_face_direction]
                return
            elif dy < -DEAD_ZONE:
                self.texture = self.fall_texture_pair[self.character_face_direction]
                return

        # Idle animation
        if abs(dx) <= DEAD_ZONE:
            self.texture = self.idle_texture_pair[self.character_face_direction]
            return

        # Have we moved far enough to change the texture?
        if abs(self.x_odometer) > DISTANCE_TO_CHANGE_TEXTURE:

            # Reset the odometer
            self.x_odometer = 0

            # Advance the walking animation
            self.cur_texture += 1
            if self.cur_texture > 7:
                self.cur_texture = 0
            self.texture = self.walk_textures[self.cur_texture][self.character_face_direction]


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

        self.main_gravity = np.array([0, GRAVITY], dtype='float')
        # self.main_gravity = np.array([-GRAVITY, -GRAVITY], dtype='float')


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

        # Map name
        # map_name = ":resources:/tiled_maps/pymunk_test_map.json"
        map_name = "resources/tiled_maps/gravity_test.json"

        # Load in TileMap
        tile_map = arcade.load_tilemap(map_name, SPRITE_SCALING_TILES)

        # Pull the sprite layers out of the tile map
        self.wall_list = tile_map.sprite_lists["Platforms"]
        self.item_list = tile_map.sprite_lists.get("Dynamic Items") or arcade.SpriteList()
        self.moving_sprites_list = tile_map.sprite_lists.get('Moving Platforms') or arcade.SpriteList()

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

        # Add kinematic sprites
        self.physics_engine.add_sprite_list(self.moving_sprites_list,
                                            body_type=arcade.PymunkPhysicsEngine.KINEMATIC)

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed. """

        # Walking directions
        if key == arcade.key.A:
            self.a_pressed = True
        elif key == arcade.key.D:
            self.d_pressed = True
        elif key == arcade.key.W:
            self.w_pressed = True
        elif key == arcade.key.S:
            self.s_pressed = True

        # Jump
        elif key == arcade.key.SPACE:
            self.space_pressed = True
            # find out if player is standing on ground
            if self.physics_engine.is_on_ground(self.player_sprite):
                if FORCES_RELATIVE_TO_PLAYER:
                    impulse = (0, PLAYER_JUMP_IMPULSE)
                else:
                    impulse = -self.main_gravity / np.linalg.norm(self.main_gravity)  * PLAYER_JUMP_IMPULSE
                    impulse = tuple(impulse)
                self.physics_engine.apply_impulse(self.player_sprite, impulse)
        
        # Gravity modifier
        elif key == arcade.key.ENTER:
            self.enter_pressed = True
            self.main_gravity = -self.main_gravity
        
        # TODO: combinations of direction buttons could be done better, this is just for testing
        def update_gravity():
            # This one will set gravity to 0 if two opposite keys are pressed, is this good...?
            new_grav = np.array([0, 0], dtype='float')
            if self.left_pressed and not self.right_pressed:
                new_grav[0] = GRAVITY
            elif self.right_pressed and not self.left_pressed:
                new_grav[0] = -GRAVITY
            if self.up_pressed and not self.down_pressed:
                new_grav[1] = -GRAVITY
            elif self.down_pressed and not self.up_pressed:
                new_grav[1] = GRAVITY
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

        if key == arcade.key.A:
            self.a_pressed = False
        elif key == arcade.key.D:
            self.d_pressed = False
        elif key == arcade.key.W:
            self.w_pressed = False
        elif key == arcade.key.S:
            self.s_pressed = False
        elif key == arcade.key.SPACE:
            self.space_pressed = False
        elif key == arcade.key.ENTER:
            self.enter_pressed = False
        elif key == arcade.key.LEFT:
            self.left_pressed = False
        elif key == arcade.key.RIGHT:
            self.right_pressed = False
        elif key == arcade.key.UP:
            self.up_pressed = False
        elif key == arcade.key.DOWN:
            self.down_pressed = False

    def on_mouse_press(self, x, y, button, modifiers):
        """ Called whenever the mouse button is clicked. """
        pass

    def apply_force_to_player(self, direction: np.ndarray, force: float):
        self.physics_engine.apply_force(self.player_sprite, tuple(direction * force))

    def on_update(self, delta_time):
        """ Movement and game logic """

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

        self.physics_engine.get_physics_object(self.player_sprite).shape.body.angle = np.pi - np.arctan2(*self.main_gravity_dir)
        print(np.arctan2(*self.main_gravity_dir))

        # Move items in the physics engine
        self.physics_engine.step()

        # For each moving sprite, see if we've reached a boundary and need to
        # reverse course.
        for moving_sprite in self.moving_sprites_list:
            if moving_sprite.boundary_right and \
                    moving_sprite.change_x > 0 and \
                    moving_sprite.right > moving_sprite.boundary_right:
                moving_sprite.change_x *= -1
            elif moving_sprite.boundary_left and \
                    moving_sprite.change_x < 0 and \
                    moving_sprite.left > moving_sprite.boundary_left:
                moving_sprite.change_x *= -1
            if moving_sprite.boundary_top and \
                    moving_sprite.change_y > 0 and \
                    moving_sprite.top > moving_sprite.boundary_top:
                moving_sprite.change_y *= -1
            elif moving_sprite.boundary_bottom and \
                    moving_sprite.change_y < 0 and \
                    moving_sprite.bottom < moving_sprite.boundary_bottom:
                moving_sprite.change_y *= -1

            # Figure out and set our moving platform velocity.
            # Pymunk uses velocity is in pixels per second. If we instead have
            # pixels per frame, we need to convert.
            velocity = (moving_sprite.change_x * 1 / delta_time, moving_sprite.change_y * 1 / delta_time)
            self.physics_engine.set_velocity(moving_sprite, velocity)

    def on_draw(self):
        """ Draw everything """
        self.clear()
        self.wall_list.draw()
        self.moving_sprites_list.draw()
        self.item_list.draw()
        self.player_list.draw()


def main():
    """ Main function """
    window = GameWindow(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()