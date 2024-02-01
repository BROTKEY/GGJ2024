"""Since arcade does not supply accessible methods to just load a tileset without a map we have to do it ourself. 
Large code segments can be copied from arcade and pytiled_parser though.
Specifically interesting:
 - arcade.tilemap.tilemap._create_sprite_from_tile(...)
 - pytiled_parser.parsers.tmx.tileset.parse
 """

import os
import numpy as np
from typing import Any, Dict, List, Optional, cast
from pathlib import Path

import pytiled_parser
import pytiled_parser.tiled_object
import pytiled_parser.parsers.tmx.tileset as tmx_tileset

import arcade
from arcade import Point
from arcade.tilemap.tilemap import _get_image_info_from_tileset, _get_image_source


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
    """Sprite representation of a pytiled_parser Tileset"""
    
    def __init__(self, 
                 filename: Optional[str|Path] = None, 
                 first_gid: int = None,
                 scaling: float = 1.0,
                 hit_box_algorithm: str = 'Simple',
                 hit_box_detail: float = 4.5,
                 custom_class: Optional[type] = None,
                 custom_class_args: Dict[str, Any] = {},
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if filename:
            self.filename = Path(filename)
            self.directory = self.filename.parent
        else:
            self.filename = None
            self.directory = None
        
        self.sprites: Dict[int, arcade.Sprite] = {
            id: self._create_sprite_from_tile(
                tile, 
                scaling, 
                hit_box_algorithm, 
                hit_box_detail, 
                custom_class, 
                custom_class_args
            ) for id, tile in self.tiles.items()
        }

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

    def _create_sprite_from_tile(
            self,
            tile: pytiled_parser.Tile,
            scaling: float = 1.0,
            hit_box_algorithm: str = "Simple",
            hit_box_detail: float = 4.5,
            custom_class: Optional[type] = None,
            custom_class_args: Dict[str, Any] = {},
        ) -> arcade.Sprite:
        """Given a tile from the parser, try and create a Sprite from it.
        Basically a standalone version of `arcade.tilemap.tilemap.TileMap._create_sprite_from_tile(...)`"""

        # --- Step 1, Find a reference to an image this is going to be based off of
        # map_source = self.tiled_map.map_file
        # map_directory = os.path.dirname(map_source)
        image_file = _get_image_source(tile, self.directory)

        if tile.animation:
            if not custom_class:
                custom_class = arcade.AnimatedTimeBasedSprite
            elif not issubclass(custom_class, arcade.AnimatedTimeBasedSprite):
                raise RuntimeError(
                    f"""
                    Tried to use a custom class {custom_class.__name__} for animated tiles
                    that doesn't subclass AnimatedTimeBasedSprite.
                    Custom classes for animated tiles must subclass AnimatedTimeBasedSprite.
                    """
                )
            # print(custom_class.__name__)
            args = {"filename": image_file, "scale": scaling}
            my_sprite = custom_class(**custom_class_args, **args)  # type: ignore
        else:
            if not custom_class:
                custom_class = arcade.Sprite
            elif not issubclass(custom_class, arcade.Sprite):
                raise RuntimeError(
                    f"""
                    Tried to use a custom class {custom_class.__name__} for
                    a tile that doesn't subclass arcade.Sprite.
                    Custom classes for tiles must subclass arcade.Sprite.
                    """
                )
            image_x, image_y, width, height = _get_image_info_from_tileset(tile)
            args = {
                "filename": image_file,
                "scale": scaling,
                "image_x": image_x,
                "image_y": image_y,
                "image_width": width,
                "image_height": height,
                "flipped_horizontally": tile.flipped_horizontally,
                "flipped_vertically": tile.flipped_vertically,
                "flipped_diagonally": tile.flipped_diagonally,
                "hit_box_algorithm": hit_box_algorithm,  # type: ignore
                "hit_box_detail": hit_box_detail,
            }
            my_sprite = custom_class(**custom_class_args, **args)  # type: ignore

        if tile.properties is not None and len(tile.properties) > 0:
            for key, value in tile.properties.items():
                my_sprite.properties[key] = value

        if tile.class_:
            my_sprite.properties["type"] = tile.class_

        # Add tile ID to sprite properties
        my_sprite.properties["tile_id"] = tile.id

        if tile.objects is not None:
            if not isinstance(tile.objects, pytiled_parser.ObjectLayer):
                print("Warning, tile.objects is not an ObjectLayer as expected.")
                return my_sprite

            if len(tile.objects.tiled_objects) > 1:
                if tile.image:
                    print(
                        f"Warning, only one hit box supported for tile with image {tile.image}."
                    )
                else:
                    print("Warning, only one hit box supported for tile.")

            for hitbox in tile.objects.tiled_objects:
                points: List[Point] = []
                if isinstance(hitbox, pytiled_parser.tiled_object.Rectangle):
                    if hitbox.size is None:
                        print(
                            "Warning: Rectangle hitbox created for without a "
                            "height or width Ignoring."
                        )
                        continue

                    sx = hitbox.coordinates.x - (my_sprite.width / (scaling * 2))
                    sy = -(hitbox.coordinates.y - (my_sprite.height / (scaling * 2)))
                    ex = (hitbox.coordinates.x + hitbox.size.width) - (
                        my_sprite.width / (scaling * 2)
                    )
                    # issue #1068
                    # fixed size of rectangular hitbox
                    ey = -(hitbox.coordinates.y + hitbox.size.height) + (
                        my_sprite.height / (scaling * 2)
                    )

                    points = [[sx, sy], [ex, sy], [ex, ey], [sx, ey]]
                elif isinstance(
                    hitbox, pytiled_parser.tiled_object.Polygon
                ) or isinstance(hitbox, pytiled_parser.tiled_object.Polyline):
                    for point in hitbox.points:
                        adj_x = (
                            point.x
                            + hitbox.coordinates.x
                            - my_sprite.width / (scaling * 2)
                        )
                        adj_y = -(
                            point.y
                            + hitbox.coordinates.y
                            - my_sprite.height / (scaling * 2)
                        )
                        adj_point = [adj_x, adj_y]
                        points.append(adj_point)

                    if points[0][0] == points[-1][0] and points[0][1] == points[-1][1]:
                        points.pop()
                elif isinstance(hitbox, pytiled_parser.tiled_object.Ellipse):
                    if not hitbox.size:
                        print(
                            f"Warning: Ellipse hitbox created without a height "
                            f" or width for {tile.image}. Ignoring."
                        )
                        continue

                    hw = hitbox.size.width / 2
                    hh = hitbox.size.height / 2
                    cx = hitbox.coordinates.x + hw
                    cy = hitbox.coordinates.y + hh

                    acx = cx - (my_sprite.width / (scaling * 2))
                    acy = cy - (my_sprite.height / (scaling * 2))

                    total_steps = 8
                    angles = [
                        step / total_steps * 2 * np.pi for step in range(total_steps)
                    ]
                    for angle in angles:
                        x = hw * np.cos(angle) + acx
                        y = -(hh * np.sin(angle) + acy)
                        points.append([x, y])
                else:
                    print(f"Warning: Hitbox type {type(hitbox)} not supported.")

                if tile.flipped_vertically:
                    for point in points:
                        point[1] *= -1

                if tile.flipped_horizontally:
                    for point in points:
                        point[0] *= -1

                if tile.flipped_diagonally:
                    for point in points:
                        point[0], point[1] = point[1], point[0]

                my_sprite.hit_box = points

        if tile.animation:
            key_frame_list = []
            for frame in tile.animation:
                # frame_tile = self._get_tile_by_id(tile.tileset, frame.tile_id)
                frame_tile = self.tiles[frame.tile_id]
                if frame_tile:
                    image_file = _get_image_source(frame_tile, self.directory)

                    if frame_tile.image and image_file:
                        texture = arcade.load_texture(image_file)
                    elif not frame_tile.image and image_file:
                        # No image for tile, pull from tilesheet
                        (
                            image_x,
                            image_y,
                            width,
                            height,
                        ) = _get_image_info_from_tileset(frame_tile)

                        texture = arcade.load_texture(
                            image_file, image_x, image_y, width, height
                        )
                    else:
                        raise RuntimeError(
                            f"Warning: failed to load image for animation frame for "
                            f"tile '{frame_tile.id}', '{image_file}'."
                        )

                    key_frame = AnimationKeyframe(  # type: ignore
                        frame.tile_id, frame.duration, texture
                    )
                    key_frame_list.append(key_frame)

                    if len(key_frame_list) == 1:
                        my_sprite.texture = key_frame.texture

            cast(arcade.AnimatedTimeBasedSprite, my_sprite).frames = key_frame_list

        return my_sprite
