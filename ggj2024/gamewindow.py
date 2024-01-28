import pathlib
import random
import arcade
import pymunk

import numpy as np
from PIL import Image
from pathlib import Path
import time

from typing import Optional
from enum import Enum

from ggj2024.HandReceiver import HandReceiver
from ggj2024.config import *
from ggj2024.utils import normalize_vector, rotate90_cw, rotate90_ccw
from ggj2024.sprites import ParticleSprite, PlayerSprite, PhysicsSprite, ControllablePlatformSprite, DummyBoxSprite
from ggj2024.itemspawner import ItemSpawner, Entity
from ggj2024.region import Region


class MECHANICS(Enum):
    PLATFORMS = 1
    GRAVITY = 2


LEVELS = {
    1: {
        'tilemap': arcade.load_tilemap("resources/tiled_maps/Level1.json",
                                         SPRITE_SCALING_TILES),
        'mechanics': MECHANICS.PLATFORMS
    },
    2: {
        'tilemap': arcade.load_tilemap("resources/tiled_maps/Level2.json",
                                       SPRITE_SCALING_TILES),
        'mechanics': MECHANICS.GRAVITY
    },
    3: {
        'tilemap': arcade.load_tilemap("resources/tiled_maps/Level3.json",
                                       SPRITE_SCALING_TILES),
        'mechanics': MECHANICS.PLATFORMS
    },
    4: {
        'tilemap': arcade.load_tilemap("resources/tiled_maps/PitOfDoom.json",
                                       SPRITE_SCALING_TILES),
        'mechanics': MECHANICS.GRAVITY
    },
}

class GameWindow(arcade.Window):
    """ Main Window """

    def __init__(self, width, height, title, leap_motion=True):
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
        self.particle_list: Optional[arcade.SpriteList] = None
        self.background_list: Optional[arcade.SpriteList] = None
        self.soft_list: Optional[arcade.SpriteList] = None
        self.finish_list: Optional[arcade.SpriteList] = None
        self.spawned_item_list: Optional[arcade.SpriteList] = None

        self.spawnable_assets: list[str] = []

        self.regions: list[Region] = []
        self.entities: list[Entity] = []

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
        self.hands = HandReceiver()#

        self.splatter_texture_dict: dict[arcade.Sprite, Image.Image] = dict()
        self.splatter_counter = 0

        self.backgroundcolor_list = arcade.ShapeElementList()

        # Set background color
        arcade.set_background_color((0, 0, 0))

        self.current_level = 1
        self.respawn_player = False
        self.leap_motion = leap_motion
        self.level_transition = False

        # Loading the audio file
        self.audio_theme = arcade.load_sound('resources/sound/theme.mp3', False)
        hit_sound_files = list(pathlib.Path('resources/sound/animal').glob('*.wav')) + list(pathlib.Path('resources/sound/kenney_impact-sounds/Audio/').glob('*.ogg'))
        max_hitsounds = min(10, len(hit_sound_files))
        self.audio_hits = [arcade.load_sound(file, False) for file in hit_sound_files[:max_hitsounds]]

        self.start_tile: arcade.Sprite = None
        self.start_center: tuple[int, int] = None
        self.finish_tiles: arcade.Sprite = None

        # Playing the audio
        arcade.play_sound(self.audio_theme, 1.0, -1, True)

    def setup(self):
        """ Set up everything with the game """
        self.spawnable_assets = [str(fn) for fn in Path('assets/AFOPNGS/').glob('*.png')]

        # Create the sprite lists
        self.player_list = arcade.SpriteList()
        self.platform_list = arcade.SpriteList()

        self.mark_player_dead = None


        # Used for dragging shapes around with the mouse
        self.last_mouse_position = 0, 0
        self.last_mouse_position_left = 0, 0
        self.last_mouse_position_right = 0, 0

        self.spawnable_assets = [str(fn) for fn in Path('assets/AFOPNGS/').glob('*.png')]

        # Create player sprite
        self.player_sprite = PlayerSprite(hit_box_algorithm="Detailed")

        # Add to player sprite list
        self.player_list.append(self.player_sprite)

        # --- Pymunk Physics Engine Setup ---

        # The default damping for every object controls the percent of velocity
        # the object will keep each second. A value of 1.0 is no speed loss,
        # 0.9 is 10% per second, 0.1 is 90% per second.
        # For top-down games, this is basically the friction for moving objects.
        # For platformers with gravity, this should probably be set to 1.0.
        # Default value is 1.0 if not specified.
        self.damping = DEFAULT_DAMPING

        # Set the gravity. (0, 0) is good for outer space and top-down.
        # gravity = (0, -GRAVITY)

        self.load_level(self.current_level)

    def setup_platforms(self):
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
            sprite = ControllablePlatformSprite(shape)#, ":resources:images/tiles/boxCrate_double.png", width=2*size, height=size)
            self.platform_list.append(sprite)

        self.platform_left = self.platform_list[0]
        self.platform_right = self.platform_list[1]

        self.platform_left_collision = False
        self.platform_right_collision = False

    def load_level(self, level):
        self.current_level = level

        tile_map = LEVELS[self.current_level]['tilemap']
        self.map_bounds_x = tile_map.width * tile_map.tile_width * tile_map.scaling
        self.map_bounds_y = tile_map.height * tile_map.tile_height * tile_map.scaling
        self.map_bounds_unscaled = [tile_map.width * tile_map.tile_width, tile_map.height * tile_map.tile_height]

        color1 = (255,255,255)
        color2 = (87, 207, 255)
        points = (0, 0), (self.map_bounds_x , 0), (self.map_bounds_x, self.map_bounds_y), (0, self.map_bounds_x)
        colors = (color1, color1, color2, color2)
        rect = arcade.create_rectangle_filled_with_colors(points, colors)
        self.backgroundcolor_list.append(rect)

        self.width = int(min(self.width, self.map_bounds_x))
        self.height = int(min(self.height, self.map_bounds_y))
        self.camera = arcade.Camera(self.width, self.height)
        self.camera_speed_factor = CAMERA_SPEED

        self.particle_list = arcade.SpriteList()
        self.spawned_item_list = arcade.SpriteList()

        # Pull the sprite layers out of the tile map
        self.wall_list = tile_map.sprite_lists["Platforms"]
        self.item_list = tile_map.sprite_lists["Dynamic Items"]
        self.background_list = tile_map.sprite_lists["Background"]
        self.soft_list = tile_map.sprite_lists.get('Soft') or arcade.SpriteList()
        self.finish_list = tile_map.sprite_lists.get('Finish') or arcade.SpriteList()
        map_entities = tile_map.sprite_lists.get('Entities') or []
        map_objects = tile_map.object_lists.get('Regions') or []

        # Get player start from level
        start_sprite_list = tile_map.sprite_lists.get('Start')
        if start_sprite_list:
            start_sprite: arcade.Sprite = start_sprite_list[0]
            self.player_sprite.center_x = start_sprite.center_x
            self.player_sprite.center_y = start_sprite.center_y
            self.start_tile = start_sprite
            self.start_center = self.start_tile.center_x, self.start_tile.center_y
        else:
            print("WARNING: No start was defined, player will spawn in the center of the level")
            self.start_tile = None
            self.start_center = ((tile_map.width * SPRITE_SIZE) / 2, (tile_map.height * SPRITE_SIZE) / 2)
            self.player_sprite.center_x, self.player_sprite.center_y = self.start_center

        # Load objectes and entities
        regions = dict[int, Region]()
        for obj in (map_objects):
            print(f'Loading object (type={obj.type})')
            match obj.type:
                case 'region':
                    shape = [(x*tile_map.scaling, self.map_bounds_y + y*tile_map.scaling) for x, y in obj.shape]
                    region = Region(shape, self.player_sprite)
                    regions[obj.properties['id']] = region
                    self.regions.append(region)
                case _:
                    print(f"ERROR: unknown object type (=Class): {obj.type}")
                    continue

        for sprite in map_entities:
            t = sprite.properties.get('type')
            print(f'Loading entity (type={t})')
            match t:
                case 'object_spawner':
                    region_id = sprite.properties.get('active_region')
                    if region_id is None:
                        region = None
                    else:
                        region = regions.get(region_id)
                        if region is None:
                            print(f'WARNING: ObjectSpawner had an active region defined (id={region_id}) but it was not found')
                    interval = sprite.properties.get('interval') or 1.0
                    entity = ItemSpawner(sprite, self.item_spawned, self.spawnable_assets, max_scale=2, active_region=region, spawn_interval=interval)
                case _:
                    print(f"ERROR: unknown entity type (=Class): {sprite.properties.get('type')}")
                    continue
            self.entities.append(entity)
        # Get finish
        if not self.finish_list:
            print('WARNING: No finish was defined, this level is unbeatable!')

        # Create the physics engine
        self.physics_engine = arcade.PymunkPhysicsEngine(damping=self.damping,
                                                         gravity=tuple(
                                                             self.main_gravity))

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
        
        self.physics_engine.add_sprite_list(self.background_list,
                                            collision_type="background",
                                            body_type=arcade.PymunkPhysicsEngine.STATIC)
    
        self.physics_engine.add_sprite_list(self.soft_list,
                                            collision_type='soft',
                                            body_type=arcade.PymunkPhysicsEngine.STATIC,
                                            elasticity=1.0)
        
        self.physics_engine.add_sprite_list(self.finish_list,
                                            collision_type='finish',
                                            body_type=arcade.PymunkPhysicsEngine.STATIC)

        self.setup_platforms()

        # add platforms moved by second player
        self.physics_engine.add_sprite_list(
            self.platform_list,
            friction=DYNAMIC_ITEM_FRICTION,
            collision_type="platform",
            body_type=arcade.PymunkPhysicsEngine.KINEMATIC
        )

        # Collisions
        def handle_player_wall_collision(player_sprite: PlayerSprite, wall_sprite: arcade.sprite, arbiter: pymunk.Arbiter, space, data):
            impulse: pymunk.Vec2d = arbiter.total_impulse
            if self.mark_player_dead:
                return False
            if impulse.length > 500:
                # print('wall collision, impulse =', impulse.length)
                hit_sound = random.choice(self.audio_hits)
                arcade.play_sound(hit_sound, 1.0, -1, False)
            if impulse.length > PLAYER_DEATH_IMPULSE:
                print(f'died from wall (impulse={impulse.length})')
                self.mark_player_dead = 'Wall'
            return True

        def handle_player_item_collision(player_sprite: PlayerSprite, item_sprite: arcade.Sprite, arbiter: pymunk.Arbiter, space, data):
            impulse: pymunk.Vec2d = arbiter.total_impulse
            if self.mark_player_dead:
                return False
            if impulse.length > 500:
                # print('object collision, impulse =', impulse.length)
                hit_sound = random.choice(self.audio_hits)
                arcade.play_sound(hit_sound, 1.0, -1, False)
            if impulse.length > PLAYER_DEATH_IMPULSE:
                print(f'died from item (impulse={impulse.length})')
                self.mark_player_dead = 'Item'
            return True

        def handle_player_finish_collision(player: PlayerSprite, finish: arcade.Sprite, arbiter: pymunk.Arbiter, space, data):
            # TODO level done
            print('Congratulations, you reached the goal!')
            # return False to cancel collisions
            self.level_transition = True
            return False

        def handle_platform_collision(player: PlayerSprite, platform: arcade.Sprite, arbiter: pymunk.Arbiter, space, data):
            if platform == self.platform_left and self.platform_left_collision:
                return True
            if platform == self.platform_right and self.platform_right_collision:
                return True
            return False

        self.physics_engine.add_collision_handler('player', 'wall', post_handler=handle_player_wall_collision)
        self.physics_engine.add_collision_handler('player', 'item', post_handler=handle_player_item_collision)
        self.physics_engine.add_collision_handler('player', 'finish', begin_handler=handle_player_finish_collision)

        self.physics_engine.add_collision_handler('player', 'platform', begin_handler=handle_platform_collision)
        self.physics_engine.add_collision_handler('item', 'platform', begin_handler=handle_platform_collision)


        def handle_particle_x_collision(particle: ParticleSprite, other: arcade.Sprite, arbiter: pymunk.Arbiter, space, data):
            # HACK: store old width and height, reset them after changing the texture
            old_w, old_h = other.width, other.height
            self.physics_engine.remove_sprite(particle)
            self.particle_list.remove(particle)
            # position yields center of object, we need corner
            other_pos = pymunk.Vec2d(
                other.position[0] - other.width/2,
                other.position[1] - other.height/2)
            contact: pymunk.ContactPoint = arbiter.contact_point_set.points[0].point_b
            contact_rel: pymunk.Vec2d = contact - other_pos
            if other in self.splatter_texture_dict:
                image = self.splatter_texture_dict[other]
            else:
                image = other.texture.image.copy()
            tex_name = f'splatter_{self.splatter_counter}'
            self.splatter_counter += 1
            scale_x = image.width / other.width
            scale_y = image.height / other.height
            splatter = particle.texture.image
            splat_size = int(5*particle.radius)
            splatter = splatter.resize((splat_size, splat_size))
            # contact_rel *= scale
            # Make it apply to a little bit smaller region so that particles will be visible
            x = contact_rel.x * scale_x
            y = image.height - contact_rel.y * scale_y
            x -= splat_size/2
            y -= splat_size/2
            x = 0.95 * x
            y = 0.95 * y
            x += 0.05 * image.width
            y += 0.05 * image.height
            x = int(x)
            y = int(y)
            # Create alpha mask of original image, multiply it with that
            alphamask = np.array(image)[:,:,3:4].astype('float')/255.
            alphamask = np.ceil(alphamask)
            image.paste(splatter, (x, y, x+splat_size, y+splat_size), splatter)
            pixdata = np.array(image)
            masked = pixdata * alphamask
            image = Image.fromarray(masked.astype('uint8'))
            self.splatter_texture_dict[other] = image
            texture = arcade.Texture(tex_name, image)
            other.texture = texture
            other.width, other.height = old_w, old_h

        def handle_particle_background_collision(*args, **kwargs):
            if np.random.rand() > 0.7:
                return handle_particle_x_collision(*args, **kwargs)

        self.physics_engine.add_collision_handler('particle', 'wall', post_handler=handle_particle_x_collision)
        self.physics_engine.add_collision_handler('particle', 'item', post_handler=handle_particle_x_collision)
        self.physics_engine.add_collision_handler('particle', 'background', post_handler=handle_particle_x_collision, 
                                                  begin_handler=lambda *args: np.random.rand() > 0.5)
        self.physics_engine.add_collision_handler('particle', 'soft', post_handler=handle_particle_x_collision)
        self.physics_engine.add_collision_handler('particle', 'player', pre_handler=lambda *args: False)
        
        self.physics_engine.add_collision_handler('particle', 'finish', pre_handler=lambda *args: False)
        self.physics_engine.add_collision_handler('item', 'finish', pre_handler=lambda *args: False)
        self.physics_engine.add_collision_handler('wall', 'finish', pre_handler=lambda *args: False)
        self.physics_engine.add_collision_handler('soft', 'finish', pre_handler=lambda *args: False)

        self.physics_engine.add_collision_handler('background', 'player', pre_handler=lambda *args: False)
        self.physics_engine.add_collision_handler('background', 'item', pre_handler=lambda *args: False)
        self.physics_engine.add_collision_handler('background', 'finish', pre_handler=lambda *args: False)

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
            print('WARNING: It was attempted to set gravity to 0, setting it to a very low value instead')
            self._main_gravity = self._main_gravity_direction * 1e-9
            # No need to set direction vector as it didn't change
        if self.physics_engine:
            self.physics_engine.space.gravity = tuple(self._main_gravity)

    @property
    def main_gravity_dir(self):
        """The direction (= normalized vector) of the main gravity"""
        return self._main_gravity_direction

    def kill_player(self, reason):
        print('Player died:', reason)
        # Add 25 particles
        x, y = self.player_sprite.position
        particle_mass = 0.5
        for i in range(BLOOD_PER_SPLATTER):
            particle_size = np.random.rand()*BLOOD_PARTICLE_SIZE_RANGE + BLOOD_PARTICLE_SIZE_MIN
            particle = ParticleSprite(x, y, particle_size, particle_mass)
            self.particle_list.append(particle)
            self.physics_engine.add_sprite(particle, particle_mass, radius=particle_size, collision_type='particle')
            self.physics_engine.apply_impulse(particle, tuple((np.random.rand(2)-.5)*BLOOD_IMPULSE))

        self.physics_engine.set_position(self.player_sprite,
                                             self.start_center)

        self.mark_player_dead = None

    def spawn_item(self, filename, center_x, center_y, width, height, mass=5.0, friction=0.2, elasticity=None):
        """Spawn one of the diversifier items into the scene"""
        sprite = arcade.Sprite(filename)#, scale=0.5)
        # sprite.
        sprite.width = width
        sprite.height = height
        sprite.center_x = center_x
        sprite.center_y = center_y
        self.item_spawned(sprite, mass, friction, elasticity)
        return sprite

    def spawn_random_item(self, center_x, center_y, width=64, height=64, mass=5.0, friction=0.2, elasticity=None):
        return self.spawn_item(np.random.choice(self.spawnable_assets),
                               center_x, center_y, width, height, mass, friction, elasticity)

    def item_spawned(self, sprite, mass=5.0, friction=0.2, elasticity=None):
        while len(self.spawned_item_list) >= MAX_SPAWNED_ITEMS:
            removed = self.spawned_item_list.pop(0)
            self.physics_engine.remove_sprite(removed)
        self.spawned_item_list.append(sprite)
        self.physics_engine.add_sprite(sprite, mass, friction, elasticity, collision_type='item',
                                       max_velocity=ITEM_MAX_VELOCITY)
        

    # TODO: combinations of direction buttons could be done better, this is just for testing
    def update_gravity(self, hand_gesture_update=False):
        if not LEVELS[self.current_level]['mechanics'] == MECHANICS.GRAVITY:
            return

        if hand_gesture_update:
            if self.leap_motion:
                left_hand = (self.hands.left_hand.x, self.hands.left_hand.y)
                right_hand = (self.hands.right_hand.x, self.hands.right_hand.y)

                # update gravity based on hand positions of second player
                v = np.array(right_hand) - np.array(left_hand)

                if np.linalg.norm(v) < 1e-6:
                    return

                new_grav = (v[1], -v[0])
                new_grav = normalize_vector(new_grav) * GRAVITY

                fists_shown = self.hands.left_hand.grab_angle > FIST_THRESHOLD and self.hands.right_hand.grab_angle > FIST_THRESHOLD
                if fists_shown:
                    new_grav = -new_grav
            else:
                new_grav = np.array([SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2]) - np.array(self.last_mouse_position)
                new_grav = normalize_vector(new_grav) * GRAVITY
        else:
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

    def update_platforms(self):
        if not LEVELS[self.current_level]['mechanics'] == MECHANICS.PLATFORMS:
            return

        if self.leap_motion:
            # update platform positions based on second player input
            if self.platform_left:
                if not self.platform_left_collision and self.hands.left_hand.grab_angle > FIST_THRESHOLD:
                    self.platform_left_collision = True
                    self.platform_left.set_opaque(True)
                if self.platform_left_collision and self.hands.left_hand.grab_angle < FIST_THRESHOLD:
                    self.platform_left_collision = False
                    self.platform_left.set_opaque(False)

                if not self.platform_left_collision:
                    lx = self.hands.left_hand.x
                    ly = self.hands.left_hand.y
                    pos = (self.camera.position.x + self.width/2 + lx, self.camera.position.y + ly)
                    self.physics_engine.set_position(self.platform_left, pos)

            if self.platform_right:
                if not self.platform_right_collision and self.hands.right_hand.grab_angle > FIST_THRESHOLD:
                    self.platform_right_collision = True
                    self.platform_right.set_opaque(True)
                if self.platform_right_collision and self.hands.right_hand.grab_angle < FIST_THRESHOLD:
                    self.platform_right_collision = False
                    self.platform_right.set_opaque(False)

                if not self.platform_right_collision:
                    rx = self.hands.right_hand.x
                    ry = self.hands.right_hand.y
                    pos = (self.camera.position.x + self.width/2 + rx, self.camera.position.y + ry)
                    self.physics_engine.set_position(self.platform_right, pos)
        else:
            # update platform position based on mouse input
            if self.platform_left:
                pos = tuple(self.camera.position + pymunk.Vec2d(self.last_mouse_position_left[0], self.last_mouse_position_left[1]))
                self.physics_engine.set_position(self.platform_left, pos)
            if self.platform_right:
                pos = tuple(self.camera.position + pymunk.Vec2d(self.last_mouse_position_right[0], self.last_mouse_position_right[1]))
                self.physics_engine.set_position(self.platform_right, pos)

    def next_level(self):
        available_levels = list(sorted(LEVELS.keys()))
        next_index = (available_levels.index(self.current_level) + 1) % len(
            available_levels)
        next_level = available_levels[next_index]
        self.load_level(next_level)

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
                        impulse = -self.main_gravity_dir * PLAYER_JUMP_IMPULSE
                        impulse = tuple(impulse)
                    self.physics_engine.apply_impulse(self.player_sprite, impulse)

            case arcade.key.ENTER:
                self.enter_pressed = True
                self.next_level()

            case arcade.key.DELETE:
                self.mark_player_dead = 'keyboard'
        if key == arcade.key.LEFT:
            self.left_pressed = True
            self.update_gravity()
        elif key == arcade.key.RIGHT:
            self.right_pressed = True
            self.update_gravity()
        elif key == arcade.key.UP:
            self.up_pressed = True
            self.update_gravity()
        elif key == arcade.key.DOWN:
            self.down_pressed = True
            self.update_gravity()

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
        if self.leap_motion:
            # mouse interaction is only required when debugging
            return

        match button:
            case arcade.MOUSE_BUTTON_LEFT:
                self.last_mouse_position_left = x, y
                self.platform_left = self.platform_list[0]
            case arcade.MOUSE_BUTTON_RIGHT:
                self.last_mouse_position_right = x, y
                self.platform_right = self.platform_list[1]
            case arcade.MOUSE_BUTTON_MIDDLE:
                # HACK debug: spawn random item
                print('spawning item at', x, y)
                self.spawn_random_item(x + self.camera.position.x,
                                       y + self.camera.position.y, 64, 64,
                                       mass=50)

                # # Test: spawn box
                # sprite = DummyBoxSprite(x, y, 32, 10.0)
                # self.item_list.append(sprite)
                # body = sprite.pymunk_shape.body
                # self.physics_engine.add_sprite(sprite, body.mass)

    def on_mouse_release(self, x, y, button, modifiers):
        if self.leap_motion:
            # mouse interaction is only required when debugging
            return

        match button:
            case arcade.MOUSE_BUTTON_LEFT:
                self.platform_left = None
            case arcade.MOUSE_BUTTON_RIGHT:
                self.platform_right = None

    def on_mouse_motion(self, x, y, dx, dy):
        if self.platform_left is not None:
            self.last_mouse_position_left = (x, y)
        if self.platform_right is not None:
            self.last_mouse_position_right = (x, y)
        self.last_mouse_position = (x, y)

    def on_update(self, delta_time):
        """ Movement and game logic """
        if self.mark_player_dead:
            self.kill_player(self.mark_player_dead)

        # Rotate player to gravity
        player_object = self.physics_engine.get_physics_object(self.player_sprite)
        gravity_angle = np.arctan2(*self.main_gravity_dir)
        player_object.shape.body.angle = np.pi - gravity_angle
        player_velocity: pymunk.Vec2d = player_object.body.velocity.rotated(gravity_angle)
        speed = -player_velocity.x

        # Update player based on key press
        is_on_ground = self.physics_engine.is_on_ground(self.player_sprite)
        movement_force = PLAYER_MOVE_FORCE_ON_GROUND if is_on_ground else PLAYER_MOVE_FORCE_IN_AIR
        speed_limit = PLAYER_MAX_WALKING_SPEED if is_on_ground else PLAYER_MAX_AIRCONTROL_SPEED
        if self.a_pressed and not self.d_pressed:
            # Create a force to the left, perpendicular to the gravity.
            # Gravity pulls down so this actually needs to be the gravity rotated *clockwise*
            if FORCES_RELATIVE_TO_PLAYER:
                if not(speed <= -speed_limit):
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
                if not(speed >= speed_limit):
                    self.physics_engine.apply_force(self.player_sprite, (movement_force, 0))
            else:
                force_dir = rotate90_ccw(self.main_gravity_dir)
                self.apply_force_to_player(force_dir, PLAYER_MOVE_FORCE_ON_GROUND if is_on_ground else PLAYER_MOVE_FORCE_IN_AIR)
            # Set friction to zero for the player while moving
            # TODO: is this really a good idea?
            self.physics_engine.set_friction(self.player_sprite, 0)
        elif self.w_pressed and not self.s_pressed:
            pass
        elif self.s_pressed and not self.w_pressed:
            pass
        else:
            # Player's feet are not moving. Therefore up the friction so we stop.
            self.physics_engine.set_friction(self.player_sprite, 1.0)

        # Delete old blood
        new_particle_list = arcade.SpriteList()
        t = time.time()
        for blood in self.particle_list:
            if isinstance(blood, ParticleSprite) and t >= blood.killtime:
                self.physics_engine.remove_sprite(blood)
            else:
                new_particle_list.append(blood)
        self.particle_list = new_particle_list

        self.update_gravity(hand_gesture_update=True)
        self.update_platforms()
        for entity in self.entities:
            entity.update()

        # Move items in the physics engine
        for _ in range(0,STEPS_PER_FRAME):
            self.physics_engine.step(delta_time=1/(60*STEPS_PER_FRAME))

        x_inbounds = (0 <= self.player_sprite.center_x <= self.map_bounds_x)
        y_inbounds = (0 <= self.player_sprite.center_y <= self.map_bounds_y)
        if not (x_inbounds and y_inbounds):
            self.mark_player_dead = 'out_of_bounds'

        if self.level_transition:
            self.next_level()
            self.level_transition = False

        self.scroll_to_player()

    def scroll_to_player(self):
        """
        Scroll the window to the player.

        if CAMERA_SPEED is 1, the camera will immediately move to the desired position.
        Anything between 0 and 1 will have the camera move to the location with a smoother
        pan.
        """

        map_bounds = np.array([self.map_bounds_x, self.map_bounds_y])
        camera_size = np.array([self.camera.viewport_width, self.camera.viewport_height])

        target_position = np.array([self.player_sprite.center_x - self.width / 2,
                        self.player_sprite.center_y - self.height / 2])
        target_position = np.max([target_position, np.zeros(2)], axis=0)
        target_position = np.min([target_position, map_bounds-camera_size], axis=0)

        camera_speed = min(np.linalg.norm(target_position - np.array(self.camera.position)) * self.camera_speed_factor, 1)

        self.camera.move_to(pymunk.Vec2d(*tuple(target_position)), camera_speed)

    def on_draw(self):
        """ Draw everything """
        self.clear()
        self.camera.use()
        self.backgroundcolor_list.draw()
        self.background_list.draw()
        self.wall_list.draw()
        self.platform_list.draw()
        self.item_list.draw()
        self.spawned_item_list.draw()
        self.player_list.draw()
        self.soft_list.draw()
        for entity in self.entities:
            entity.draw()
        self.particle_list.draw()