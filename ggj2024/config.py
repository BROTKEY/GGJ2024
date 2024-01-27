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
CAMERA_SPEED = 1e-4

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
PLAYER_MAX_HORIZONTAL_SPEED = 5000
PLAYER_MAX_VERTICAL_SPEED = 5000

# PLAYER_MAX_HORIZONTAL_SPEED_ON_GROUND = 1000
PLAYER_MAX_WALKING_SPEED = 500
PLAYER_MAX_AIRCONTROL_SPEED = 250

# Force applied while on the ground
PLAYER_MOVE_FORCE_ON_GROUND = 8000
# Force applied when moving left/right in the air
PLAYER_MOVE_FORCE_IN_AIR = 5000

# Strength of a jump
PLAYER_JUMP_IMPULSE = 1500

PLAYER_DEATH_IMPULSE = 5000

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
MAX_SPAWNED_ITEMS = 10