import os
import sys


def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

with open(resource_path("wordlist.txt")) as file:
    ALLOWED_WORDS = set(line.strip("\n") for line in file)

SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 800
FPS = 60
SQUARE_COLOUR = [
            ["r", "y", "y", "c", "y", "y", "y", "r", "y", "y", "y", "c", "y", "y", "r"],
            ["y", "p", "y", "y", "y", "b", "y", "y", "y", "b", "y", "y", "y", "p", "y"],
            ["y", "y", "p", "y", "y", "y", "c", "y", "c", "y", "y", "y", "p", "y", "y"],
            ["c", "y", "y", "p", "y", "y", "y", "c", "y", "y", "y", "p", "y", "y", "c"],
            ["y", "y", "y", "y", "p", "y", "y", "y", "y", "y", "p", "y", "y", "y", "y"],
            ["y", "b", "y", "y", "y", "b", "y", "y", "y", "b", "y", "y", "y", "b", "y"],
            ["y", "y", "c", "y", "y", "y", "c", "y", "c", "y", "y", "y", "c", "y", "y"],
            ["r", "y", "y", "c", "y", "y", "y", "m", "y", "y", "y", "c", "y", "y", "r"],
            ["y", "y", "c", "y", "y", "y", "c", "y", "c", "y", "y", "y", "c", "y", "y"],
            ["y", "b", "y", "y", "y", "b", "y", "y", "y", "b", "y", "y", "y", "b", "y"],
            ["y", "y", "y", "y", "p", "y", "y", "y", "y", "y", "p", "y", "y", "y", "y"],
            ["c", "y", "y", "p", "y", "y", "y", "c", "y", "y", "y", "p", "y", "y", "c"],
            ["y", "y", "p", "y", "y", "y", "c", "y", "c", "y", "y", "y", "p", "y", "y"],
            ["y", "p", "y", "y", "y", "b", "y", "y", "y", "b", "y", "y", "y", "p", "y"],
            ["r", "y", "y", "c", "y", "y", "y", "r", "y", "y", "y", "c", "y", "y", "r"]
        ]
COLOURS = {"y": "lightyellow3",
           "r": "red",
           "c": "cyan",
           "p": "pink",
           "b": "blue",
           "m": "pink3"}
TILES = {"a": (1, 9),
         "b": (3, 2),
         "c": (3, 2),
         "d": (2, 4),
         "e": (1, 12),
         "f": (4, 2),
         "g": (2, 3),
         "h": (4, 2),
         "i": (1, 9),
         "j": (8, 1),
         "k": (5, 1),
         "l": (1, 4),
         "m": (3, 2),
         "n": (1, 6),
         "o": (1, 8),
         "p": (3, 2),
         "q": (10, 1),
         "r": (1, 6),
         "s": (1, 4),
         "t": (1, 6),
         "u": (1, 4),
         "v": (4, 2),
         "w": (4, 2),
         "x": (8, 1),
         "y": (4, 2),
         "z": (10, 1),
         "!": (0, 2)}
TILE_SIZE = 50
