import pymunk
import arcade
import time
import numpy as np



class Entity:
    def __init__(self, sprite: arcade.Sprite):
        self.sprite = sprite
    
    @property
    def position(self):
        return self.sprite.position
    
    def update(self):
        pass

    def draw(self):
        self.sprite.draw()
    

class ItemSpawner(Entity):
    def __init__(self, sprite: arcade.Sprite, register_callback, asset_filenames,
                 spawn_interval: float = 1, enabled: bool = True,
                 item_size: int | tuple[int, int] = (32, 32),
                 max_scale: int | None = None,
                 item_mass = 5,
                 **kwargs
                #  min_item_size: int | tuple[int, int] = (32, 32),
                #  max_item_size: int | tuple[int, int] = (64, 64)
                 ):
        """@param sprite The sprite that represents it in the world
        @param register_callback A function that is used to register spawned items in the world
        @param asset_filenames A list with asset filenames of which to choose randomly
        @param spawn_interval Item spawn interval in seconds
        @param enabled Initial enabled state
        @param item_size Size of the spawned items (size or (width, height) tuple)
        @param max_scale Maximum scale factor for randomized items
        @param kwargs Custom arguments for register_callback"""
        super().__init__(sprite)
        self.assets = asset_filenames
        self.register_callback = register_callback
        self.spawn_interval = spawn_interval
        self.next_spawn = 0
        self.enabled = enabled
        self.item_size = np.array([item_size, item_size]) if isinstance(item_size, (int, float)) else np.array(item_size)
        self.max_scale = max_scale
        self.item_mass = item_mass
        self.callback_args = kwargs
        # self.min_size = (min_item_size, min_item_size) if isinstance(min_item_size, (int, float)) else min_item_size
        # self.max_size = (max_item_size, max_item_size) if isinstance(max_item_size, (int, float)) else max_item_size
    
    @property
    def enabled(self):
        return self._enabled
    
    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        if value:
            self.next_spawn = time.time() + self.spawn_interval

    def update(self):
        if self.enabled:
            t = time.time()
            if t >= self.next_spawn:
                self.spawn_item()
                self.next_spawn += self.spawn_interval
    
    def spawn_item(self):
        sprite = arcade.Sprite(np.random.choice(self.assets))
        print(self.max_scale, self.item_size)
        if self.max_scale:
            s = np.random.uniform(low=1, high=self.max_scale)
            w, h = self.item_size * s
            mass = self.item_mass * s
        else:
            w, h = self.item_size
            mass = self.item_mass
        sprite.width = int(w)
        sprite.height = int(h)
        sprite.center_x = self.sprite.center_x
        sprite.center_y = self.sprite.center_y
        self.register_callback(sprite, mass=mass,**self.callback_args)