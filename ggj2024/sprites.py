import arcade

from ggj2024.config import *
import pymunk
import numpy as np
import time



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
        self.jump_texture_pair = arcade.load_texture_pair(f"{main_path}/jump.png")
        self.fall_texture_pair = arcade.load_texture_pair(f"{main_path}/fall.png")

        # Load textures for walking
        self.walk_textures = []
        for i in range(1, 9):
            texture = arcade.load_texture_pair(f"{main_path}/walk{i}.png")
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
    PARTICLE_COUNT = 0
    COLOR_VARIATION = 50

    def __init__(self, x, y, radius, mass=1, liftetime=BLOOD_LIFETIME):
        self.texture_name = f'particle_{ParticleSprite.PARTICLE_COUNT}'
        ParticleSprite.PARTICLE_COUNT += 1
        color_var = int(np.random.random() * ParticleSprite.COLOR_VARIATION)
        if np.random.rand() < 0.5:
            color = (255 - color_var, 0, 0)
        else:
            color = (255, color_var, color_var)
        diameter = int(2*radius)
        texture = arcade.make_circle_texture(diameter, color, self.texture_name)
        super().__init__(center_x=x, center_y=y, texture=texture)
        self.radius = radius
        self.width = 2*radius
        self.height = 2*radius
        self.killtime = time.time() + liftetime