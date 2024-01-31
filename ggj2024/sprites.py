import arcade
import pymunk

import numpy as np
import time
from PIL import Image, ImageDraw

from ggj2024.config import *
from ggj2024.utils import *


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
        main_path = "resources/images/characters/mickey"
        # main_path = ":resources:images/animated_characters/male_person/malePerson"
        # main_path = ":resources:images/animated_characters/male_adventurer/maleAdventurer"
        # main_path = ":resources:images/animated_characters/zombie/zombie"
        # main_path = ":resources:images/animated_characters/robot/robot"

        # Load textures for idle standing
        self.idle_texture_pair = arcade.load_texture_pair(f"{main_path}/idle.png",
                                                          hit_box_algorithm=hit_box_algorithm)
        self.jump_texture_pair = arcade.load_texture_pair(f"{main_path}/jump.png",
                                                          hit_box_algorithm=hit_box_algorithm)
        self.fall_texture_pair = arcade.load_texture_pair(f"{main_path}/fall.png",
                                                          hit_box_algorithm=hit_box_algorithm)

        # Load textures for walking
        self.walk_textures = []
        for i in range(1, 9):
            texture = arcade.load_texture_pair(f"{main_path}/walk{i}.png",
                                                          hit_box_algorithm=hit_box_algorithm)
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
        phys_obj = physics_engine.get_physics_object(self)
        orientation = phys_obj.shape.body.angle
        
        direction = pymunk.Vec2d(dx, dy)
        direction_rot = direction.rotated(np.pi - orientation)
        dx, dy = -direction_rot

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
    
    def jump(self, physics_engine):
        if physics_engine.is_on_ground(self):
            impulse = (0, PLAYER_JUMP_IMPULSE)
            physics_engine.apply_impulse(self, impulse)


class PhysicsSprite(arcade.Sprite):
    def __init__(self, pymunk_shape, filename):
        super().__init__(filename, center_x=pymunk_shape.body.position.x, center_y=pymunk_shape.body.position.y)
        self.pymunk_shape = pymunk_shape


class ControllablePlatformSprite(PhysicsSprite):
    def __init__(self, pymunk_shape):
        filename_solid = 'assets/TILES/PlayerControlledPlatform.png'
        self.texture_solid = arcade.load_texture(
            filename_solid
        )
        self.texture_opaque = arcade.load_texture(
            'assets/TILES/PlayerControlledPlatformOpague.png'
        )

        super().__init__(pymunk_shape, filename_solid)
        self.set_opaque(True)

    def set_opaque(self, value):
        if value:
            self.texture = self.texture_solid
        else:
            self.texture = self.texture_opaque
        self.opaque = value


class DummyBoxSprite(PhysicsSprite):
    def __init__(self, x, y, size, mass):
        moment = pymunk.moment_for_box(mass, (size, size))
        body = pymunk.Body(mass, moment)
        body.position = pymunk.Vec2d(x, y)
        shape = pymunk.Poly.create_box(body, (size, size))
        shape.elasticity = 0.2
        shape.friction = 0.9
        super().__init__(shape, ":resources:images/tiles/boxCrate_double.png")
        self.width = size
        self.height = size


class ParticleSprite(arcade.Sprite):
    def __init__(self, x, y, radius, mass=1, liftetime=BLOOD_LIFETIME):
        color_var = int(np.random.random() * BLOOD_COLOR_VARIATION)
        if np.random.rand() < 0.5:
            color = (255 - color_var, 0, 0)
        else:
            color = (255, color_var, color_var)
        diameter = int(2*radius)
        self.texture_name = f'particle_{diameter}_{color[0]}_{color[1]}_{color[2]}'
        img = create_circle_image(diameter, color, BLOOD_PARTICLE_ANTIALIASING)
        texture = arcade.Texture(self.texture_name, img)

        super().__init__(center_x=x, center_y=y, texture=texture)
        self.radius = radius
        self.color = color
        self.killtime = time.time() + liftetime