import arcade
import ggj2024.sprites as sprites


class Region:
    def __init__(self, shape: list[tuple[int, int]], player_sprite: sprites.PlayerSprite):
        self.shape = shape
        self.player = player_sprite
        # self.map_bounds = map_bounds
    
    def is_player_inside(self):
        # print('player:', self.player.position, 'shape:', self.object.shape)
        # print(self.map_bounds)
        # print(self.object.shape)
        # reg = [(x, self.map_bounds[1] + y) for x, y in self.object.shape]
        # print(self.player.center_x, self.player.center_y, reg)
        return arcade.is_point_in_polygon(self.player.center_x, self.player.center_y, self.shape)