import time
import pathlib
from pathlib import Path
import random
import traceback
from typing import Optional
from enum import Enum
from dataclasses import dataclass

import arcade
import pymunk
import pyglet.input

import numpy as np
from PIL import Image

try: 
    import leap
    LEAP_AVAILABLE = True
except ImportError:
    LEAP_AVAILABLE = False

if LEAP_AVAILABLE:
    from ggj2024.HandReceiver import HandReceiver
else:
    from ggj2024.HandReceiver import HandReceiverBase as HandReceiver

from ggj2024.config import *
from ggj2024.utils import *
from ggj2024.sprites import ParticleSprite, PlayerControlledPlatformSprite, PlayerSprite, SPRITESETS
from ggj2024.itemspawner import ItemSpawner, Entity
from ggj2024.region import Region
from ggj2024.physics_engine import PhysicsEngine



class MECHANICS(Enum):
    PLATFORMS = 1
    GRAVITY = 2


LEVELS = {
    1: {
        'tilemap': arcade.load_tilemap("resources/tiled_maps/Level1.json",
                                       SPRITE_SCALING_TILES),
        'theme': arcade.load_sound('resources/sound/theme_calm.mp3', False),
        'mechanics': MECHANICS.PLATFORMS
    },
    2: {
        'tilemap': arcade.load_tilemap("resources/tiled_maps/Level2.json",
                                       SPRITE_SCALING_TILES),
        'theme': arcade.load_sound('resources/sound/theme_fast.mp3', False),
        'mechanics': MECHANICS.GRAVITY
    },
    3: {
        'tilemap': arcade.load_tilemap("resources/tiled_maps/Level3.json",
                                       SPRITE_SCALING_TILES),
        'theme': arcade.load_sound('resources/sound/theme.mp3', False),
        'mechanics': MECHANICS.PLATFORMS
    },
    4: {
        'tilemap': arcade.load_tilemap("resources/tiled_maps/PitOfDoom.json",
                                       SPRITE_SCALING_TILES),
        'theme': arcade.load_sound('resources/sound/theme_fast.mp3', False),
        'mechanics': MECHANICS.GRAVITY
    },
}

STEP_DELTA_T = 1/(60*STEPS_PER_FRAME)


class GameWindow(arcade.Window):
    """ Main Window """

    def __init__(self, width, height, title, leap_motion=True, debug=False):
        """ Create the variables """

        # Init the parent class
        super().__init__(width, height, title)

        self.leap_motion = leap_motion
        self.debug = debug

        # Physics engine
        self.physics_engine: Optional[PhysicsEngine] = None

        # Player sprite
        self.player_sprite: Optional[PlayerSprite] = None

        # Sprite lists we need
        self.player_list: Optional[arcade.SpriteList] = None
        self.wall_list: Optional[arcade.SpriteList] = None
        self.item_list: Optional[arcade.SpriteList] = None
        self.moving_sprites_list: Optional[arcade.SpriteList] = None
        self.controllable_platform_list: Optional[arcade.SpriteList] = None
        self.particle_list: Optional[arcade.SpriteList] = None
        self.background_list: Optional[arcade.SpriteList] = None
        self.soft_list: Optional[arcade.SpriteList] = None
        self.finish_list: Optional[arcade.SpriteList] = None
        self.spawned_item_list: Optional[arcade.SpriteList] = None

        self.debug_sprite_list: Optional[arcade.SpriteList] = None

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
        self.shift_pressed: bool = False

        self.left_pressed: bool = False
        self.right_pressed: bool = False
        self.up_pressed: bool = False
        self.down_pressed: bool = False
        if self.leap_motion:
            self.hands = HandReceiver()
        else:
            self.hands = None
            
        self.splatter_texture_dict: dict[arcade.Sprite, arcade.Texture] = {}
        # self.splatter_texture_dict: dict[arcade.Sprite, Image.Image] = dict()
        self.splatter_counter = 0

        self.backgroundcolor_list = arcade.ShapeElementList()

        # Set background color
        arcade.set_background_color((0, 0, 0))

        self.current_level = 1
        self.respawn_player = False
        self.level_transition = False

        # Loading the audio file
        hit_sound_files = list(pathlib.Path('resources/sound/kenney_impact-sounds/Audio/').glob('*.ogg'))
        animal_sound_files = list(pathlib.Path('resources/sound/animal').glob('*.wav'))
        max_hitsounds = min(20, len(hit_sound_files))
        self.audio_hits = [arcade.load_sound(file, False) for file in hit_sound_files[:max_hitsounds]]
        self.audio_animals = [arcade.load_sound(file, False) for file in animal_sound_files]

        self.start_tile: arcade.Sprite = None
        self.start_center: tuple[int, int] = None
        self.finish_tiles: arcade.Sprite = None

        self.active_theme = None
        self.music_on = not MUTE_MUSIC

        self.platform_left: PlayerControlledPlatformSprite = None
        self.platform_right: PlayerControlledPlatformSprite = None

        self.controller: Optional[pyglet.input.Controller] = None

    def setup(self):
        """ Set up everything with the game """
        controllers = pyglet.input.get_controllers()
        print(f'Found {len(controllers)} controllers')
        for controller in controllers:
            print(controller)
        if controllers:
            print(f'Choosing first controller')
            self.controller = controller
            self.controller.open()
            @self.controller.event
            def on_button_press(*args):
                return self.on_controller_button_pressed(*args)
            @self.controller.event
            def on_button_release(*args):
                return self.on_controller_button_released(*args)
            @self.controller.event
            def on_trigger_motion(*args):
                return self.on_controller_trigger_motion(*args)
            @self.controller.event
            def on_stick_motion(*args):
                return self.on_controller_stick_motion(*args)
            @self.controller.event
            def on_dpad_motion(*args):
                return self.on_controller_dpad_motion(*args)

        self.spawnable_assets = [str(fn) for fn in Path('assets/AFOPNGS/').glob('*.png')]

        # Create the sprite lists
        self.player_list = arcade.SpriteList()

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

        # The default damping for every object controls the percent of velocity
        # the object will keep each second. A value of 1.0 is no speed loss,
        # 0.9 is 10% per second, 0.1 is 90% per second.
        # For top-down games, this is basically the friction for moving objects.
        # For platformers with gravity, this should probably be set to 1.0.
        # Default value is 1.0 if not specified.
        self.damping = DEFAULT_DAMPING

        self.load_level(self.current_level)


            

    def setup_platforms(self):
        # player-controlled platforms

        self.controllable_platform_list = arcade.SpriteList()
        tiles = SPRITESETS.GENERAL.get_tiles_by_class('PlayerControlledPlatform')
        if not tiles:
            raise RuntimeError('Could not find tile for PlayerControlledPlaform')
        elif len(tiles) > 1:
            print('WARNING: More than one PlayerControlledPlatform tile defined')
        tile = tiles[0]
        for i in range(2):
            sprite = SPRITESETS.GENERAL.create_sprite(tile, custom_class=PlayerControlledPlatformSprite)
            self.controllable_platform_list.append(sprite)

        self.platform_left = self.controllable_platform_list[0]
        self.platform_right = self.controllable_platform_list[1]

        if self.debug:
            self.platform_left.active = True
            self.platform_right.active = True

    def load_level(self, level):
        self.current_level = level

        self.main_gravity = np.array([0, -GRAVITY], dtype='float')

        # Playing the audio
        if self.active_theme:
            arcade.stop_sound(self.active_theme)
        self.active_theme = arcade.play_sound(LEVELS[self.current_level]['theme'], 1.0 if self.music_on else 0.0, -1, True)

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

        self.splatter_texture_dict: dict[arcade.Sprite, arcade.Texture] = {}

        self.width = int(min(self.width, self.map_bounds_x))
        self.height = int(min(self.height, self.map_bounds_y))
        self.camera = arcade.Camera(self.width, self.height)
        self.camera_speed_factor = CAMERA_SPEED

        self.particle_list = arcade.SpriteList()
        self.spawned_item_list = arcade.SpriteList()
        self.debug_sprite_list = arcade.SpriteList()

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

        try:
            for e in self.entities:
                self.physics_engine.remove_sprite(e.sprite)
        except: pass
        self.entities = [] 
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
        self.physics_engine = PhysicsEngine(damping=self.damping,
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
                                       max_vertical_velocity=PLAYER_MAX_VERTICAL_SPEED,
                                       disable_collisions_for=['particle', 'background'])

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
        # Create backgrounds
        self.physics_engine.add_sprite_list(self.background_list,
                                            collision_type="background",
                                            body_type=arcade.PymunkPhysicsEngine.STATIC,
                                            disable_collisions_for=['player', 'item', 'wall', 'soft', 'finish'])
        # Create soft static objects        
        self.physics_engine.add_sprite_list(self.soft_list,
                                            collision_type='soft',
                                            body_type=arcade.PymunkPhysicsEngine.STATIC,
                                            elasticity=1.0)
        # Create the items
        self.physics_engine.add_sprite_list(self.item_list,
                                            friction=DYNAMIC_ITEM_FRICTION,
                                            collision_type="item",
                                            disable_collisions_for=['background', 'finish'])
        # Create finish object
        self.physics_engine.add_sprite_list(self.finish_list,
                                            collision_type='finish',
                                            body_type=arcade.PymunkPhysicsEngine.STATIC,
                                            disable_collisions_for=['item', 'wall', 'soft', 'finish'])

        # add platforms moved by second player
        self.setup_platforms()
        self.physics_engine.add_sprite_list(self.controllable_platform_list,
                                            friction=DYNAMIC_ITEM_FRICTION,
                                            collision_type="platform",
                                            body_type=arcade.PymunkPhysicsEngine.KINEMATIC,
                                            disable_collisions_for=['background', 'particle'])

        # Collisions
        def handle_player_wall_collision(player_sprite: PlayerSprite, wall_sprite: arcade.sprite, arbiter: pymunk.Arbiter, space, data):
            if self.mark_player_dead:
                return False
            self.play_collision_hit_sound(arbiter)
            impulse: pymunk.Vec2d = arbiter.total_impulse
            if impulse.length > PLAYER_DEATH_IMPULSE:
                print(f'died from wall (impulse={impulse.length})')
                self.mark_player_dead = 'Wall'
            return True

        def handle_player_item_collision(player_sprite: PlayerSprite, item_sprite: arcade.Sprite, arbiter: pymunk.Arbiter, space, data):
            if self.mark_player_dead:
                return False
            self.play_collision_hit_sound(arbiter)
            impulse: pymunk.Vec2d = arbiter.total_impulse
            if impulse.length > PLAYER_DEATH_IMPULSE:
                print(f'died from item (impulse={impulse.length})')
                self.mark_player_dead = 'Item'
            return True

        def handle_player_finish_collision(player: PlayerSprite, finish: arcade.Sprite, arbiter: pymunk.Arbiter, space, data):
            print('Congratulations, you reached the goal!')
            self.level_transition = True
            return False

        def handle_platform_collision(player: PlayerSprite, platform: PlayerControlledPlatformSprite, arbiter: pymunk.Arbiter, space, data):
            # If platform is active: return True => continue with collision
            # Else: return False to ignore collision
            return platform.active

        self.physics_engine.add_collision_handler('player', 'wall', post_handler=handle_player_wall_collision)
        self.physics_engine.add_collision_handler('player', 'item', post_handler=handle_player_item_collision)
        self.physics_engine.add_collision_handler('player', 'finish', begin_handler=handle_player_finish_collision)

        self.physics_engine.add_collision_handler('player', 'platform', begin_handler=handle_platform_collision)
        self.physics_engine.add_collision_handler('item', 'platform', begin_handler=handle_platform_collision)

        def handle_item_wall_collision(item: arcade.Sprite, wall: arcade.Sprite, arbiter: pymunk.Arbiter, space, data):
            self.play_collision_hit_sound(arbiter)

        self.physics_engine.add_collision_handler('item', 'wall', post_handler=handle_item_wall_collision)
        self.physics_engine.add_collision_handler('item', 'item', post_handler=handle_item_wall_collision)

        # This is what draws the blood splatters onto the walls and items
        def handle_particle_collision(particle: ParticleSprite, other: arcade.Sprite, arbiter: pymunk.Arbiter, space: pymunk.Space, data):
            """Handle a collision between a blood particle and a static object (walls, backgrounds)"""
            try:
                if particle not in self.physics_engine.sprites:
                    # Was already removed by other collision...? Happens quite often
                    # TODO: investigate this. Is this a bug and can this be avoided? (performance)
                    return False
                
                particle_obj: arcade.PymunkPhysicsObject = self.physics_engine.get_physics_object(particle)
                impact_v = particle_obj.body.velocity
                impact_pos: pymunk.Vec2d = arbiter.contact_point_set.points[0].point_b
                
                # TODO: normal or uniform distribution?
                additional_movement = abs(np.random.normal() * BLOOD_SPLATTER_IMPACT_RANGE) * impact_v
                splatter_pos = impact_pos + additional_movement
                
                if DEBUG_BLOOD_SPLATTER:
                    # Draw a small dot at final splatter position
                    dbg_sprite_final = arcade.SpriteCircle(1, (0, 0, 255))
                    dbg_sprite_final.position = splatter_pos
                    self.debug_sprite_list.append(dbg_sprite_final)

                collision_filter = self.physics_engine.make_shapefilter(['wall', 'background', 'soft', 'item'], categories='particle')
                collisions = space.point_query(splatter_pos, max_distance=int(particle.radius), shape_filter=collision_filter)
                if DEBUG_BLOOD_SPLATTER:
                    print('Collision with', len(collisions), 'shapes')

                if collisions:
                    # These are the same for all collided tiles and are only needed *if* there is a collision
                    splatter_radius = particle.radius * BLOOD_WALL_SIZE_MULTIPLIER
                    splatter = create_circle_image(splatter_radius * 2, particle.color, BLOOD_WALL_ANTIALIASING)
                    splatter_array = np.array(splatter).astype('float') / 255

                for i, collision_info in enumerate(collisions):
                    # TODO: this operation is O(n), find better solution
                    collided_sprite = self.physics_engine.get_sprite_for_shape(collision_info.shape)

                    tex_image = collided_sprite.texture.image
                    sprite_size = np.array([collided_sprite.width, collided_sprite.height])
                    image_size = np.array([tex_image.width, tex_image.height])
                    sprite_scale = image_size / sprite_size
                    
                    pos_in_sprite = np.array(self.point_to_sprite(sprite=collided_sprite, point=splatter_pos))
                    pos_in_image = sprite_scale * pos_in_sprite
                    pos_in_image[1] = tex_image.height - pos_in_image[1]
                    # Draw centered
                    pos_in_image -= splatter_radius

                    tex_array = np.array(tex_image).astype('float') / 255
                    new_img = alpha_composite(tex_array, splatter_array, tuple(pos_in_image.astype(int)), inplace=True, mask_fg_with_bg=True) * 255
                    tex_image = Image.fromarray(new_img.astype('uint8'))

                    # Use textures in the texture dict instead of creating a new one every time
                    texture: arcade.Texture = self.splatter_texture_dict.get(collided_sprite)
                    if texture is None:
                        # No splatter texture created for this sprite yet, create one
                        tex_name = f'splatter_{self.splatter_counter}'
                        self.splatter_counter += 1
                        texture = arcade.Texture(tex_name, tex_image)
                        self.splatter_texture_dict[collided_sprite] = texture
                        # HACK: just restore sprite size (gets reset on texture change)
                        collided_sprite.texture = texture
                        collided_sprite.width, collided_sprite.height = sprite_size
                    else:
                        # Re-use the existing texture
                        texture.image = tex_image
                        self.ctx.default_atlas.update_texture_image(texture)
                        # No need to re-apply the texture to the sprite since it is already the active one

                # Collision handled, remove particle
                self.physics_engine.remove_sprite(particle)
                self.particle_list.remove(particle)
            except Exception as err:
                traceback.print_exception(err)
            # Sprite is removed, don't continue collision
            return False
        
        self.physics_engine.add_collision_handler('particle', 'wall', begin_handler=handle_particle_collision)
        self.physics_engine.add_collision_handler('particle', 'soft', begin_handler=handle_particle_collision)
        self.physics_engine.add_collision_handler('particle', 'item', begin_handler=handle_particle_collision)
        self.physics_engine.add_collision_handler('particle', 'background', begin_handler=handle_particle_collision)


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

    @property
    def music_on(self):
        return self._music_on
    @music_on.setter
    def music_on(self, value):
        self._music_on = value
        if self.active_theme:
            self.active_theme.volume = 1.0 if self._music_on else 0.0
    
    def point_to_sprite(self, sprite: arcade.Sprite, point: pymunk.Vec2d | tuple):
        """Convert a point from world space to sprite space (0, 0 is the bottom left corner of the sprite)"""
        if not isinstance(point, pymunk.Vec2d):
            point = pymunk.Vec2d(*point)
        # Sprite's position is unreliable, use physics object
        body = self.physics_engine.get_physics_object(sprite).body
        # Get position on the top left (default is center)
        s_rot = body.angle
        if s_rot == 0.0:
            # No rotation, simple case
            return point - body.position + pymunk.Vec2d(sprite.width/2, sprite.height/2)
        # Handle rotation
        s_pos: pymunk.Vec2d = point - body.position
        s_pos = s_pos.rotated(-s_rot)
        return s_pos + pymunk.Vec2d(sprite.width/2, sprite.height/2)
        

    def kill_player(self, reason):
        print('Player died:', reason)
        self.play_random_sound(self.audio_animals, volume=0.8)
        self.spawn_blood_particles(self.player_sprite.position, BLOOD_PARTICLES_PER_SPLATTER)
        self.physics_engine.set_position(self.player_sprite,
                                             self.start_center)
        self.mark_player_dead = None
    
    def spawn_blood_particles(self, position, count):
        x, y = position
        particle_mass = 0.5
        for i in range(count):
            particle_size = np.random.rand()*BLOOD_PARTICLE_SIZE_RANGE + BLOOD_PARTICLE_SIZE_MIN
            particle = ParticleSprite(x, y, particle_size, particle_mass)
            self.particle_list.append(particle)
            self.physics_engine.add_sprite(particle, particle_mass, radius=particle_size, collision_type='particle')
            self.physics_engine.apply_impulse(particle, tuple((np.random.rand(2)-.5)*BLOOD_IMPULSE))


    def play_random_sound(self, sounds,  volume: float = 1.0):
        hit_sound = random.choice(sounds)
        arcade.play_sound(hit_sound, volume, -1, False)

    def play_collision_hit_sound(self, arbiter: pymunk.Arbiter):
        p = arbiter.total_impulse.length
        if p > HITSOUND_MIN_IMPULSE:
            vol = (p - HITSOUND_MIN_IMPULSE) / HITSOUND_RANGE
            self.play_random_sound(self.audio_hits, min(1.0, vol))

    def spawn_item(self, filename, center_x, center_y, width, height, mass=5.0, friction=0.2, elasticity=None):
        """Spawn one of the diversifier items into the scene"""
        sprite = arcade.Sprite(filename)
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
        self.physics_engine.add_sprite(sprite, 
                                       mass, 
                                       friction, 
                                       elasticity, 
                                       max_velocity=ITEM_MAX_VELOCITY,
                                       collision_type='item',
                                       disable_collisions_for=['backround', 'finish']
                                       )
        
    @property
    def current_mechanics(self):
        return LEVELS[self.current_level]['mechanics']

    def update_gravity(self):
        if not self.current_mechanics == MECHANICS.GRAVITY:
            return
        new_grav = None

        if self.debug:
            pass
            # This one will set gravity to 0 if two opposite keys are pressed, is this good...?
            # TODO: maybe also make mouse controlled gravity an optional feature and include this one again?
            new_grav = np.array([0, 0], dtype='float')
            if self.left_pressed and not self.right_pressed:
                new_grav[0] = -GRAVITY
            elif self.right_pressed and not self.left_pressed:
                new_grav[0] = GRAVITY
            if self.up_pressed and not self.down_pressed:
                new_grav[1] = GRAVITY
            elif self.down_pressed and not self.up_pressed:
                new_grav[1] = -GRAVITY
        else:
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
            elif self.controller:
                stick_dir = pymunk.Vec2d(self.controller.rightx, self.controller.righty)
                if stick_dir.length > CONTROLLER_STICK_GRAVITY_DEADZONE:
                    new_grav = stick_dir.normalized() * 2000
            else:
                new_grav = np.array([SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2]) - np.array(self.last_mouse_position)
                new_grav = normalize_vector(new_grav) * GRAVITY
        if new_grav is not None:
            self.main_gravity = new_grav

    def update_platforms(self):
        if not LEVELS[self.current_level]['mechanics'] == MECHANICS.PLATFORMS:
            return

        if self.debug:
            # update platform position based on mouse input
            if not self.platform_left.active:
                pos = tuple(self.camera.position + pymunk.Vec2d(self.last_mouse_position_left[0], self.last_mouse_position_left[1]))
                self.physics_engine.set_position(self.platform_left, pos)
            if not self.platform_right.active:
                pos = tuple(self.camera.position + pymunk.Vec2d(self.last_mouse_position_right[0], self.last_mouse_position_right[1]))
                self.physics_engine.set_position(self.platform_right, pos)
        
        elif self.leap_motion:
            # update platform positions based on second player input
            for platform, hand in [(self.platform_left, self.hands.left_hand), (self.platform_right, self.hands.right_hand)]:
                if not platform or not hand:
                    continue
                if platform.active and hand.grab_angle > FIST_THRESHOLD:
                    platform.active = True
                elif not platform.active and hand.grab_angle < FIST_THRESHOLD:
                    platform.active = False
                if not platform.active:
                    pos = (self.camera.position.x + self.width/2 + hand.x,
                           self.camera.position.y + self.height/2 + hand.y)
                    self.physics_engine.set_position(platform, pos)

        elif self.controller:
            lt = self.controller.lefttrigger < CONTROLLER_TRIGGER_PLATFORM_THRESHOLD
            rt = self.controller.righttrigger < CONTROLLER_TRIGGER_PLATFORM_THRESHOLD
            cx = self.controller.rightx * CONTROLLER_PLATFORM_MULTIPLIER
            cy = self.controller.righty * CONTROLLER_PLATFORM_MULTIPLIER
            for platform, trigger in [(self.platform_left, lt), (self.platform_right, rt)]:
                if not platform:
                    continue
                if not platform.active and trigger:
                    platform.active = True
                elif platform.active and not trigger:
                    platform.active = False
                if not platform.active:
                    pos = (self.camera.position.x + self.width/2 + cx, self.camera.position.y + self.height/2 + cy)
                    self.physics_engine.set_position(platform, pos)


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
                self.player_sprite.jump(self.physics_engine)

            case arcade.key.ENTER:
                self.enter_pressed = True
                self.next_level()
            case arcade.key.DELETE:
                self.mark_player_dead = 'keyboard'
            
            case arcade.key.M:
                self.music_on = not self.music_on

            case arcade.key.LEFT:
                self.left_pressed = True
            case arcade.key.RIGHT:
                self.right_pressed = True
            case arcade.key.UP:
                self.up_pressed = True
            case arcade.key.DOWN:
                self.down_pressed = True

        if modifiers & arcade.key.MOD_SHIFT:
            self.shift_pressed = True
        else:
            self.shift_pressed = False

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
                
        if modifiers & arcade.key.MOD_SHIFT:
            self.shift_pressed = True
        else:
            self.shift_pressed = False

    def on_mouse_press(self, x, y, button, modifiers):
        """ Called whenever the mouse button is clicked. """
        if not self.debug:
            # mouse interaction is only required when debugging
            return

        match button:
            case arcade.MOUSE_BUTTON_LEFT:
                self.last_mouse_position_left = x, y
                pos = tuple(self.camera.position + pymunk.Vec2d(x, y))
                self.physics_engine.set_position(self.platform_left, pos)
            case arcade.MOUSE_BUTTON_RIGHT:
                self.last_mouse_position_right = x, y
                pos = tuple(self.camera.position + pymunk.Vec2d(x, y))
                self.physics_engine.set_position(self.platform_right, pos)
            case arcade.MOUSE_BUTTON_MIDDLE:
                pos = (self.camera.position.x + x,
                       self.camera.position.y + y)
                # Use this to spawn blood particles:
                self.spawn_blood_particles(pos, 50)
                # Use this to spawn random items:
                # self.spawn_random_item(*pos, 64, 64, mass=50)

    def on_mouse_release(self, x, y, button, modifiers):
        if not self.debug:
            # mouse interaction is only required when debugging
            return

    def on_mouse_motion(self, x, y, dx, dy):
        self.last_mouse_position = (x, y)

    def on_controller_button_pressed(self, controller, button):
        match button:
            case 'a':
                self.player_sprite.jump(self.physics_engine)
            case 'b':
                self.player_sprite.jump(self.physics_engine)
                pass
            case 'x':
                pass
            case 'y':
                pass
            case _:
                print('Unknown button', button, 'pressed')
    
    def on_controller_button_released(self, controller, button):
        match button:
            case 'a':
                pass
            case 'b':
                pass
            case 'x':
                pass
            case 'y':
                pass
            case _:
                print('Unknown button', button, 'released')
    
    def on_controller_stick_motion(self, controller, name, x_val, y_val):
        match name:
            case 'leftstick':
                if x_val > CONTROLLER_STICK_WALK_DEADZONE:
                    self.d_pressed = True
                elif x_val < -CONTROLLER_STICK_WALK_DEADZONE:
                    self.a_pressed = True
                else:
                    self.a_pressed = self.d_pressed = False
            case 'rightstick':
                pass
    
    def on_controller_trigger_motion(self, controller, name, value):
        pass

    def on_controller_dpad_motion(self, controller, left, right, up, down):
        # print('dpad', left, right, up, down)
        pass
    
    def is_player_sprinting(self):
        if self.controller:
            if self.controller.x or self.controller.y:
                return True
        if self.shift_pressed:
            return True
        return False

    def do_physics_step(self, delta_time, resync_sprites: bool):
        """ Movement and game logic """
        player_object = self.physics_engine.get_physics_object(self.player_sprite)
        
        x_inbounds = (0 <= player_object.body.position.x <= self.map_bounds_x)
        y_inbounds = (0 <= player_object.body.position.y <= self.map_bounds_y)
        if not (x_inbounds and y_inbounds):
            self.mark_player_dead = 'out_of_bounds'

        if self.mark_player_dead:
            self.kill_player(self.mark_player_dead)

        # Rotate player to gravity
        gravity_angle = np.arctan2(*self.main_gravity_dir)
        player_object.shape.body.angle = np.pi - gravity_angle
        player_velocity: pymunk.Vec2d = player_object.body.velocity.rotated(gravity_angle)
        speed = -player_velocity.x

        # Update player based on key press
        is_on_ground = self.physics_engine.is_on_ground(self.player_sprite)
        is_sprinting = self.is_player_sprinting()
        if is_on_ground:
            movement_force = PLAYER_SPRINT_FORCE_ON_GROUND if is_sprinting else PLAYER_MOVE_FORCE_ON_GROUND
        else:
            movement_force = PLAYER_SPRINT_FORCE_IN_AIR if is_sprinting else PLAYER_MOVE_FORCE_IN_AIR
        # movement_force = PLAYER_MOVE_FORCE_ON_GROUND if is_on_ground else PLAYER_MOVE_FORCE_IN_AIR
        speed_limit = (PLAYER_MAX_SPRINTING_SPEED if is_sprinting else PLAYER_MAX_WALKING_SPEED) if is_on_ground else PLAYER_MAX_AIRCONTROL_SPEED
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
            self.physics_engine.set_friction(self.player_sprite, 0)
        elif self.w_pressed and not self.s_pressed:
            pass
        elif self.s_pressed and not self.w_pressed:
            pass
        else:
            # Player's feet are not moving. Therefore up the friction so we stop.
            self.physics_engine.set_friction(self.player_sprite, 1.0)

        self.update_gravity()
        self.update_platforms()
        for entity in self.entities:
            entity.update()

        self.physics_engine.step(delta_time, resync_sprites)

    def on_update(self, delta_time):
        # Advance simulation n-1 times without resyncing sprites, then one last time with resyncing
        for i in range(STEPS_PER_FRAME-1):
            self.do_physics_step(STEP_DELTA_T, resync_sprites=False)
        self.do_physics_step(STEP_DELTA_T, resync_sprites=True)

        # Delete old blood
        new_particle_list = arcade.SpriteList()
        t = time.time()
        for blood in self.particle_list:
            if isinstance(blood, ParticleSprite) and t >= blood.killtime:
                self.physics_engine.remove_sprite(blood)
            else:
                new_particle_list.append(blood)
        self.particle_list = new_particle_list

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
        if LEVELS[self.current_level]['mechanics'] == MECHANICS.PLATFORMS:
            self.controllable_platform_list.draw()
        self.item_list.draw()
        self.spawned_item_list.draw()
        self.player_list.draw()
        self.soft_list.draw()
        for entity in self.entities:
            entity.draw()
        self.particle_list.draw()
        
        if self.debug:
            if DEBUG_SHOW_ITEM_HITBOXES:
                self.spawned_item_list.draw_hit_boxes(color=DEBUG_HITBOX_COLOR)
            if DEBUG_SHOW_PLAYER_HITBOXES:
                self.player_list.draw_hit_boxes(color=DEBUG_HITBOX_COLOR)
            
            self.debug_sprite_list.draw()
