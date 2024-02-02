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
SCREEN_GRID_HEIGHT = 12

# Size of screen to show, in pixels
SCREEN_WIDTH = SPRITE_SIZE * SCREEN_GRID_WIDTH
SCREEN_HEIGHT = SPRITE_SIZE * SCREEN_GRID_HEIGHT

# How fast the camera scrolls
CAMERA_SPEED = 1e-3

# --- Physics forces. Higher number, faster accelerating.

# Gravity
GRAVITY = 2000

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
PLAYER_MAX_HORIZONTAL_SPEED = 4000
PLAYER_MAX_VERTICAL_SPEED = 4000

ITEM_MAX_VELOCITY = 6000

PLAYER_MAX_WALKING_SPEED = 300
PLAYER_MAX_SPRINTING_SPEED = 2 * PLAYER_MAX_WALKING_SPEED
PLAYER_MAX_AIRCONTROL_SPEED = 300

# Force applied while on the ground
PLAYER_MOVE_FORCE_ON_GROUND = 5000
PLAYER_SPRINT_FORCE_ON_GROUND = 2 * PLAYER_MOVE_FORCE_ON_GROUND
# Force applied when moving left/right in the air
PLAYER_MOVE_FORCE_IN_AIR = 4000
PLAYER_SPRINT_FORCE_IN_AIR = 2 * PLAYER_MOVE_FORCE_IN_AIR

# Strength of a jump
PLAYER_JUMP_IMPULSE = 2000

PLAYER_DEATH_IMPULSE = 3000

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

# Defines how many (additionally spawned) diversifier items can exist at one time
MAX_SPAWNED_ITEMS = 50

FIST_THRESHOLD = 2.5

STEPS_PER_FRAME = 4

# Blood particles
BLOOD_PARTICLES_PER_SPLATTER = 75
# Max. initial impulse of blood particles
BLOOD_IMPULSE = 1000
# When a particle collides a random offset in movement direction will be added (for more randomness). 
# IMAPCT_RANGE is the multiplier for this (higher = more distributed over the wall)
BLOOD_SPLATTER_IMPACT_RANGE = 0.01
# Particle size will be random from [MIN, MIN + RANGE)
BLOOD_PARTICLE_SIZE_MIN = 1
BLOOD_PARTICLE_SIZE_RANGE = 5

BLOOD_LIFETIME = 3

BLOOD_COLOR_VARIATION = 60
BLOOD_PARTICLE_ANTIALIASING = 4
BLOOD_WALL_ANTIALIASING = 4
# Multiplier for the size of the blood splatters on the wall compared to their respective particles
BLOOD_WALL_SIZE_MULTIPLIER = 2

BLOOD_COLOR_VARIATION = 60
BLOOD_PARTICLE_ANTIALIASING = 4
BLOOD_WALL_ANTIALIASING = 4
BLOOD_WALL_SIZE_MULTIPLIER = 2

# Controller config
CONTROLLER_STICK_WALK_DEADZONE = 0.5
CONTROLLER_STICK_GRAVITY_DEADZONE = 0.5

CONTROLLER_TRIGGER_PLATFORM_THRESHOLD = 0.5
CONTROLLER_PLATFORM_MULTIPLIER = 500

# LeapMotion
USE_LEAPMOTION = False

# Sounds
MUTE_MUSIC = False
HITSOUND_MIN_IMPULSE = 5000
HITSOUND_RANGE = 10000

# Utils
# Epsilon to avoid zero division
ALPHA_COMPOSITE_EPSILON = 1e-9

# Debug switches. Only relevant when launching with --debug
DEBUG_SHOW_ITEM_HITBOXES = True
DEBUG_SHOW_PLAYER_HITBOXES = True
DEBUG_HITBOX_COLOR = (0, 0, 255, 255) # blue 
DEBUG_BLOOD_SPLATTER = False