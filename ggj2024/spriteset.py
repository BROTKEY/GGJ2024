"""Since arcade does not supply accessible methods to just load a tileset without a map we have to do it ourself. 
Large code segments can be copied from arcade and pytiled_parser though"""

import pytiled_parser
import pytiled_parser.tiled_object
import pytiled_parser.parsers.tmx.tileset as tmx_tileset
from arcade import Point
import numpy as np



def parse_pytiled_tileset(filename, first_gid) -> pytiled_parser.Tileset:
    """first_gid means "first global ID" but I don't really know it this is important here."""
    with open(filename) as raw_tileset_file:
        raw_tileset_external = tmx_tileset.etree.parse(raw_tileset_file).getroot()
        return tmx_tileset.parse(
            raw_tileset_external,
            first_gid,
            # external_path=tileset_path.parent,
        )
    

def convert_hitbox_to_points(hitbox: pytiled_parser.tiled_object.TiledObject, 
                   sprite_size: tuple[int, int], 
                   scaling: float = 1.0,
                   flipped_vertically: bool = False,
                   flipped_horizontally: bool = False,
                   flipped_diagonally: bool = False):
    """Convert a pytiled_parser hitbox to a list[Point] supported by arcade. Basically copied out of arcade's source code."""

    sprite_width, sprite_height = sprite_size
    points: list[Point] = []
    if isinstance(hitbox, pytiled_parser.tiled_object.Rectangle):
        if hitbox.size is None:
            raise ValueError("Rectangle hitbox without a width or height")
        sx = hitbox.coordinates.x - (sprite_width / (scaling * 2))
        sy = -(hitbox.coordinates.y - (sprite_height / (scaling * 2)))
        ex = (hitbox.coordinates.x + hitbox.size.width) - (
            sprite_width / (scaling * 2)
        )
        # issue #1068
        # fixed size of rectangular hitbox
        ey = -(hitbox.coordinates.y + hitbox.size.height) + (sprite_height / (scaling * 2))
        points = [[sx, sy], [ex, sy], [ex, ey], [sx, ey]]

    elif isinstance(hitbox, (pytiled_parser.tiled_object.Polygon, pytiled_parser.tiled_object.Polyline)):
        for point in hitbox.points:
            adj_x = (
                point.x
                + hitbox.coordinates.x
                - sprite_width / (scaling * 2)
            )
            adj_y = -(
                point.y
                + hitbox.coordinates.y
                - sprite_height / (scaling * 2)
            )
            adj_point = [adj_x, adj_y]
            points.append(adj_point)
        if points[0][0] == points[-1][0] and points[0][1] == points[-1][1]:
            points.pop()

    elif isinstance(hitbox, pytiled_parser.tiled_object.Ellipse):
        if not hitbox.size:
            raise ValueError("Ellipse hitbox without a width or height")

        hw = hitbox.size.width / 2
        hh = hitbox.size.height / 2
        cx = hitbox.coordinates.x + hw
        cy = hitbox.coordinates.y + hh

        acx = cx - (sprite_width / (scaling * 2))
        acy = cy - (sprite_height / (scaling * 2))

        total_steps = 8
        angles = [
            step / total_steps * 2 * np.pi for step in range(total_steps)
        ]
        for angle in angles:
            x = hw * np.cos(angle) + acx
            y = -(hh * np.sin(angle) + acy)
            points.append([x, y])

    else:
        raise TypeError(f'Hitbox type {type(hitbox)} not supported.')

    if flipped_vertically:
        for point in points:
            point[1] *= -1

    if flipped_horizontally:
        for point in points:
            point[0] *= -1

    if flipped_diagonally:
        for point in points:
            point[0], point[1] = point[1], point[0]
    
    return points



class Spriteset(pytiled_parser.Tileset):
    """Sprite representation of a tiled Tileset"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hitbox_object = None
        self.hitbox_points = None

    @staticmethod
    def load(filename, first_gid):
        """first_gid means "first global ID" but I don't really know it this is important here."""
        pytiled_tileset = parse_pytiled_tileset(filename, first_gid)
        return Spriteset(pytiled_tileset)

    def get_tile_by_id(self, id: int):
        return self.tiles[id]

    def get_tiles_by_class(self, classname: str):
        return [t for t in self.tiles.values() if t.class_ == classname]

    def get_tiles_by_properties(self, properties: dict):
        """Return all tiles that match all the given properties (Custom Properties)"""
        return [t for t in self.tiles.values() if properties.items() <= t.properties.items()]

    def get_sprite(self, id):
        tile = self.tiles[id]
        if not isinstance(tile.objects, pytiled_parser.ObjectLayer):
            raise TypeError('Expected tile.objects to be of type pytiled_parser.ObjectLayer')
        hitboxes = tile.objects.tiled_objects
        if hitboxes:
            if len(hitboxes) > 1:
                print(f'Warning: Found multiple hitboxes (or TiledObjects) for sprite {id}. Currently only one hitbox is supported.')
            self.hitbox_object = hitboxes[0]
            self.hitbox_points = convert_hitbox_to_points(
                self.hitbox_object,
                
            )