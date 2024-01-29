import numpy as np


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
