import numpy as np
from PIL import Image, ImageDraw

from ggj2024.config import *



def normalize_vector(vec: np.ndarray, inplace=False) -> np.ndarray:
    if inplace:
        vec /= np.linalg.norm(vec)
        return vec
    else:
        return vec / np.linalg.norm(vec)


def rotate90_cw(vec: np.ndarray, inplace=False) -> np.ndarray:
    if inplace:
        x = vec[0]
        vec[0] = vec[1]
        vec[1] = -x
        return vec
    else:
        return np.array([
            vec[1],
            -vec[0]
        ])


def rotate90_ccw(vec: np.ndarray, inplace=False) -> np.ndarray:
    if inplace:
        x = vec[0]
        vec[0] = -vec[1]
        vec[1] = x
        return vec
    else:
        return np.array([
            -vec[1],
            vec[0]
        ])

def intersect_rect(a, b):
    """Intersection of two rectangles
    https://stackoverflow.com/questions/25068538/intersection-and-difference-of-two-rectangles"""
    x1 = max(min(a[0], a[2]), min(b[0], b[2]))
    y1 = max(min(a[1], a[3]), min(b[1], b[3]))
    x2 = min(max(a[0], a[2]), max(b[0], b[2]))
    y2 = min(max(a[1], a[3]), max(b[1], b[3]))
    if x1 < x2 and y1 < y2:
        return (x1, y1, x2, y2)

def alpha_composite_src_over(src: np.ndarray, dest: np.ndarray, inplace=False):
    if not inplace:
        src = src.copy()
        dest = dest.copy()
    src_a = src[:,:,3:]
    dest_a = dest[:,:,3:]
    # Premultiply alpha
    src[:,:,:3] *= src_a
    dest[:,:,:3] *= dest_a
    # Composite
    dest = src + dest * (1 - src_a)
    # Divide with epsilon (to avoid zero division)
    dest[:,:,:3] /= dest[:,:,3:] + ALPHA_COMPOSITE_EPSILON
    dest[:,:,:] = np.clip(dest, 0, 1)
    return dest

def alpha_composite(bg: np.ndarray, fg: np.ndarray, pos: tuple[int, int] = None, mask_fg_with_bg=False, inplace=False):
    """Alpha composite two images. Paste `fg` onto `bg` at position `pos`. Pixel data must be in floats of range [0, 1].
    If `mask_fg_with_bg` is True, `fg` will first be masked if `bg`'s alpha channel (taking `pos` into account)"""
    if pos is None:
        if bg.shape == fg.shape:
            # No transformations needed
            if mask_fg_with_bg:
                if not inplace:
                    fg = fg.copy()
                fg[:,:,3:] *= bg[:,:,3:]
            return alpha_composite_src_over(fg, bg, inplace)
        pos = (0, 0)
    
    # Calculate and crop overlapping area
    x_fg, y_fg = pos
    isect_bg = intersect_rect((0, 0, bg.shape[0], bg.shape[1]), (x_fg, y_fg, x_fg+fg.shape[0], y_fg+fg.shape[1]))
    if isect_bg is None:
        # No intersection -> just return original bg image
        return bg if inplace else bg.copy()
    ibg_x1, ibg_y1, ibg_x2, ibg_y2 = isect_bg
    ifg_x1, ifg_y1, ifg_x2, ifg_y2 = ibg_x1 - x_fg, ibg_y1 - y_fg, ibg_x2 - x_fg, ibg_y2 - y_fg
    # Images are stored in [y,x,c] order
    bg_crop = bg[ibg_y1:ibg_y2, ibg_x1: ibg_x2, :]
    fg_crop = fg[ifg_y1:ifg_y2, ifg_x1: ifg_x2, :]
    if mask_fg_with_bg:
        fg_crop[:,:,3:] *= bg_crop[:,:,3:]
    res_crop = alpha_composite_src_over(fg_crop, bg_crop)
    if inplace:
        res = bg
    else:
        res = bg.copy()
    res[ibg_y1:ibg_y2, ibg_x1: ibg_x2, :] = res_crop
    return res

def create_circle_image(diameter, color, antialiasing: int = 1):
    diameter = int(diameter)
    if antialiasing > 1:
        diameter_aa = diameter
        diameter = int(diameter * antialiasing)
    bg_color = (0, 0, 0, 0)  # fully transparent
    img = Image.new("RGBA", (diameter, diameter), bg_color)
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, diameter - 1, diameter - 1), fill=color)
    if antialiasing > 1:
        img = img.resize((diameter_aa, diameter_aa), Image.Resampling.BICUBIC)
    return img