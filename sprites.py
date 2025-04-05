import pygame
from constants import *

pygame.init()

FONT = pygame.font.Font(resource_path("fonts/Scramble-KVBe.ttf"), 49)
FONT2 = pygame.font.Font(resource_path("fonts/InterstateBold.otf"), 40)

class Square(pygame.sprite.Sprite):
    def __init__(self, x, y, colour):
        super().__init__()
        self.x = x
        self.y = y
        self.colour = colour
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.rect = self.image.get_rect(topleft=(self.x, self.y))
        self.image.fill(self.colour)
        pygame.draw.rect(self.image, "black", (0, 0, TILE_SIZE, TILE_SIZE), 1)
        self.selected = False

    def update(self, arrow=None):
        if self.selected:
            self.image.fill(self.colour)
            pygame.draw.rect(self.image, "black", (0, 0, TILE_SIZE, TILE_SIZE), 1)
            self.image.blit(arrow, (0, 0))
        else:
            self.image.fill(self.colour)
            pygame.draw.rect(self.image, "black", (0, 0, TILE_SIZE, TILE_SIZE), 1)


class TileRackSlot(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.image.fill("lightgoldenrod")


class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, letter, score):
        super().__init__()
        self.letter = letter
        self.score = score
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.image.blit(FONT.render(letter, True, "black", "lightgoldenrod"), (0, 0))

    def update(self, pos=None, letter=None):
        if letter:
            self.letter = letter
            if self.letter == "!":
                text = FONT.render(self.letter, True, "black", "lightgoldenrod")
                text_rect = text.get_rect(topleft=(0, 0))
            else:
                text = FONT2.render(letter.upper(), True, "gray40", "lightgoldenrod")
                text_rect = text.get_rect(center=(self.image.get_width()//2, self.image.get_height()//2))
            self.image.blit(text, text_rect)
        else:
            self.rect = self.image.get_rect(center=(pos[0], pos[1]))
